# SDD-算法：归因模板 SOP 执行引擎详细设计

> **模块**：归因模板（Attribution Templates）
> **关联PRD**：归因模板模块PRD_v2.0
> **核心原则**：复用现有 Text2SQL Workflow，归因引擎只做步骤编排 + 变量替换 + 结果聚合

---

## 一、算法总览

### 1.1 归因引擎在系统中的位置

```
用户点击"运行SOP"
    ↓
归因模板引擎（本文件设计）
    ├── 步骤编排器（StepOrchestrator）
    ├── 变量替换器（VariableReplacer）
    ├── 步骤间依赖解析器（DependencyResolver）
    ├── Text2SQL 调用器（复用现有 Workflow）
    ├── 策略建议生成器（StrategyGenerator）
    └── 结果聚合器（ResultAggregator）
    ↓
返回每步结果给前端渲染
```

**关键决策**：归因引擎**不重新实现 NL2SQL**。每一步的查询执行完全复用现有 `Text2SQLWorkflow.run(question)`，归因引擎的增量价值在于：
1. 把多步查询组织成 SOP 流程
2. 处理变量替换（品牌/时间/区域）
3. 处理步骤间依赖（上一步结果注入下一步）
4. 聚合多步结果生成总结

### 1.2 单次 SOP 运行的完整算法流程

```
输入：template_id, params{brand, time_range, region}
  ↓
1. 加载模板配置（templates + template_steps + template_dimensions）
  ↓
2. 创建运行记录（template_runs，status=running）
  ↓
3. 循环执行每一步 step_index = 0..N-1：
   a. 读取该步配置（query_template, step_type, expected_output）
   b. 变量替换：{{brand}}/{{time}}/{{region}} → params 中的值
   c. 如果 step_type != strategy：
      - 依赖解析：{{prev_result}} → 从上一步结果提取关键实体
      - 调用 Text2SQLWorkflow.run(replaced_question)
      - 得到 {thinking_steps, sql, result, chart_type, chart_config, conclusion, key_numbers}
   d. 如果 step_type == strategy：
      - 调用 StrategyGenerator.generate(previous_conclusions)
      - 得到 {conclusion, key_numbers}（无 sql/result/chart）
   e. 存入 step_results[step_index]
   f. 更新 current_step = step_index
   g. 返回该步结果给前端（同步返回，非SSE）
  ↓
4. 全部步骤完成 → 调用 ResultAggregator.summarize(step_results)
  ↓
5. 更新运行记录（status=completed, completed_at, total_duration_ms）
  ↓
6. 返回总结给前端
```

---

## 二、变量替换器（VariableReplacer）

### 2.1 支持的变量

| 变量 | 来源 | 替换规则 | 示例 |
|---|---|---|---|
| `{{brand}}` | params.brand | 直接替换，"全部"时替换为"全集团" | "广汽埃安" |
| `{{time}}` | params.time_range | 时间范围标准化为自然语言 | "2025年第二季度" |
| `{{region}}` | params.region | 直接替换，"全部"时省略 | "华南区域" |
| `{{prev_result}}` | 上一步结果 | DependencyResolver 提取，见第三章 | "传祺" |
| `{{metric}}` | template.metric_key | 从语义层指标字典映射为中文名 | "总交付量" |

### 2.2 替换算法

```python
class VariableReplacer:
    def __init__(self, semantic_service):
        self.semantic = semantic_service  # 用于 metric_key → 中文名映射

    def replace(self, query_template: str, params: dict, prev_result: str = None) -> str:
        result = query_template

        # 品牌替换
        brand = params.get('brand', '全部')
        result = result.replace('{{brand}}', '全集团' if brand == '全部' else brand)

        # 时间替换（标准化）
        time_range = params.get('time_range', '上季度')
        result = result.replace('{{time}}', self._normalize_time(time_range))

        # 区域替换（全部时省略，用"各区域"替代）
        region = params.get('region', '全部')
        result = result.replace('{{region}}', '各区域' if region == '全部' else f'{region}区域')

        # 指标替换
        metric_key = params.get('metric_key', 'delivered_units')
        metric_name = self.semantic.get_metric_name(metric_key)
        result = result.replace('{{metric}}', metric_name)

        # 上一步结果替换
        if prev_result:
            result = result.replace('{{prev_result}}', prev_result)

        return result

    def _normalize_time(self, time_range: str) -> str:
        """将快捷选项转为自然语言时间范围"""
        mapping = {
            '本月': '本月',
            '上月': '上个月',
            '本季度': '本季度',
            '上季度': '上一季度',
            '今年': '今年',
            '去年': '去年',
        }
        return mapping.get(time_range, time_range)
```

