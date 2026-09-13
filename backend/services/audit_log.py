"""
P2-4 + P2-7：审计日志 + Bad Case 反馈持久化
================================================
两张表：
  - audit_log：所有写操作审计（谁、什么时候、改了什么）
  - bad_case：用户对 AI 回答的负面反馈 + 修正口径

设计原则：
  - 全部走 DuckDB（与业务数据同库，无需额外存储）
  - append-only（audit log 不允许改写）
  - bad_case 与 semantic_term 关联，AI PM 采纳后可一键闭环
"""
import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import duckdb

# 与 sql_executor / data_manager 同源：使用同一个 duckdb 文件
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BACKEND_DIR, "data")
DUCKDB_PATH = os.path.join(DATA_DIR, "gac_bi.duckdb")


def _conn(write: bool = True):
    """获取 DuckDB 连接（写模式）"""
    os.makedirs(DATA_DIR, exist_ok=True)
    return duckdb.connect(DUCKDB_PATH, read_only=not write)


def _now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


# ========================================================
# 表创建（启动时调用一次）
# ========================================================
def ensure_audit_tables() -> None:
    """初始化审计 + Bad Case 表"""
    con = _conn()
    # 审计日志
    con.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id VARCHAR PRIMARY KEY,
            ts TIMESTAMP NOT NULL,
            actor VARCHAR NOT NULL,
            action VARCHAR NOT NULL,
            resource VARCHAR NOT NULL,
            resource_id VARCHAR,
            payload JSON,
            ip VARCHAR,
            note VARCHAR
        )
    """)
    con.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_ts
            ON audit_log(ts DESC)
    """)
    con.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_actor
            ON audit_log(actor, ts DESC)
    """)

    # Bad Case 反馈
    con.execute("""
        CREATE TABLE IF NOT EXISTS bad_case (
            id VARCHAR PRIMARY KEY,
            ts TIMESTAMP NOT NULL,
            actor VARCHAR NOT NULL,
            query TEXT NOT NULL,
            sql_text TEXT,
            result_summary TEXT,
            feedback_type VARCHAR NOT NULL,
            feedback_label VARCHAR,
            correction TEXT,
            resolved BOOLEAN DEFAULT FALSE,
            resolved_by VARCHAR,
            resolved_at TIMESTAMP,
            semantic_term_id VARCHAR
        )
    """)
    con.execute("""
        CREATE INDEX IF NOT EXISTS idx_badcase_ts
            ON bad_case(ts DESC)
    """)
    con.execute("""
        CREATE INDEX IF NOT EXISTS idx_badcase_resolved
            ON bad_case(resolved, ts DESC)
    """)


# ========================================================
# 审计日志写入
# ========================================================
def write_audit(
    *,
    actor: str,
    action: str,
    resource: str,
    resource_id: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
    ip: str = "127.0.0.1",
    note: Optional[str] = None,
) -> str:
    """写入一条审计日志，返回 id"""
    audit_id = f"audit-{uuid.uuid4().hex[:12]}"
    payload_json = json.dumps(payload or {}, ensure_ascii=False)
    con = _conn()
    con.execute(
        """
        INSERT INTO audit_log
            (id, ts, actor, action, resource, resource_id, payload, ip, note)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            audit_id,
            datetime.utcnow(),
            actor,
            action,
            resource,
            resource_id,
            payload_json,
            ip,
            note,
        ],
    )
    return audit_id


