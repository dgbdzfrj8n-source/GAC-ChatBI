# SDD-后端：归因模板模块后端详细设计

> **模块**：归因模板（Attribution Templates）
> **关联PRD**：归因模板模块PRD_v2.0
> **技术栈**：FastAPI + SQLite（SQLAlchemy）+ 复用 Text2SQL Workflow

---

## 一、目录结构

```
backend/
├── api/
│   └── templates.py          # 归因模板相关路由（10个接口）
├── services/
│   ├── template_service.py   # 模板CRUD + 克隆服务
│   ├── sop_run_service.py    # SOP运行服务（编排器）
│   └── sop_step_executor.py  # 单步执行器（变量替换+调用Text2SQL）
├── models/
│   └── template_models.py    # SQLAlchemy 4张表模型
├── schemas/
│   └── template_schemas.py   # Pydantic 请求/响应模型
├── core/
│   └── template_seed.py      # 系统预设模板初始数据
└── data/
    └── app.db                # SQLite数据库（与现有系统共用）
```

---

## 二、数据模型（SQLAlchemy）

### 2.1 模型定义

```python
# models/template_models.py
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class Template(Base):
    __tablename__ = 'templates'
    id = Column(String, primary_key=True)  # preset_xxx 或 user_ + UUID
    name = Column(String, nullable=False)
    description = Column(Text, default='')
    template_type = Column(String, nullable=False)  # system / role_default / user
    role = Column(String, default='all')  # executive/analyst/product_manager/guest/all
    metric_key = Column(String, default='delivered_units')
    creator = Column(String, default='system')
    is_active = Column(Integer, default=1)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    steps = relationship('TemplateStep', back_populates='template', cascade='all, delete-orphan', order_by='TemplateStep.step_order')
    dimensions = relationship('TemplateDimension', back_populates='template', cascade='all, delete-orphan')
    runs = relationship('TemplateRun', back_populates='template', cascade='all, delete-orphan')

class TemplateStep(Base):
    __tablename__ = 'template_steps'
    id = Column(Integer, primary_key=True, autoincrement=True)
    template_id = Column(String, ForeignKey('templates.id'), nullable=False)
    step_order = Column(Integer, nullable=False)  # 从0开始
    step_name = Column(String, nullable=False)
    step_icon = Column(String, default='🎯')
    step_type = Column(String, nullable=False)  # overview/horizontal/drilldown/breakdown/trend/strategy
    query_template = Column(Text, nullable=False)
    dimension_hints = Column(JSON, default=list)  # ["brand","region"]
    expected_output = Column(String, default='kpi')  # kpi/bar/line/table/pie
    is_auto_execute = Column(Integer, default=1)

    template = relationship('Template', back_populates='steps')

class TemplateDimension(Base):
    __tablename__ = 'template_dimensions'
    id = Column(Integer, primary_key=True, autoincrement=True)
    template_id = Column(String, ForeignKey('templates.id'), nullable=False)
    dimension_key = Column(String, nullable=False)  # brand/region/model/energy_type/price_segment/time
    dimension_name = Column(String, nullable=False)
    is_required = Column(Integer, default=0)
    sort_order = Column(Integer, default=0)

    template = relationship('Template', back_populates='dimensions')

class TemplateRun(Base):
    __tablename__ = 'template_runs'
    id = Column(String, primary_key=True)  # run_ + UUID
    template_id = Column(String, ForeignKey('templates.id'), nullable=False)
    user_id = Column(String, nullable=False)
    params = Column(JSON, default=dict)  # {brand, time_range, region}
    status = Column(String, default='running')  # running/completed/failed
    current_step = Column(Integer, default=0)
    step_results = Column(JSON, default=list)  # 每步完整结果
    total_duration_ms = Column(Integer, default=0)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    template = relationship('Template', back_populates='runs')
```

### 2.2 数据库初始化

应用启动时执行：
```python
# 建表（如果不存在）
Base.metadata.create_all(engine)

# Seed预设模板（如果templates表为空）
from core.template_seed import seed_preset_templates
seed_preset_templates(db)
```