### 2.3 替换示例

**输入 query_template**：
```
"{{time}} {{brand}}的{{metric}}与预算目标达成率是多少？"
```

**输入 params**：`{brand: "全部", time_range: "上季度", metric_key: "delivered_units"}`

**替换后**：
```
"上一季度 全集团的总交付量与预算目标达成率是多少？"
```

---

## 三、步骤间依赖解析器（DependencyResolver）

### 3.1 为什么需要依赖解析

归因分析的核心逻辑是**逐层下钻**：
- Step1：整体达成率 → 找出"达成率最低的品牌"
- Step2：该品牌各区域对比 → 找出"表现最差的区域"
- Step3：该区域各车型对比 → 找出"拖累最大的车型"

Step2 的查询需要知道 Step1 找出的品牌名，这就是 `{{prev_result}}` 变量。

### 3.2 提取算法

```python
class DependencyResolver:
    # 品牌名关键词列表（从语义层维度字典获取）
    BRAND_KEYWORDS = ['广汽埃安', '埃安', '广汽传祺', '传祺', '昊铂']
    REGION_KEYWORDS = ['华东', '华南', '华北', '西南', '华中', '东北', '西北']

    def extract_prev_result(self, prev_step_result: dict, step_type: str) -> str:
        """
        从上一步结果中提取关键实体，用于注入下一步的 {{prev_result}}
        返回提取到的实体名，提取失败返回默认值
        """
        conclusion = prev_step_result.get('conclusion', '')
        result_data = prev_step_result.get('result', {})

        # 策略1：从结论文本中正则匹配品牌/区域名
        entity = self._extract_from_text(conclusion)
        if entity:
            return entity

        # 策略2：从结果数据中取第一行第一列（通常是排名第一的实体）
        rows = result_data.get('rows', [])
        if rows and len(rows) > 0:
            first_value = str(rows[0][0])
            if self._is_valid_entity(first_value):
                return first_value

        # 策略3：根据步骤类型给默认值
        return self._default_for_step_type(step_type)

    def _extract_from_text(self, text: str) -> str | None:
        """从结论文本中提取第一个出现的品牌或区域名"""
        for keyword in self.BRAND_KEYWORDS + self.REGION_KEYWORDS:
            if keyword in text:
                # 处理"广汽埃安"和"埃安"的包含关系，优先匹配长的
                return keyword
        return None

    def _is_valid_entity(self, value: str) -> bool:
        """判断值是否像一个实体名（不是数字/日期）"""
        if not value or value.isdigit():
            return False
        # 排除纯数字和日期格式
        if '-' in value and value.count('-') == 1:  # 可能是日期
            return False
        return True

    def _default_for_step_type(self, step_type: str) -> str:
        """提取失败时的兜底默认值"""
        defaults = {
            'drilldown': '全部品牌',
            'breakdown': '全部',
            'trend': '全集团',
        }
        return defaults.get(step_type, '全部')
```

### 3.3 提取失败的兜底

- 提取失败时用默认值（如"全部品牌"），**不阻断 SOP 执行**
- 在该步的 thinking_steps 中添加一条备注："未从上一步提取到具体实体，使用默认值'全部品牌'"
- 产品理由：归因SOP是辅助分析工具，某一步依赖提取失败不应让整个流程中断，用户可以在结果中看到用了默认值，自行判断

---

## 四、Text2SQL 调用器（NL2SQLInvoker）

### 4.1 调用方式

**直接调用现有 Workflow 的内部函数，不通过 HTTP 自调用。**

