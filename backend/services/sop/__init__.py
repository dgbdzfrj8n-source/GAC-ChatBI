"""
归因模板中心 v3 服务包
=====================

按 SDD v3 实现：

- `models`：Pydantic v2 数据模型（Template/Version/Run/StepExecution）
- `template_db`：DuckDB 数据访问层（4 张表）
- `seed_templates`：5 个内置 seed
- 后续：`template_executor` / `step_executor`（执行引擎，Phase B 后续）

设计原则：
1. 复用 `workflow.orchestrator.Text2SQLWorkflow`，**不重新实现 NL2SQL**
2. 同步返回结果写入 DuckDB（异步执行由 Phase C 前端轮询）
3. 单步失败不阻断整体，由前端决定重试 / 跳过
4. DuckDB 作为数据底座（与 .cursorrules 一致）
"""

from .models import (
    Template,
    TemplateVersion,
    TemplateRun,
    StepExecution,
    StepSpec,
    StepVariable,
    RunStatus,
    StepStatus,
    StepType,
    VersionStatus,
    TemplateCategory,
    TemplateCreateRequest,
    TemplateUpdateRequest,
    TemplatePublishVersionRequest,
    TemplateRunCreateRequest,
    TemplateListResponse,
    TemplateRunListResponse,
    StepExecutionListResponse,
    TemplateRunDetailResponse,
)
from .template_db import TemplateDB

__all__ = [
    # 实体
    "Template",
    "TemplateVersion",
    "TemplateRun",
    "StepExecution",
    "StepSpec",
    "StepVariable",
    # 枚举
    "RunStatus",
    "StepStatus",
    "StepType",
    "VersionStatus",
    "TemplateCategory",
    # API 模型
    "TemplateCreateRequest",
    "TemplateUpdateRequest",
    "TemplatePublishVersionRequest",
    "TemplateRunCreateRequest",
    "TemplateListResponse",
    "TemplateRunListResponse",
    "StepExecutionListResponse",
    "TemplateRunDetailResponse",
    # 数据访问
    "TemplateDB",
]