---

## 三、API 路由实现

### 3.1 路由注册

```python
# api/templates.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from services.template_service import TemplateService
from services.sop_run_service import SOPRunService

router = APIRouter(prefix='/api', tags=['归因模板'])

def get_template_service(db: Session = Depends(get_db)):
    return TemplateService(db)

def get_run_service(db: Session = Depends(get_db)):
    return SOPRunService(db)
```

### 3.2 接口清单与实现

#### GET /api/templates — 获取模板列表

```python
@router.get('/templates')
def list_templates(type: str = 'all', role: str = None, db: Session = Depends(get_db)):
    service = TemplateService(db)
    templates = service.list_templates(template_type=type, role=role)
    return {
        'templates': [
            {
                'id': t.id,
                'name': t.name,
                'description': t.description,
                'template_type': t.template_type,
                'role': t.role,
                'metric_key': t.metric_key,
                'step_count': len(t.steps),
                'dimensions': [d.dimension_key for d in t.dimensions],
                'created_at': t.created_at.isoformat(),
            }
            for t in templates
        ]
    }
```

#### GET /api/templates/{template_id} — 获取模板详情

```python
@router.get('/templates/{template_id}')
def get_template(template_id: str, db: Session = Depends(get_db)):
    service = TemplateService(db)
    template = service.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail='模板不存在')
    return {
        'id': template.id,
        'name': template.name,
        'description': template.description,
        'template_type': template.template_type,
        'role': template.role,
        'metric_key': template.metric_key,
        'steps': [
            {
                'step_order': s.step_order,
                'step_name': s.step_name,
                'step_icon': s.step_icon,
                'step_type': s.step_type,
                'query_template': s.query_template,
                'dimension_hints': s.dimension_hints,
                'expected_output': s.expected_output,
                'is_auto_execute': s.is_auto_execute,
            }
            for s in template.steps
        ],
        'dimensions': [
            {'dimension_key': d.dimension_key, 'dimension_name': d.dimension_name, 'is_required': d.is_required}
            for d in template.dimensions
        ],
    }
```

#### POST /api/templates — 创建模板

```python
@router.post('/templates', status_code=201)
def create_template(req: CreateTemplateRequest, user=Depends(get_current_user), db: Session = Depends(get_db)):
    service = TemplateService(db)
    template = service.create_template(
        name=req.name,
        description=req.description,
        metric_key=req.metric_key,
        dimensions=req.dimensions,
        creator=user.username,
    )
    return {'template_id': template.id, 'name': template.name}
```

**CreateTemplateRequest 模型**：
```python
class CreateTemplateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    description: str = ''
    metric_key: str = 'delivered_units'
    dimensions: list[str] = ['brand', 'region']
```

#### PUT /api/templates/{template_id} — 更新模板

```python
@router.put('/templates/{template_id}')
def update_template(template_id: str, req: UpdateTemplateRequest, user=Depends(get_current_user), db: Session = Depends(get_db)):
    service = TemplateService(db)
    template = service.get_template(template_id)
    if not template:
        raise HTTPException(404, '模板不存在')
    # 权限校验：系统预设不可修改
    if template.template_type in ('system', 'role_default'):
        raise HTTPException(403, '系统预设模板不可修改')
    if template.creator != user.username:
        raise HTTPException(403, '只能修改自己创建的模板')

    updated = service.update_template(template_id, req.dict())
    return {'template_id': updated.id, 'updated': True}
```

#### DELETE /api/templates/{template_id} — 删除模板

```python
@router.delete('/templates/{template_id}')
def delete_template(template_id: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    service = TemplateService(db)
    template = service.get_template(template_id)
    if not template:
        raise HTTPException(404, '模板不存在')
    if template.template_type in ('system', 'role_default'):
        raise HTTPException(403, '系统预设模板不可删除')
    if template.creator != user.username:
        raise HTTPException(403, '只能删除自己创建的模板')

    service.delete_template(template_id)
    return {'deleted': True}
```

#### POST /api/templates/{template_id}/clone — 克隆模板

