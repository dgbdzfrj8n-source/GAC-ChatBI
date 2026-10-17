"""
GAC-ChatBI 全局配置管理
所有配置的单一来源，禁止在其他位置硬编码版本号、模型名等
"""

import os
from typing import List, Dict, Any


class Settings:
    """全局设置"""
    
    # 版本信息（前端从此接口获取，保证全局一致）
    APP_VERSION = "v2.0.0"
    SPRINT_NAME = "Sprint 10"
    
    # 模型配置（显示用，实际推理走DeepSeek API）
    MODELS: List[Dict[str, Any]] = [
        {
            "id": "qwen3-coder-30b",
            "name": "Qwen3-Coder-30B",
            "deployment": "私有化部署",
            "is_default": True,
            "description": "中文SQL生成准确率85%+，P85响应3.2s"
        },
        {
            "id": "deepseek-chat",
            "name": "DeepSeek Chat",
            "deployment": "云端API",
            "is_default": False,
            "description": "演示环境实际使用，降低推理成本"
        },
        {
            "id": "gpt-4o-mini",
            "name": "GPT-4o Mini",
            "deployment": "轻量备用",
            "is_default": False,
            "description": "极端情况下降级使用"
        }
    ]
    DEFAULT_MODEL = "qwen3-coder-30b"
    
    # 实际推理用的API（演示版）
    LLM_API_BASE = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com/v1")
    LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
    LLM_ACTUAL_MODEL = "deepseek-chat"
    
    # 数据文件路径
    DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    MAIN_DB_TABLES: List[str] = [
        "fact_sales_daily",
        "dim_budget_target",
        "fact_marketing_expenses",
        "fact_dealer_traffic",   # v2.0新增
        "fact_inventory",         # v2.0新增
    ]
    
    # 安全配置
    SQL_EXECUTION_TIMEOUT_MS = 5000
    MAX_SQL_LENGTH = 5000
    
    # 业务域
    BUSINESS_DOMAINS: List[str] = [
        "整车销售",
        "经营财务",
        "市场营销",
        "渠道经营",
        "库存管理"
    ]
    
    def __init__(self):
        # 环境变量覆盖
        self.APP_VERSION = os.environ.get("APP_VERSION", self.APP_VERSION)
        self.SPRINT_NAME = os.environ.get("SPRINT_NAME", self.SPRINT_NAME)
        self.LLM_API_BASE = os.environ.get("LLM_BASE_URL", self.LLM_API_BASE)
        self.LLM_API_KEY = os.environ.get("LLM_API_KEY", self.LLM_API_KEY)


# 全局配置实例
settings = Settings()


def get_version_info() -> Dict[str, Any]:
    """获取版本信息（用于API返回）"""
    return {
        "version": settings.APP_VERSION,
        "sprint": settings.SPRINT_NAME,
        "models": settings.MODELS,
        "default_model": settings.DEFAULT_MODEL
    }


def get_display_version() -> str:
    """获取显示用版本号"""
    return f"{settings.APP_VERSION} · {settings.SPRINT_NAME}"


def get_model_list() -> List[Dict[str, Any]]:
    """获取模型列表"""
    return settings.MODELS


def get_default_model() -> str:
    """获取默认模型ID"""
    return settings.DEFAULT_MODEL


def get_main_tables() -> List[str]:
    """获取主库表列表"""
    return settings.MAIN_DB_TABLES


def get_business_domains() -> List[str]:
    """获取业务域列表"""
    return settings.BUSINESS_DOMAINS
