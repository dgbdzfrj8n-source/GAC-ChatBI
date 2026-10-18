"""
归因模板中心 v3 数据模型（Pydantic v2）

约定：
- 时间字段：datetime
- 枚举：StrEnum（与 DB 字符串对齐）
- 业务字段全部 Optional，避免老数据缺字段报错
"""
from __future__ import annotations

import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict


# =====================================================================
# 枚举
# =====================================================================
class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class StepType(str, Enum):
    NL2SQL = "nl2sql"               # 自然语言 → SQL → 数据
    STRATEGY = "strategy"           # 选策略（如同环比/TopN）
    AGGREGATION = "aggregation"     # 聚合中间结果
    CONCLUSION = "conclusion"       # LLM 写结论
    LLM_DIRECT = "llm_direct"       # 直接 LLM 推理


class VersionStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"


class TemplateCategory(str, Enum):
    SALES = "销售归因"
    MARKETING = "市场归因"
    INVENTORY = "库存归因"
    CHANNEL = "渠道归因"
    CUSTOM = "自定义"


# =====================================================================
# 步骤定义（StepSpec）— 模板里的步骤 schema
# =====================================================================
class StepVariable(BaseModel):
    """用户需要填的变量"""
    model_config = ConfigDict(extra="forbid")
    name: str = Field(..., description="变量名（英文）")
    label: str = Field(..., description="展示名（中文）")
    type: str = Field(..., description="string/number/date/select")
    required: bool = Field(default=True)
    default: Optional[Any] = None
    options: Optional[List[str]] = Field(default=None, description="select 时使用")


class StepSpec(BaseModel):
    """单步定义"""
    model_config = ConfigDict(extra="forbid")
    name: str = Field(..., description="步骤中文名")
    type: StepType
    description: str = Field(default="", description="步骤业务说明")
    # 1) NL2SQL 步骤
    question: Optional[str] = Field(default=None, description="NL2SQL 子问题模板，支持 {var}")
    metrics: Optional[List[str]] = Field(default=None, description="涉及指标名（用于 schema 剪枝）")
    dimensions: Optional[List[str]] = Field(default=None, description="涉及维度")
    # 2) Strategy 步骤
    strategy: Optional[str] = Field(default=None, description="策略名：qoq/mom/yoy/topn/diff")
    # 3) Aggregation 步骤
    aggregation: Optional[str] = Field(default=None, description="sum/avg/count/min/max")
    group_by: Optional[List[str]] = Field(default=None, description="分组字段")
    # 4) Conclusion 步骤
    prompt: Optional[str] = Field(default=None, description="LLM 提示词模板")
    # 5) 通用
    variables: List[StepVariable] = Field(default_factory=list)
    depends_on: List[str] = Field(default_factory=list, description="依赖的前置步骤 name")


# =====================================================================
# 实体模型（与 DB 行对齐）
# =====================================================================
class Template(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    template_id: str
    name: str
    code: str
    description: str = ""
    category: str = ""
    tags: List[str] = Field(default_factory=list)
    current_version: int = 1
    is_archived: bool = False
    is_builtin: bool = False
    created_by: str = ""
    created_at: datetime.datetime
    updated_at: datetime.datetime


class TemplateVersion(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    template_id: str
    version: int
    steps: List[Dict[str, Any]]  # 解析后的 StepSpec 列表（保持 Dict 以便前端灵活）
    status: str
    changelog: str = ""
    created_by: str = ""
    created_at: datetime.datetime


class TemplateRun(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    run_id: str
    template_id: str
    template_version: int
    user_query: str
    params: Dict[str, Any] = Field(default_factory=dict)
    status: str
    total_steps: int
    completed_steps: int = 0
    summary: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime.datetime] = None
    finished_at: Optional[datetime.datetime] = None
    duration_ms: Optional[int] = None
    created_by: str = ""
    created_at: datetime.datetime


class StepExecution(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    step_execution_id: str
    run_id: str
    step_index: int
    step_name: str
    step_type: str
    input_data: Dict[str, Any] = Field(default_factory=dict)
    output_data: Optional[Dict[str, Any]] = None
    status: str
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None
    created_at: datetime.datetime


# =====================================================================
# API 请求/响应模型
# =====================================================================
class TemplateCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=50, pattern=r"^[a-z0-9_]+$")
    description: str = ""
    category: str = "自定义"
    tags: List[str] = Field(default_factory=list)
    steps: List[Dict[str, Any]] = Field(..., min_length=1)


class TemplateUpdateRequest(BaseModel):
    """修改元信息"""
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None


class TemplatePublishVersionRequest(BaseModel):
    steps: List[Dict[str, Any]] = Field(..., min_length=1)
    changelog: str = ""


class TemplateRunCreateRequest(BaseModel):
    user_query: str = Field(..., min_length=1)
    params: Dict[str, Any] = Field(default_factory=dict)


class TemplateListResponse(BaseModel):
    items: List[Template]
    total: int


class TemplateRunListResponse(BaseModel):
    items: List[TemplateRun]
    total: int


class StepExecutionListResponse(BaseModel):
    items: List[StepExecution]
    total: int


class TemplateRunDetailResponse(BaseModel):
    run: TemplateRun
    steps: List[StepExecution]