```python
@router.post('/templates/{template_id}/clone')
def clone_template(template_id: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    service = TemplateService(db)
    source = service.get_template(template_id)
    if not source:
        raise HTTPException(404, '源模板不存在')

    cloned = service.clone_template(template_id, creator=user.username)
    return {'template_id': cloned.id, 'name': cloned.name}
```

#### POST /api/templates/{template_id}/run — 开始SOP运行

```python
@router.post('/templates/{template_id}/run')
def start_run(template_id: str, req: RunParamsRequest, user=Depends(get_current_user), db: Session = Depends(get_db)):
    service = SOPRunService(db)
    template = service.get_template(template_id)
    if not template:
        raise HTTPException(404, '模板不存在')

    run = service.create_run(template_id, user_id=user.username, params=req.dict())
    return {'run_id': run.id}
```

#### POST /api/template-runs/{run_id}/steps/{step_index}/execute — 执行单步

```python
@router.post('/template-runs/{run_id}/steps/{step_index}/execute')
async def execute_step(run_id: str, step_index: int, req: RunParamsRequest, db: Session = Depends(get_db)):
    service = SOPRunService(db)
    run = service.get_run(run_id)
    if not run:
        raise HTTPException(404, '运行记录不存在')
    if run.status == 'completed':
        raise HTTPException(400, '该运行已完成，如需重新执行请创建新运行')

    result = await service.execute_step(run_id, step_index, params=req.dict())
    return result
```

#### GET /api/template-runs/{run_id} — 获取运行状态

```python
@router.get('/template-runs/{run_id}')
def get_run(run_id: str, db: Session = Depends(get_db)):
    service = SOPRunService(db)
    run = service.get_run(run_id)
    if not run:
        raise HTTPException(404, '运行记录不存在')
    return {
        'run_id': run.id,
        'template_id': run.template_id,
        'status': run.status,
        'current_step': run.current_step,
        'params': run.params,
        'step_results': run.step_results,
        'total_duration_ms': run.total_duration_ms,
        'started_at': run.started_at.isoformat(),
        'completed_at': run.completed_at.isoformat() if run.completed_at else None,
    }
```

#### GET /api/template-runs — 运行历史列表

```python
@router.get('/template-runs')
def list_runs(template_id: str = None, limit: int = 20, user=Depends(get_current_user), db: Session = Depends(get_db)):
    service = SOPRunService(db)
    runs = service.list_runs(user_id=user.username, template_id=template_id, limit=limit)
    return {
        'runs': [
            {
                'run_id': r.id,
                'template_id': r.template_id,
                'template_name': r.template.name,
                'status': r.status,
                'started_at': r.started_at.isoformat(),
                'total_duration_ms': r.total_duration_ms,
            }
            for r in runs
        ]
    }
```

---

## 四、服务层实现

### 4.1 TemplateService（模板CRUD + 克隆）

