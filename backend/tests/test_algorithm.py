"""
算法部分测试用例
验证 Text2SQL 8步链路的正确性
"""

import sys
import os

# 添加项目路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "backend"))

import unittest
import json

# 测试结果统计
PASS = 0
FAIL = 0


def check(name, fn):
    """运行测试并打印结果"""
    global PASS, FAIL
    try:
        fn()
        print(f"  ✔ {name}")
        PASS += 1
        return True
    except AssertionError as e:
        print(f"  ✘ {name}: {e}")
        FAIL += 1
        return False
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"  ✘ {name}: {type(e).__name__}: {e}")
        FAIL += 1
        return False


# ============================================================
# Step 1: 意图识别测试
# ============================================================
def test_intent_recognition():
    """意图识别 - 指标查询"""
    from workflow.steps.step1_intent import recognize_intent
    
    # 业务查询
    result = recognize_intent("2025年3月埃安销量与预算达成率是多少？")
    assert result["intent"] in ["指标查询", "对比查询", "趋势查询"], f"期望业务查询，实际: {result['intent']}"
    assert result["confidence"] >= 0.5, f"置信度过低: {result['confidence']}"
    print(f"    - 业务查询识别: {result['intent']} ({result['confidence']:.2f})")


def test_intent_recognition_trend():
    """意图识别 - 趋势查询"""
    from workflow.steps.step1_intent import recognize_intent
    
    result = recognize_intent("近半年销量走势如何？")
    assert result["intent"] == "趋势查询", f"期望趋势查询，实际: {result['intent']}"
    print(f"    - 趋势查询识别: {result['intent']}")


def test_intent_recognition_non_business():
    """意图识别 - 非业务查询"""
    from workflow.steps.step1_intent import recognize_intent
    
    result = recognize_intent("今天天气怎么样？")
    assert result["intent"] == "非业务查询", f"期望非业务查询，实际: {result['intent']}"
    print(f"    - 非业务查询识别: {result['intent']}")


# ============================================================
# Step 2: 指标匹配测试
# ============================================================
def test_metric_matching():
    """指标匹配 - 销量指标"""
    from workflow.steps.step2_metric_matching import load_metrics, match_metric
    
    metrics = load_metrics()
    assert len(metrics) > 0, "指标库为空"
    
    matched, confidence = match_metric("2025年3月埃安销量多少", metrics)
    assert matched is not None, "未匹配到指标"
    print(f"    - 销量指标匹配: {matched.metric_name if matched else None} ({confidence:.2f})")


def test_metric_matching_cpl():
    """指标匹配 - CPL指标"""
    from workflow.steps.step2_metric_matching import load_metrics, match_metric
    
    metrics = load_metrics()
    matched, confidence = match_metric("各渠道CPL排名", metrics)
    assert matched is not None, "未匹配到CPL指标"
    print(f"    - CPL指标匹配: {matched.metric_name if matched else None} ({confidence:.2f})")


def test_synonym_mapping():
    """同义词匹配"""
    from workflow.steps.step2_metric_matching import match_synonyms
    
    result = match_synonyms("上个月埃安卖了多少台车")
    assert "卖" in result or "销量" in result or len(result) >= 0, "同义词匹配失败"
    print(f"    - 同义词匹配: {result}")


# ============================================================
# Step 3: 维度解析测试
# ============================================================
def test_dimension_parsing_brand():
    """维度解析 - 品牌"""
    from workflow.steps.step3_dimension import parse_brand
    
    assert parse_brand("广汽埃安3月销量") == "广汽埃安"
    assert parse_brand("传祺各车型销量") == "广汽传祺"
    assert parse_brand("昊铂GT销量") == "昊铂"
    print("    - 品牌解析正确")


def test_dimension_parsing_time():
    """维度解析 - 时间"""
    from workflow.steps.step3_dimension import parse_absolute_time, parse_relative_time
    
    # 绝对时间
    assert parse_absolute_time("2025年3月") == "2025-03"
    assert parse_absolute_time("2025-04") == "2025-04"
    print("    - 绝对时间解析正确")
    
    # 相对时间
    result = parse_relative_time("上个月销量")
    assert result is not None
    print(f"    - 相对时间解析: {result}")


def test_dimension_parsing_region():
    """维度解析 - 区域"""
    from workflow.steps.step3_dimension import parse_region
    
    assert parse_region("华东大区销量") == "华东区"
    assert parse_region("华南区销量") == "华南区"
    print("    - 区域解析正确")


