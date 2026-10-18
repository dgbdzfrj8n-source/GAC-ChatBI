"""
归因模板 v3 - 元信息路由
端点：
  GET /api/template-center/categories    分类字典
  GET /api/template-center/step-types    步骤类型字典
  GET /api/template-center/health        健康检查
"""
import os
import sys

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from fastapi import APIRouter, Depends

from core.auth import CurrentUser, get_current_user
from services.sop import TemplateCategory, StepType
from config import get_settings
import duckdb

router = APIRouter(prefix="/api/template-center", tags=["template-center"])


@router.get("/categories")
def list_categories(user: CurrentUser = Depends(get_current_user)):
    return {
        "items": [
            {"value": c.value, "label": c.value}
            for c in TemplateCategory
        ]
    }


@router.get("/step-types")
def list_step_types(user: CurrentUser = Depends(get_current_user)):
    return {
        "items": [
            {
                "value": t.value,
                "label": {
                    "nl2sql": "自然语言查询",
                    "strategy": "策略选择",
                    "aggregation": "数据聚合",
                    "conclusion": "AI 结论",
                    "llm_direct": "LLM 直接推理",
                }.get(t.value, t.value),
                "description": {
                    "nl2sql": "将自然语言转为 SQL 并执行",
                    "strategy": "在前几步数据上选策略（TopN/同比/环比）",
                    "aggregation": "对数据做聚合（sum/avg/diff）",
                    "conclusion": "用 LLM 写经营结论",
                    "llm_direct": "直接调 LLM 完成推理",
                }.get(t.value, ""),
            }
            for t in StepType
        ]
    }


@router.get("/health")
def health_check():
    """不需鉴权，单纯健康检查"""
    settings = get_settings()
    try:
        con = duckdb.connect(settings.DATABASE_PATH, read_only=True)
        # 检查 4 张 v3 表
        tables = con.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_name IN ('attribution_template','attribution_template_version',"
            "  'attribution_template_run','attribution_step_execution')"
        ).fetchall()
        con.close()
        return {
            "status": "healthy",
            "v3_tables_present": [t[0] for t in tables],
            "missing": ["4 张 v3 表"] if len(tables) < 4 else [],
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