```python
# services/template_service.py
import uuid
from sqlalchemy.orm import Session
from models.template_models import Template, TemplateStep, TemplateDimension

DEFAULT_STEPS = [
    {'step_name': '整体概览', 'step_icon': '🎯', 'step_type': 'overview',
     'query_template': '{{time}} {{brand}}的{{metric}}整体表现如何？', 'expected_output': 'kpi'},
    {'step_name': '横向对比', 'step_icon': '↔️', 'step_type': 'horizontal',
     'query_template': '{{time}}各品牌的{{metric}}对比', 'expected_output': 'bar'},
    {'step_name': '策略建议', 'step_icon': '💡', 'step_type': 'strategy',
     'query_template': '', 'expected_output': 'text'},
]

DIMENSION_NAME_MAP = {
    'brand': '品牌', 'region': '区域', 'model': '车型',
    'energy_type': '能源类型', 'price_segment': '价格段', 'time': '时间',
}

class TemplateService:
    def __init__(self, db: Session):
        self.db = db

    def list_templates(self, template_type='all', role=None):
        query = self.db.query(Template).filter(Template.is_active == 1)
        if template_type != 'all':
            if template_type == 'user':
                query = query.filter(Template.template_type == 'user')
            else:
                query = query.filter(Template.template_type.in_(['system', 'role_default']))
        if role:
            query = query.filter(Template.role.in_([role, 'all']))
        return query.order_by(Template.sort_order).all()

    def get_template(self, template_id: str):
        return self.db.query(Template).filter(Template.id == template_id).first()

    def create_template(self, name, description, metric_key, dimensions, creator):
        template_id = f'user_{uuid.uuid4().hex[:8]}'
        template = Template(
            id=template_id, name=name, description=description,
            template_type='user', role='all', metric_key=metric_key, creator=creator,
        )
        self.db.add(template)

        # 自动插入3个默认步骤
        for i, step in enumerate(DEFAULT_STEPS):
            self.db.add(TemplateStep(
                template_id=template_id, step_order=i, **step
            ))

        # 插入维度
        for i, dim_key in enumerate(dimensions):
            self.db.add(TemplateDimension(
                template_id=template_id, dimension_key=dim_key,
                dimension_name=DIMENSION_NAME_MAP.get(dim_key, dim_key),
                is_required=1 if dim_key in ('brand', 'time') else 0,
                sort_order=i,
            ))

        self.db.commit()
        self.db.refresh(template)
        return template

    def update_template(self, template_id, data):
        template = self.get_template(template_id)
        template.name = data.get('name', template.name)
        template.description = data.get('description', template.description)
        template.metric_key = data.get('metric_key', template.metric_key)

        # 全量替换步骤（先删后插）
        self.db.query(TemplateStep).filter(TemplateStep.template_id == template_id).delete()
        for i, step in enumerate(data.get('steps', [])):
            self.db.add(TemplateStep(template_id=template_id, step_order=i, **step))

        # 全量替换维度
        self.db.query(TemplateDimension).filter(TemplateDimension.template_id == template_id).delete()
        for i, dim in enumerate(data.get('dimensions', [])):
            self.db.add(TemplateDimension(
                template_id=template_id,
                dimension_key=dim['dimension_key'],
                dimension_name=dim.get('dimension_name', dim['dimension_key']),
                is_required=dim.get('is_required', 0),
                sort_order=i,
            ))

        self.db.commit()
        self.db.refresh(template)
        return template

    def delete_template(self, template_id):
        template = self.get_template(template_id)
        self.db.delete(template)
        self.db.commit()

    def clone_template(self, source_id, creator):
        source = self.get_template(source_id)
        new_id = f'user_{uuid.uuid4().hex[:8]}'
        cloned = Template(
            id=new_id, name=f'{source.name} 副本', description=source.description,
            template_type='user', role='all', metric_key=source.metric_key, creator=creator,
        )
        self.db.add(cloned)

        # 复制所有步骤
        for step in source.steps:
            self.db.add(TemplateStep(
                template_id=new_id, step_order=step.step_order,
                step_name=step.step_name, step_icon=step.step_icon,
                step_type=step.step_type, query_template=step.query_template,
                dimension_hints=step.dimension_hints, expected_output=step.expected_output,
                is_auto_execute=step.is_auto_execute,
            ))

        # 复制所有维度
        for dim in source.dimensions:
            self.db.add(TemplateDimension(
                template_id=new_id, dimension_key=dim.dimension_key,
                dimension_name=dim.dimension_name, is_required=dim.is_required,
                sort_order=dim.sort_order,
            ))

        self.db.commit()
        self.db.refresh(cloned)
        return cloned
```

### 4.2 SOPRunService（运行编排）