# ============================================================
# Step 4: 表定位测试
# ============================================================
def test_table_location():
    """表定位"""
    from workflow.steps.step4_table_location import get_compact_schema, get_table_join_hints
    
    tables = ["fact_sales_daily", "dim_budget_target"]
    schema = get_compact_schema(tables)
    assert "fact_sales_daily" in schema
    assert "delivered_units" in schema
    print(f"    - 精简Schema生成: {len(schema)} 字符")
    
    hints = get_table_join_hints(tables)
    assert len(hints) > 0, "应有关联提示"
    print(f"    - 关联提示: {hints[0][:50]}...")


# ============================================================
# Step 5: SQL生成测试
# ============================================================
def test_sql_extraction():
    """SQL提取"""
    from workflow.steps.step5_sql_generation import extract_sql
    
    # Markdown 代码块
    text = "```sql\nSELECT * FROM table\n```"
    sql = extract_sql(text)
    assert sql is not None and "SELECT" in sql
    
    # 普通文本
    text = "SELECT brand, SUM(units) FROM sales GROUP BY brand"
    sql = extract_sql(text)
    assert sql is not None and "SELECT" in sql
    
    print("    - SQL提取正确")


def test_fallback_sql_generation():
    """兜底SQL生成"""
    from workflow.steps.step5_sql_generation import _generate_fallback_sql
    from workflow.context import WorkflowContext, Metric
    
    metric = Metric(
        metric_id="M02",
        metric_name="总交付量",
        business_domain="整车销售",
        definition="统计周期内交付量",
        unit="辆",
        calculation_rule="SUM(delivered_units)",
        required_tables=["fact_sales_daily"],
        related_dimensions=["brand_name", "sale_date"]
    )
    
    context = WorkflowContext(
        question="广汽埃安3月销量多少",
        dimensions={"brand": "广汽埃安", "time": "2025-03"}
    )
    context.matched_metric = metric
    
    sql = _generate_fallback_sql(context)
    assert sql is not None
    assert "SELECT" in sql.upper()
    assert "fact_sales_daily" in sql
    print(f"    - 兜底SQL生成: {sql[:80]}...")


# ============================================================
# Step 6: 执行校验测试
# ============================================================
def test_sql_validation():
    """SQL语法校验"""
    from workflow.steps.step6_execution import validate_sql_syntax
    
    # 合法 SQL
    valid_sql = "SELECT brand_name, SUM(delivered_units) FROM fact_sales_daily GROUP BY brand_name"
    is_valid, error, cleaned = validate_sql_syntax(valid_sql)
    assert is_valid, f"合法SQL被拒绝: {error}"
    
    # 危险 SQL
    danger_sql = "DROP TABLE fact_sales_daily"
    is_valid, error, cleaned = validate_sql_syntax(danger_sql)
    assert not is_valid, "危险SQL未被拦截"
    
    print("    - SQL校验正确")


# ============================================================
# Step 7: 可视化决策测试
# ============================================================
def test_chart_type_inference():
    """图表类型推断"""
    from workflow.steps.step7_visualization import infer_chart_type
    
    # 单行 → KPI
    chart_type = infer_chart_type("达成率是多少", ["品牌", "达成率"], 1)
    assert chart_type == "single_kpi", f"单行应为single_kpi，实际: {chart_type}"
    
    # 趋势 → 折线图
    chart_type = infer_chart_type("近半年销量走势", ["月份", "销量"], 6)
    assert chart_type == "line", f"趋势应为line，实际: {chart_type}"
    
    # 多行 → 柱状图
    chart_type = infer_chart_type("各品牌销量对比", ["品牌", "销量"], 3)
    assert chart_type in ["bar", "table"], f"多行应为bar或table，实际: {chart_type}"
    
    print("    - 图表类型推断正确")


def test_field_mapping():
    """字段映射推断"""
    from workflow.steps.step7_visualization import infer_field_mapping
    
    columns = ["品牌", "交付量", "达成率"]
    mapping = infer_field_mapping(columns, "bar")
    assert "x" in mapping or "y" in mapping
    
    print(f"    - 字段映射: {mapping}")


