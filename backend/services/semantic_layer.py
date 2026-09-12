"""P2-2: 语义层（Semantic Layer）服务

设计目标：
  1. 把"指标定义 / 维度字段 / 业务同义词"三层语义资产集中管理
  2. 维度层自动从 schema_linker 的 TABLE_DEFINITIONS 抽取字段，免维护
  3. 提供编辑接口 + 模拟问数预览，让业务分析师在 UI 里直接调整 NL2SQL 召回口径
  4. 编辑结果直接写回 metrics_dict.json / glossary.json（运行时生效）

调用方：
  - GET    /api/semantic             → 完整三层快照
  - PUT    /api/semantic/metrics/{id} → 编辑指标
  - PUT    /api/semantic/glossary/{name} → 编辑术语
  - POST   /api/semantic/preview     → 模拟问数召回
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

# 路径
CURRENT_DIR = Path(__file__).parent.parent  # backend/
METRICS_PATH = CURRENT_DIR / "core" / "metrics_dict.json"
GLOSSARY_PATH = CURRENT_DIR / "knowledge" / "glossary.json"

# 维度层：从 schema_linker 自动抽取（单一数据源）
try:
    from core.schema_linker import TABLE_DEFINITIONS, KEYWORD_MAPPING
except ImportError:
    TABLE_DEFINITIONS = {}
    KEYWORD_MAPPING = {}


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(path: Path, data: Dict[str, Any]) -> None:
    """原子写：保持磁盘文件紧凑格式 + 清掉运行时元字段

    indent=2 会让内部数组也展开（diff 噪音）。我们的解决方案：
    1) 用 indent=2 写出可读格式
    2) 二次正则：把所有内部数组 [\\n  "a",\\n  "b"\\n] 压缩成 ["a", "b"]
    """
    # 清理运行时元字段（仅 UI 展示用，不写盘）
    for collection in ("metrics", "terms"):
        for item in data.get(collection, []):
            item.pop("_last_modified", None)
            item.pop("_modified_fields", None)

    raw = json.dumps(data, ensure_ascii=False, indent=2)

    # 把展开的字符串数组压回 ["a", "b"] 紧凑形式
    import re as _re
    def _compact_array(match):
        items = _re.findall(r'"(?:[^"\\]|\\.)*"', match.group(1))
        return "[" + ", ".join(items) + "]"
    raw = _re.sub(r'\[\s*((?:"(?:[^"\\]|\\.)*"(?:\s*,\s*)?\s*)+)\]', _compact_array, raw)

    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(raw + "\n", encoding="utf-8")
    tmp.replace(path)


def extract_dimensions() -> List[Dict[str, Any]]:
    """
    从 schema_linker 自动抽取维度字段清单
    返回: [{table, field, type, description, synonyms, domain}, ...]
    """
    dims: List[Dict[str, Any]] = []
    # 表 → 业务域 映射
    table_domain = {
        "fact_sales_daily": "整车销售",
        "dim_budget_target": "经营财务",
        "fact_marketing_expenses": "市场营销",
    }
    for table, meta in TABLE_DEFINITIONS.items():
        for col_def in meta.get("columns", []):
            # 解析 "field_name TYPE (描述)"
            m = re.match(r"^(\w+)\s+(\w+(?:\([^)]+\))?)\s*(?:\((.+)\))?", col_def.strip())
            if not m:
                continue
            field, ftype, desc = m.group(1), m.group(2), m.group(3) or ""
            # 解析括号内的同义词
            syn_m = re.search(r"[:：](.+?)(?:[，。]|$)", desc)
            synonyms = []
            if syn_m:
                synonyms = [s.strip() for s in re.split(r"[、,，/]", syn_m.group(1)) if s.strip()]
            dims.append({
                "table": table,
                "field": field,
                "type": ftype,
                "description": desc.strip(),
                "synonyms": synonyms,
                "domain": table_domain.get(table, "其他"),
            })
    return dims


def get_full_snapshot() -> Dict[str, Any]:
    """返回三层完整快照"""
    metrics_doc = _load_json(METRICS_PATH)
    glossary_doc = _load_json(GLOSSARY_PATH)
    return {
        "version": metrics_doc.get("version", "1.0.0"),
        "domain_group": metrics_doc.get("domain_group", ""),
        "metrics": metrics_doc.get("metrics", []),
        "dimensions": extract_dimensions(),
        "glossary": glossary_doc.get("terms", []),
    }


def update_metric(metric_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """编辑指标（按 metric_id 匹配，definition/calculation_rule/example_query 三字段可改）

    返回值带 _last_modified / _modified_fields 给前端展示，但磁盘上不保留这些元字段
    """
    doc = _load_json(METRICS_PATH)
    target = None
    for m in doc.get("metrics", []):
        if m.get("metric_id") == metric_id:
            target = m
            break
    if not target:
        raise ValueError(f"指标 {metric_id} 不存在")

    allowed_keys = {"definition", "calculation_rule", "example_query"}
    changed = []
    for k, v in updates.items():
        if k in allowed_keys and v is not None:
            target[k] = v
            changed.append(k)

    # 写盘（清掉元字段，保持磁盘文件干净）
    _save_json(METRICS_PATH, doc)

    # 返回给前端的副本含 UI 元字段
    import copy
    ret = copy.deepcopy(target)
    ret["_last_modified"] = datetime.now().isoformat(timespec="seconds")
    ret["_modified_fields"] = changed
    return ret


def update_glossary(term_name: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """编辑术语（按 name 匹配）"""
    doc = _load_json(GLOSSARY_PATH)
    target = None
    for t in doc.get("terms", []):
        if t.get("name") == term_name:
            target = t
            break
    if not target:
        raise ValueError(f"术语 {term_name} 不存在")

    allowed_keys = {"definition", "synonyms", "related_metrics"}
    changed = []
    for k, v in updates.items():
        if k in allowed_keys and v is not None:
            target[k] = v
            changed.append(k)

    _save_json(GLOSSARY_PATH, doc)

    import copy
    ret = copy.deepcopy(target)
    ret["_last_modified"] = datetime.now().isoformat(timespec="seconds")
    ret["_modified_fields"] = changed
    return ret


def preview_query(query: str) -> Dict[str, Any]:
    """
    模拟问数：用当前语义层跑一遍 RAG 召回，返回命中的指标/术语
    召回策略：
      1. 指标名精确包含（权重 5）
      2. 指标定义/公式中的关键词命中（权重 1/词）
      3. 同义词命中：业务术语的 synonyms 命中 query 中的中文词（权重 3）
      4. 反向：query 中的词在术语定义中出现（权重 2）
    """
    snapshot = get_full_snapshot()
    q_lower = query.lower()

    # 先把所有术语的"别名集合"摊平（包含 name + synonyms）
    term_aliases: Dict[str, List[str]] = {}
    for t in snapshot["glossary"]:
        aliases = [t["name"]] + t.get("synonyms", [])
        term_aliases[t["name"]] = aliases

    # 把 query 分词成中文 2-gram（命中术语/指标更稳）
    query_words = set()
    for i in range(len(query)):
        query_words.add(query[i])
        if i + 2 <= len(query):
            query_words.add(query[i:i + 2])

    # 1. 匹配指标
    matched_metrics = []
    for m in snapshot["metrics"]:
        score = 0
        reasons = []
        name = m.get("metric_name", "")
        # 指标名精确包含
        if name and name in query:
            score += 5
            reasons.append(f"含指标名「{name}」")
        # 指标名 2-gram 命中
        for i in range(len(name) - 1):
            if name[i:i + 2] in query:
                score += 2
                reasons.append(f"指标词「{name[i:i+2]}」")
                break
        # 同义词兜底：query 里有术语 → 该术语关联的指标加分
        for term_name, aliases in term_aliases.items():
            hit_aliases = [a for a in aliases if a and a in query]
            if hit_aliases and m["metric_id"] in [r for t in snapshot["glossary"] if t["name"] == term_name for r in t.get("related_metrics", [])]:
                score += 3
                reasons.append(f"术语「{term_name}」({'/'.join(hit_aliases)}) 关联到本指标")
        # 计算规则 + 定义关键词
        keywords = re.findall(r"[\u4e00-\u9fa5]{2,}", m.get("calculation_rule", "") + m.get("definition", ""))
        kw_hits = [kw for kw in keywords[:8] if kw in query]
        if kw_hits:
            score += len(kw_hits)
            reasons.append(f"关键词「{'/'.join(kw_hits[:3])}」")
        if score > 0:
            matched_metrics.append({
                "metric_id": m["metric_id"],
                "metric_name": m["metric_name"],
                "business_domain": m.get("business_domain", ""),
                "score": score,
                "reasons": reasons[:3],
                "sample_sql": m.get("example_query"),
            })
    matched_metrics.sort(key=lambda x: -x["score"])

    # 2. 匹配术语
    matched_terms = []
    for t in snapshot["glossary"]:
        score = 0
        reasons = []
        if t["name"] in query:
            score += 5
            reasons.append(f"含术语名「{t['name']}」")
        for syn in t.get("synonyms", []):
            if syn and syn in query:
                score += 3
                reasons.append(f"含同义词「{syn}」")
                break
        if score > 0:
            matched_terms.append({
                "name": t["name"],
                "definition": t.get("definition", ""),
                "synonyms": t.get("synonyms", []),
                "related_metrics": t.get("related_metrics", []),
                "score": score,
                "reasons": reasons,
            })
    matched_terms.sort(key=lambda x: -x["score"])

    return {
        "query": query,
        "matched_metrics": matched_metrics[:3],
        "matched_terms": matched_terms[:3],
        "sample_sql": matched_metrics[0]["sample_sql"] if matched_metrics else None,
    }