```python
# services/sop_run_service.py
import uuid, time
from sqlalchemy.orm import Session
from models.template_models import Template, TemplateRun
from services.sop_step_executor import SOPStepExecutor

class SOPRunService:
    def __init__(self, db: Session):
        self.db = db
        self.executor = SOPStepExecutor()

    def get_template(self, template_id):
        return self.db.query(Template).filter(Template.id == template_id).first()

    def get_run(self, run_id):
        return self.db.query(TemplateRun).filter(TemplateRun.id == run_id).first()

    def create_run(self, template_id, user_id, params):
        run = TemplateRun(
            id=f'run_{uuid.uuid4().hex[:8]}',
            template_id=template_id, user_id=user_id,
            params=params, status='running', current_step=0, step_results=[],
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    async def execute_step(self, run_id, step_index, params):
        run = self.get_run(run_id)
        template = self.get_template(run.template_id)
        step = template.steps[step_index]

        # 调用执行器
        result = await self.executor.execute(
            step=step,
            template=template,
            params=params,
            previous_results=run.step_results,
            step_index=step_index,
        )

        # 保存结果
        step_results = run.step_results
        # 确保数组长度足够
        while len(step_results) <= step_index:
            step_results.append(None)
        step_results[step_index] = result.dict()
        run.step_results = step_results
        run.current_step = step_index

        # 如果是最后一步，标记完成
        if step_index == len(template.steps) - 1:
            run.status = 'completed'
            run.completed_at = datetime.utcnow()
            run.total_duration_ms = sum(r.get('duration_ms', 0) for r in step_results if r)

        self.db.commit()
        return result.dict()

    def list_runs(self, user_id, template_id=None, limit=20):
        query = self.db.query(TemplateRun).filter(TemplateRun.user_id == user_id)
        if template_id:
            query = query.filter(TemplateRun.template_id == template_id)
        return query.order_by(TemplateRun.started_at.desc()).limit(limit).all()
```

### 4.3 SOPStepExecutor（单步执行器）

```python
# services/sop_step_executor.py
from services.variable_replacer import VariableReplacer
from services.dependency_resolver import DependencyResolver
from workflow.orchestrator import Text2SQLWorkflow
from services.strategy_generator import StrategyGenerator

class SOPStepExecutor:
    def __init__(self):
        self.replacer = VariableReplacer()
        self.dependency = DependencyResolver()
        self.workflow = Text2SQLWorkflow()
        self.strategy_gen = StrategyGenerator()

    async def execute(self, step, template, params, previous_results, step_index):
        start_time = time.time()

        # 1. 变量替换
        prev_result = None
        if step_index > 0 and previous_results and previous_results[step_index - 1]:
            prev_result = self.dependency.extract_prev_result(
                previous_results[step_index - 1], step.step_type
            )

        replaced_question = self.replacer.replace(
            step.query_template,
            {**params, 'metric_key': template.metric_key},
            prev_result,
        )

        # 2. 根据步骤类型执行
        try:
            if step.step_type == 'strategy':
                # 策略步骤：基于前面结论生成建议
                result = await self.strategy_gen.generate(
                    previous_results[:step_index], template.name
                )
            else:
                # 普通步骤：调用Text2SQL
                result = await self._execute_nl2sql(replaced_question, params)

            result.status = 'success'

        except Exception as e:
            result = StepResult(status='failed', error=str(e))

        result.step_name = step.step_name
        result.step_type = step.step_type
        result.replaced_question = replaced_question
        result.duration_ms = int((time.time() - start_time) * 1000)
        return result

    async def _execute_nl2sql(self, question, params):
        # 复用现有Text2SQL Workflow（同步包装异步）
        context = WorkflowContext(question=question, brand_filter=params.get('brand', '全部'))
        events = []
        async for event in self.workflow.run(context):
            events.append(event)
        return self._parse_events(events, context)
```

---

## 五、Seed 数据（系统预设模板）