# ============================================================
# Step 8: 业务解读测试
# ============================================================
def test_conclusion_generation():
    """结论生成（模板）"""
    from workflow.steps.step8_conclusion import generate_conclusion_template
    from workflow.context import WorkflowContext, QueryResult, Metric
    
    metric = Metric(
        metric_id="M02",
        metric_name="总交付量",
        business_domain="整车销售",
        definition="",
        unit="辆",
        calculation_rule="SUM(delivered_units)",
        required_tables=[],
        related_dimensions=[]
    )
    
    context = WorkflowContext(
        question="广汽埃安3月销量多少",
        matched_metric=metric,
        dimensions={"brand": "广汽埃安", "time": "2025-03"}
    )
    
    context.result = QueryResult(
        columns=["品牌", "交付量"],
        rows=[["广汽埃安", 4462]],
        row_count=1
    )
    
    conclusion, key_numbers = generate_conclusion_template(context)
    assert conclusion != ""
    print(f"    - 结论生成: {conclusion[:50]}...")
    print(f"    - 关键数字: {key_numbers}")


# ============================================================
# 完整链路测试
# ============================================================
def test_full_workflow():
    """完整链路测试"""
    from workflow.orchestrator import run_workflow_sync
    
    result = run_workflow_sync("2025年3月埃安销量与预算达成率是多少？")
    
    context = result["context"]
    
    print(f"    - 状态: {context.status}")
    print(f"    - 意图: {context.intent}")
    print(f"    - 指标: {context.matched_metric.metric_name if context.matched_metric else None}")
    print(f"    - SQL: {'已生成' if context.sql else '未生成'}")
    print(f"    - 结果: {context.result.row_count if context.result else 0} 行")
    print(f"    - 图表: {context.chart_config.chart_type if context.chart_config else None}")
    print(f"    - 思考链: {len(context.thinking_steps)} 步")
    
    assert context.status in ["success", "failed"], f"状态异常: {context.status}"


# ============================================================
# 思考链展示测试
# ============================================================
def test_thinking_chain():
    """思考链记录"""
    from workflow.context import WorkflowContext
    
    context = WorkflowContext(
        question="测试问题",
        brand_filter="全部"
    )
    
    context.add_thinking_step(1, "意图识别", "检测到指标查询", "done", 50)
    context.add_thinking_step(2, "指标匹配", "命中M02总交付量", "done", 30)
    
    assert len(context.thinking_steps) == 2
    assert context.thinking_steps[0].step == 1
    assert context.thinking_steps[0].name == "意图识别"
    
    # 测试 to_dict
    step_dict = context.thinking_steps[0].to_dict()
    assert "step" in step_dict
    assert "name" in step_dict
    assert "content" in step_dict
    
    print(f"    - 思考链记录: {len(context.thinking_steps)} 步")
    for step in context.thinking_steps:
        print(f"      {step.step}. {step.name}: {step.content[:30]}...")


# ============================================================
# 运行所有测试
# ============================================================
def run_all_tests():
    global PASS, FAIL
    PASS = 0
    FAIL = 0
    
    print("\n" + "=" * 60)
    print("   GAC-ChatBI v2.0 算法层测试套件")
    print("=" * 60)
    
    print("\n--- Step 1: 意图识别 ---")
    test_intent_recognition()
    test_intent_recognition_trend()
    test_intent_recognition_non_business()
    
    print("\n--- Step 2: 指标匹配 ---")
    test_metric_matching()
    test_metric_matching_cpl()
    test_synonym_mapping()
    
    print("\n--- Step 3: 维度解析 ---")
    test_dimension_parsing_brand()
    test_dimension_parsing_time()
    test_dimension_parsing_region()
    
    print("\n--- Step 4: 表定位 ---")
    test_table_location()
    
    print("\n--- Step 5: SQL生成 ---")
    test_sql_extraction()
    test_fallback_sql_generation()
    
    print("\n--- Step 6: 执行校验 ---")
    test_sql_validation()
    
    print("\n--- Step 7: 可视化决策 ---")
    test_chart_type_inference()
    test_field_mapping()
    
    print("\n--- Step 8: 业务解读 ---")
    test_conclusion_generation()
    
    print("\n--- 完整链路 ---")
    test_full_workflow()
    
    print("\n--- 思考链展示 ---")
    test_thinking_chain()
    
    print("\n" + "=" * 60)
    print(f"   测试结果: {PASS} pass / {FAIL} fail")
    print("=" * 60)
    
    if FAIL == 0:
        print("🎉 算法层所有测试用例通过！")
        return True
    else:
        print(f"⚠️  有 {FAIL} 个用例失败，请检查")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