def list_audit(
    *,
    actor: Optional[str] = None,
    action: Optional[str] = None,
    resource: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """查询审计日志（按时间倒序）"""
    where: List[str] = []
    params: List[Any] = []
    if actor:
        where.append("actor = ?")
        params.append(actor)
    if action:
        where.append("action = ?")
        params.append(action)
    if resource:
        where.append("resource = ?")
        params.append(resource)
    where_clause = ("WHERE " + " AND ".join(where)) if where else ""

    con = _conn()
    rows = con.execute(
        f"""
        SELECT id, ts, actor, action, resource, resource_id, payload, ip, note
        FROM audit_log
        {where_clause}
        ORDER BY ts DESC
        LIMIT ?
        """,
        [*params, limit],
    ).fetchall()

    items = []
    for r in rows:
        items.append(
            {
                "id": r[0],
                "ts": r[1].isoformat() if hasattr(r[1], "isoformat") else str(r[1]),
                "actor": r[2],
                "action": r[3],
                "resource": r[4],
                "resource_id": r[5],
                "payload": json.loads(r[6]) if r[6] else {},
                "ip": r[7],
                "note": r[8],
            }
        )
    return items


def audit_stats() -> Dict[str, Any]:
    """审计统计概览"""
    con = _conn()
    total = con.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
    today = con.execute(
        """
        SELECT COUNT(*) FROM audit_log
        WHERE ts >= CURRENT_DATE
        """
    ).fetchone()[0]
    by_actor = con.execute(
        """
        SELECT actor, COUNT(*) AS cnt
        FROM audit_log
        GROUP BY actor
        ORDER BY cnt DESC
        LIMIT 10
        """
    ).fetchall()
    by_action = con.execute(
        """
        SELECT action, COUNT(*) AS cnt
        FROM audit_log
        GROUP BY action
        ORDER BY cnt DESC
        """
    ).fetchall()
    by_resource = con.execute(
        """
        SELECT resource, COUNT(*) AS cnt
        FROM audit_log
        GROUP BY resource
        ORDER BY cnt DESC
        """
    ).fetchall()
    return {
        "total": total,
        "today": today,
        "by_actor": [{"actor": a, "count": c} for a, c in by_actor],
        "by_action": [{"action": a, "count": c} for a, c in by_action],
        "by_resource": [{"resource": a, "count": c} for a, c in by_resource],
    }


# ========================================================
# Bad Case 反馈
# ========================================================
def submit_bad_case(
    *,
    actor: str,
    query: str,
    sql_text: Optional[str] = None,
    result_summary: Optional[str] = None,
    feedback_type: str,   # 'positive' | 'negative' | 'correction'
    feedback_label: Optional[str] = None,
    correction: Optional[str] = None,
) -> str:
    """提交一条反馈，返回 id"""
    case_id = f"bc-{uuid.uuid4().hex[:12]}"
    con = _conn()
    con.execute(
        """
        INSERT INTO bad_case
            (id, ts, actor, query, sql_text, result_summary,
             feedback_type, feedback_label, correction, resolved)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, FALSE)
        """,
        [
            case_id,
            datetime.utcnow(),
            actor,
            query,
            sql_text,
            result_summary,
            feedback_type,
            feedback_label,
            correction,
        ],
    )
    return case_id


def list_bad_case(
    *,
    feedback_type: Optional[str] = None,
    resolved: Optional[bool] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """查询 Bad Case 列表（按时间倒序）"""
    where: List[str] = []
    params: List[Any] = []
    if feedback_type:
        where.append("feedback_type = ?")
        params.append(feedback_type)
    if resolved is not None:
        where.append("resolved = ?")
        params.append(resolved)
    where_clause = ("WHERE " + " AND ".join(where)) if where else ""

    con = _conn()
    rows = con.execute(
        f"""
        SELECT id, ts, actor, query, sql_text, result_summary,
               feedback_type, feedback_label, correction,
               resolved, resolved_by, resolved_at, semantic_term_id
        FROM bad_case
        {where_clause}
        ORDER BY ts DESC
        LIMIT ?
        """,
        [*params, limit],
    ).fetchall()

    items = []
    for r in rows:
        items.append(
            {
                "id": r[0],
                "ts": r[1].isoformat() if hasattr(r[1], "isoformat") else str(r[1]),
                "actor": r[2],
                "query": r[3],
                "sql_text": r[4],
                "result_summary": r[5],
                "feedback_type": r[6],
                "feedback_label": r[7],
                "correction": r[8],
                "resolved": r[9],
                "resolved_by": r[10],
                "resolved_at": r[11].isoformat() if r[11] and hasattr(r[11], "isoformat") else r[11],
                "semantic_term_id": r[12],
            }
        )
    return items


def resolve_bad_case(
    *,
    case_id: str,
    resolved_by: str,
    semantic_term_id: Optional[str] = None,
) -> bool:
    """闭环 Bad Case：标记已解决 + 关联语义层 term"""
    con = _conn()
    con.execute(
        """
        UPDATE bad_case
        SET resolved = TRUE,
            resolved_by = ?,
            resolved_at = CURRENT_TIMESTAMP,
            semantic_term_id = ?
        WHERE id = ?
        """,
        [resolved_by, semantic_term_id, case_id],
    )
    return True


def bad_case_stats() -> Dict[str, Any]:
    """Bad Case 统计概览"""
    con = _conn()
    total = con.execute("SELECT COUNT(*) FROM bad_case").fetchone()[0]
    resolved = con.execute(
        "SELECT COUNT(*) FROM bad_case WHERE resolved = TRUE"
    ).fetchone()[0]
    by_type = con.execute(
        """
        SELECT feedback_type, COUNT(*) AS cnt
        FROM bad_case
        GROUP BY feedback_type
        ORDER BY cnt DESC
        """
    ).fetchall()
    by_label = con.execute(
        """
        SELECT feedback_label, COUNT(*) AS cnt
        FROM bad_case
        WHERE feedback_label IS NOT NULL
        GROUP BY feedback_label
        ORDER BY cnt DESC
        LIMIT 10
        """
    ).fetchall()
    return {
        "total": total,
        "resolved": resolved,
        "open": total - resolved,
        "by_type": [{"feedback_type": a, "count": c} for a, c in by_type],
        "by_label": [{"feedback_label": a, "count": c} for a, c in by_label],
    }
