"""
指标字典数据访问层
提供统一的指标元数据读取接口，供 SOP 引擎等模块调用。
"""

import json
import os

_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_METRICS_PATH = os.path.join(_CURRENT_DIR, "metrics_dict.json")


def load_metrics() -> dict:
    """加载并返回指标字典的完整 JSON 数据结构"""
    if not os.path.exists(_METRICS_PATH):
        return {"version": "", "domain_group": "", "metrics": []}
    with open(_METRICS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_metric_by_id(metric_id: str) -> dict:
    """根据 metric_id 精确查找指标定义"""
    data = load_metrics()
    for m in data.get("metrics", []):
        if m.get("metric_id") == metric_id:
            return m
    return {}


def get_metric_by_name(metric_name: str) -> dict:
    """根据 metric_name 模糊查找指标定义"""
    data = load_metrics()
    for m in data.get("metrics", []):
        if metric_name in m.get("metric_name", ""):
            return m
    return {}