```python
from workflow.orchestrator import Text2SQLWorkflow
from workflow.context import WorkflowContext

class NL2SQLInvoker:
    def __init__(self):
        self.workflow = Text2SQLWorkflow()

    async def execute(self, question: str, params: dict) -> StepResult:
        """
        调用 Text2SQL Workflow 执行单步查询
        返回标准化的 StepResult 对象
        """
        context = WorkflowContext(
            question=question,
            brand_filter=params.get('brand', '全部'),
            session_id=f"sop_step_{int(time.time())}",
            user=params.get('user'),
        )

        # 执行完整的8步链路（复用现有实现）
        result_events = []
        async for event in self.workflow.run(context):
            result_events.append(event)

        # 从事件中提取各部分结果
        return self._parse_events(result_events, context)

    def _parse_events(self, events, context) -> StepResult:
        """将 Workflow 的 SSE 事件解析为结构化 StepResult"""
        thinking_steps = []
        sql = None
        result = None
        chart_type = None
        chart_config = None
        conclusion = None
        key_numbers = []

        for event in events:
            if event.type == 'thinking_step':
                thinking_steps.append(event.data)
            elif event.type == 'sql':
                sql = event.data['sql']
            elif event.type == 'result':
                result = {'columns': event.data['columns'], 'rows': event.data['rows']}
            elif event.type == 'chart':
                chart_type = event.data['chart_type']
                chart_config = event.data['config']
            elif event.type == 'conclusion':
                conclusion = event.data['text']
                key_numbers = event.data.get('key_numbers', [])

        return StepResult(
            thinking_steps=thinking_steps,
            sql=sql,
            result=result,
            chart_type=chart_type,
            chart_config=chart_config,
            conclusion=conclusion,
            key_numbers=key_numbers,
            duration_ms=context.total_duration_ms,
        )
```

### 4.2 超时与重试

```python
class NL2SQLInvoker:
    TIMEOUT_SECONDS = 30
    MAX_RETRIES = 1  # SOP单步只重试1次，避免整体耗时过长

    async def execute_with_retry(self, question, params):
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                return await asyncio.wait_for(
                    self.execute(question, params),
                    timeout=self.TIMEOUT_SECONDS
                )
            except asyncio.TimeoutError:
                if attempt < self.MAX_RETRIES:
                    continue
                raise StepExecutionError("查询超时，请简化问题后重试")
            except Exception as e:
                if attempt < self.MAX_RETRIES:
                    continue
                raise StepExecutionError(f"查询失败：{str(e)}")
```

**为什么只重试1次**：SOP有5步，如果每步重试3次，最坏情况15次Text2SQL调用，用户等待时间过长。SOP场景下用户更在意整体流程能跑完，单步失败可以跳过。

---

## 五、策略建议生成器（StrategyGenerator）

### 5.1 什么时候用

`step_type = strategy` 的步骤（如高管季度复盘的第5步"策略建议"），不执行 SQL 查询，而是基于前面所有步骤的结论，让大模型生成经营策略建议。

### 5.2 生成算法

```python
class StrategyGenerator:
    def __init__(self, llm_client):
        self.llm = llm_client

    async def generate(self, previous_results: list[StepResult], template_name: str) -> StepResult:
        """
        基于前几步的分析结论，生成3条具体策略建议
        """
        # 拼接前几步的结论
        conclusions = []
        for i, r in enumerate(previous_results):
            if r.conclusion:
                conclusions.append(f"第{i+1}步发现：{r.conclusion}")

        prompt = f"""你是广汽集团的资深经营分析师。基于以下归因分析发现，给出3条具体、可执行的策略建议。

分析模板：{template_name}
分析发现：
{chr(10).join(conclusions)}

要求：
1. 每条建议必须针对上面的具体发现，不泛泛而谈
2. 建议要具体到动作（如"加大XX区域的营销投入"，不是"加强管理"）
3. 按优先级排序，最重要的放第一条
4. 同时提取关键数字列表

只返回JSON：{{"conclusion":"3条建议的汇总文字","key_numbers":[{{"label":"标签","value":"数值"}}],"suggestions":["建议1","建议2","建议3"]}}"""

        response = await self.llm.chat(prompt)
        parsed = self._parse_json_response(response)

        return StepResult(
            thinking_steps=[{'step': '策略生成', 'content': '基于前几步结论生成策略建议', 'status': 'done'}],
            sql=None,  # 策略步骤无SQL
            result=None,  # 无查询结果
            chart_type='text',
            chart_config=None,
            conclusion=parsed['conclusion'],
            key_numbers=parsed.get('key_numbers', []),
            extra={'suggestions': parsed.get('suggestions', [])},
        )
```