```python
# core/template_seed.py
def seed_preset_templates(db: Session):
    if db.query(Template).count() > 0:
        return  # 已有数据，不重复seed

    presets = [
        {
            'id': 'preset_exec_quarterly', 'name': '高管季度复盘',
            'description': '高管视角5步SOP：整体达成率→横向看品牌→下钻问题品牌-区域→下钻问题区域-车型→策略建议',
            'template_type': 'role_default', 'role': 'executive', 'sort_order': 1,
            'steps': [
                {'step_name': '整体达成率对标', 'step_icon': '🎯', 'step_type': 'overview',
                 'query_template': '{{time}}全集团的{{metric}}与预算目标达成率是多少？', 'expected_output': 'kpi'},
                {'step_name': '横向对比品牌', 'step_icon': '↔️', 'step_type': 'horizontal',
                 'query_template': '{{time}}各品牌的{{metric}}和营收对比，按达成率排序', 'expected_output': 'bar'},
                {'step_name': '下钻问题品牌-区域', 'step_icon': '🔍', 'step_type': 'drilldown',
                 'query_template': '达成率最低的品牌是{{prev_result}}，该品牌在各区域的{{metric}}表现如何？', 'expected_output': 'bar'},
                {'step_name': '下钻问题区域-车型', 'step_icon': '🔍', 'step_type': 'drilldown',
                 'query_template': '{{prev_result}}区域表现最差，该区域各车型的{{metric}}如何？', 'expected_output': 'table'},
                {'step_name': '策略建议', 'step_icon': '💡', 'step_type': 'strategy',
                 'query_template': '', 'expected_output': 'text'},
            ],
            'dimensions': [('brand', '品牌', 1), ('region', '区域', 0), ('model', '车型', 0), ('time', '时间', 1)],
        },
        # ... 其余4个预设模板（分析师深度下钻、区域总监KPI、车型经理产品复盘、新能源专项）
        # 完整数据见PRD第五章
    ]

    for preset in presets:
        template = Template(id=preset['id'], name=preset['name'], description=preset['description'],
                           template_type=preset['template_type'], role=preset['role'],
                           metric_key='delivered_units', creator='system', sort_order=preset['sort_order'])
        db.add(template)
        for i, step in enumerate(preset['steps']):
            db.add(TemplateStep(template_id=preset['id'], step_order=i, **step))
        for i, (dim_key, dim_name, is_req) in enumerate(preset['dimensions']):
            db.add(TemplateDimension(template_id=preset['id'], dimension_key=dim_key,
                                    dimension_name=dim_name, is_required=is_req, sort_order=i))

    db.commit()
```

---

## 六、与现有系统的集成

### 6.1 复用 Text2SQL Workflow

- 直接 import 现有的 `workflow.orchestrator.Text2SQLWorkflow`
- 不通过 HTTP 自调用 `/api/chat`，避免网络开销和循环依赖
- 传入 `WorkflowContext(question=replaced_question, brand_filter=params.brand)`

### 6.2 复用数据库

- 与现有系统共用同一个 SQLite `app.db`
- 4张新表（templates/template_steps/template_dimensions/template_runs）建在同一个库中
- 不影响现有表（badcases/history/audit_logs等）

### 6.3 复用用户鉴权

- 所有写操作（创建/更新/删除/运行）通过 `Depends(get_current_user)` 获取当前用户
- 模板的 creator 字段存用户名
- 运行记录的 user_id 存用户名

### 6.4 审计日志

- 模板的创建/更新/删除/克隆/运行操作写入现有审计日志表
- 通过现有审计中间件自动记录，不需要额外代码

---

## 七、错误处理

| HTTP状态码 | 场景 | 响应体 |
|---|---|---|
| 400 | 运行已完成不能再执行 / 参数校验失败 | `{detail: '错误信息'}` |
| 403 | 修改/删除系统预设模板 / 非本人模板 | `{detail: '权限不足'}` |
| 404 | 模板/运行记录不存在 | `{detail: '不存在'}` |
| 500 | Text2SQL执行异常（未被捕获） | `{detail: '服务器内部错误'}` |

**单步执行失败不返回500**：execute_step 接口总是返回200，结果中包含 `status: 'failed'` 和 `error` 字段，由前端决定展示重试/跳过。

---

## 八、部署与迁移

1. 应用启动时自动建表（`Base.metadata.create_all`）
2. 自动 seed 预设模板（表为空时）
3. 旧版本的模板数据（如果有）直接清空重建，不做迁移
4. 运行记录保留最近30天，可通过定时任务清理（可选，Phase 5实现）

---

> **后端SDD结束**。算法细节见 SDD-算法，前端对接见 SDD-前端。