### 5.3 策略步骤的特殊处理

- 不调用 Text2SQL，不生成 SQL，不展示图表
- 前端渲染时：显示结论文字 + 3条建议列表（带序号）
- step_results 中该步的 sql/result/chart 字段为 null

---

## 六、结果聚合器（ResultAggregator）

### 6.1 总结页生成算法

SOP 全部步骤完成后，生成总结页内容：

```python
class ResultAggregator:
    def summarize(self, step_results: list[StepResult], template_name: str) -> Summary:
        """
        聚合所有步骤的结果，生成SOP总结
        """
        # 1. 提取每步的关键发现（1句话）
        findings = []
        for i, r in enumerate(step_results):
            if r.conclusion:
                # 取结论的第一句话作为关键发现
                first_sentence = r.conclusion.split('。')[0] + '。'
                findings.append(f"{i+1}. {first_sentence}")

        # 2. 聚合关键数字（去重，取前6个）
        all_key_numbers = []
        seen_labels = set()
        for r in step_results:
            for kn in r.key_numbers or []:
                if kn['label'] not in seen_labels:
                    all_key_numbers.append(kn)
                    seen_labels.add(kn['label'])
        key_numbers = all_key_numbers[:6]

        # 3. 计算总耗时
        total_duration = sum(r.duration_ms or 0 for r in step_results)

        # 4. 统计成功/失败步数
        success_count = sum(1 for r in step_results if r.status == 'success')
        failed_count = sum(1 for r in step_results if r.status == 'failed')
        skipped_count = sum(1 for r in step_results if r.status == 'skipped')

        return Summary(
            findings=findings,
            key_numbers=key_numbers,
            total_duration_ms=total_duration,
            success_count=success_count,
            failed_count=failed_count,
            skipped_count=skipped_count,
        )
```

### 6.2 总结页前端展示结构

```
✅ SOP 执行完成（成功X步 / 失败Y步 / 跳过Z步）  总耗时：XX秒

📊 关键发现汇总
1. 整体达成率87%，未达90%目标
2. 传祺表现最差，达成率仅72%
3. ...

🔢 关键数字看板
[达成率87%] [最低品牌传祺72%] [总交付45,678] [平均CPL 320元]

[重新运行]  [修改参数重跑]  [返回模板列表]
```

---

## 七、步骤编排器（StepOrchestrator）

### 7.1 核心编排逻辑

```python
class StepOrchestrator:
    def __init__(self, template_repo, run_repo, nl2sql, strategy_gen, dependency_resolver, variable_replacer):
        self.template_repo = template_repo
        self.run_repo = run_repo
        self.nl2sql = nl2sql
        self.strategy_gen = strategy_gen
        self.dependency = dependency_resolver
        self.replacer = variable_replacer

    async def execute_step(self, run_id: str, step_index: int, params: dict) -> StepResult:
        """
        执行SOP的某一步，由前端调用（同步返回）
        """
        # 1. 加载运行记录和模板配置
        run = self.run_repo.get(run_id)
        template = self.template_repo.get_with_steps(run.template_id)
        step = template.steps[step_index]

        # 2. 变量替换
        prev_result = None
        if step_index > 0:
            prev_step_result = run.step_results[step_index - 1]
            prev_result = self.dependency.extract_prev_result(prev_step_result, step.step_type)

        replaced_question = self.replacer.replace(
            step.query_template,
            {**params, 'metric_key': template.metric_key},
            prev_result
        )

        # 3. 根据步骤类型执行
        try:
            if step.step_type == 'strategy':
                # 策略步骤：基于前面所有结论生成建议
                previous_results = run.step_results[:step_index]
                result = await self.strategy_gen.generate(previous_results, template.name)
            else:
                # 普通步骤：调用Text2SQL
                result = await self.nl2sql.execute_with_retry(replaced_question, params)

            result.status = 'success'
            result.step_name = step.step_name
            result.step_type = step.step_type
            result.replaced_question = replaced_question  # 存下来用于调试和展示

        except StepExecutionError as e:
            result = StepResult(
                status='failed',
                error=str(e),
                step_name=step.step_name,
                step_type=step.step_type,
            )

        # 4. 保存到运行记录
        run.step_results[step_index] = result
        run.current_step = step_index
        self.run_repo.update(run)

        return result
```

### 7.2 状态流转

```
步骤状态：pending → running → success / failed / skipped

- pending：未执行
- running：正在执行（前端显示loading）
- success：执行成功，有结果
- failed：执行失败（重试1次后仍失败）
- skipped：用户选择跳过（失败时的选项）
```

---

## 八、错误分类与处理

### 8.1 错误分类

| 错误类型 | 触发条件 | 处理方式 | 用户感知 |
|---|---|---|---|
| TIMEOUT | Text2SQL调用超过30s | 重试1次，仍失败标记failed | 超时提示+重试/跳过 |
| SQL_ERROR | Text2SQL生成的SQL执行失败 | Text2SQL内部已重试3次，归因层不再重试 | 显示错误原因+重试/跳过 |
| EMPTY_RESULT | SQL执行成功但返回0行 | 不算失败，status=success，conclusion提示"无数据" | 显示空状态+建议调整参数 |
| STRATEGY_ERROR | 大模型生成策略建议失败 | 用模板兜底："建议进一步分析以上发现，制定针对性改进措施" | 显示兜底建议 |
| DEPENDENCY_WARNING | prev_result提取失败 | 不阻断，用默认值，思考链加备注 | 思考链中可见备注 |

### 8.2 单步失败不阻断整体

**核心设计决策**：某一步失败时，SOP不终止，用户可以选择：
- **重试**：重新执行该步
- **跳过**：标记为skipped，继续下一步
- **终止**：结束本次运行，状态标记为failed

产品理由：归因分析是探索性的，某一步数据异常不应让整个流程白跑。用户可以看完其他步骤的结果，再决定是否重跑失败的步骤。

---

## 九、性能考量

### 9.1 单次SOP运行的耗时估算

| 环节 | 单次耗时 | 5步SOP总计 |
|---|---|---|
| Text2SQL 执行（P85） | 3-5秒 | 15-25秒 |
| 策略建议生成 | 2-3秒 | 2-3秒（仅最后一步） |
| 变量替换+依赖解析 | <100ms | <0.5秒 |
| 数据库读写 | <50ms | <0.5秒 |
| **总计（P85）** | — | **20-30秒** |

### 9.2 优化策略

1. **预加载**：开始运行时一次性加载所有步骤配置，避免每步查数据库
2. **并行预取**：执行当前步时，可预取下一步的模板配置（但不能并行执行Text2SQL，因为有依赖）
3. **结果缓存**：相同 template_id + params 的运行结果缓存5分钟，重复运行直接返回
4. **分步返回**：每步执行完立即返回给前端，用户可以边等边看，不需要等全部完成

---

## 十、与现有系统的算法集成

| 集成点 | 复用的现有能力 | 归因层的增量 |
|---|---|---|
| NL2SQL | Text2SQLWorkflow（8步链路） | 步骤编排+变量替换+依赖注入 |
| 语义层 | SemanticService（指标字典） | metric_key→中文名映射 |
| 图表 | ChartRenderer（前端组件） | 无增量，直接复用 |
| 思考链 | ThinkingChain（前端组件） | 无增量，直接复用 |
| 大模型 | LLMClient | 策略建议生成（新用途） |

---

> **算法SDD结束**。后端实现见 SDD-后端，前端对接见 SDD-前端。
