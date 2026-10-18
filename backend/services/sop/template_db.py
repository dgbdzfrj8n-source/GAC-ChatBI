"""
归因模板中心 v3 - DuckDB 数据访问层

职责：
1. 4 张表的 CRUD
2. version 快照的发布/回滚
3. run 生命周期管理

设计原则：
- 全部使用 DuckDB 原生 SQL
- 软删除（is_archived）而非物理删除
- 写入走参数化（防注入）
- 读操作走工具方法
"""
from __future__ import annotations

import json
import uuid
import datetime
from typing import Any, Dict, List, Optional

import duckdb

from .models import (
    Template,
    TemplateVersion,
    TemplateRun,
    StepExecution,
    RunStatus,
    StepStatus,
    StepType,
    VersionStatus,
)


class TemplateDB:
    """模板中心 DuckDB 数据访问层（单例友好）"""

    def __init__(self, db_path: str):
        self.db_path = db_path

    # ---------- 连接辅助 ----------
    def _conn(self) -> duckdb.DuckDBPyConnection:
        return duckdb.connect(self.db_path, read_only=False)

    # =====================================================================
    # 模板定义（attribution_template）
    # =====================================================================
    def create_template(
        self,
        name: str,
        code: str,
        description: str,
        category: str,
        tags: List[str],
        steps: List[Dict[str, Any]],
        created_by: str,
        is_builtin: bool = False,
        status: str = "draft",
    ) -> Template:
        """创建模板 + 第一版快照。返回 Template（含 version=1）"""
        template_id = f"tpl_{uuid.uuid4().hex[:12]}"
        now = datetime.datetime.now()
        steps_json = json.dumps(steps, ensure_ascii=False)

        with self._conn() as con:
            con.execute(
                """
                INSERT INTO attribution_template
                    (template_id, name, code, description, category, tags,
                     current_version, is_archived, is_builtin, created_by, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 1, FALSE, ?, ?, ?, ?)
                """,
                [template_id, name, code, description, category, json.dumps(tags, ensure_ascii=False),
                 is_builtin, created_by, now, now],
            )
            con.execute(
                """
                INSERT INTO attribution_template_version
                    (template_id, version, steps_json, status, changelog, created_by, created_at)
                VALUES (?, 1, ?, ?, ?, ?, ?)
                """,
                [template_id, steps_json, status, "初始版本", created_by, now],
            )

        return self.get_template(template_id)

    def get_template(self, template_id: str) -> Optional[Template]:
        with self._conn() as con:
            row = con.execute(
                "SELECT * FROM attribution_template WHERE template_id = ?",
                [template_id],
            ).fetchone()
            if not row:
                return None
            return self._row_to_template(row)

    def get_template_by_code(self, code: str) -> Optional[Template]:
        with self._conn() as con:
            row = con.execute(
                "SELECT * FROM attribution_template WHERE code = ? AND is_archived = FALSE",
                [code],
            ).fetchone()
            if not row:
                return None
            return self._row_to_template(row)

    def list_templates(
        self,
        category: Optional[str] = None,
        keyword: Optional[str] = None,
        include_archived: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Template]:
        sql = "SELECT * FROM attribution_template WHERE 1=1"
        params: List[Any] = []
        if not include_archived:
            sql += " AND is_archived = FALSE"
        if category:
            sql += " AND category = ?"
            params.append(category)
        if keyword:
            sql += " AND (name LIKE ? OR code LIKE ? OR description LIKE ?)"
            kw = f"%{keyword}%"
            params.extend([kw, kw, kw])
        sql += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        with self._conn() as con:
            rows = con.execute(sql, params).fetchall()
            return [self._row_to_template(r) for r in rows]

    def update_template(
        self,
        template_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        updated_by: str = "",
    ) -> Optional[Template]:
        """仅更新元信息；steps 修改走 publish_new_version"""
        fields, params = [], []
        if name is not None:
            fields.append("name = ?"); params.append(name)
        if description is not None:
            fields.append("description = ?"); params.append(description)
        if category is not None:
            fields.append("category = ?"); params.append(category)
        if tags is not None:
            fields.append("tags = ?"); params.append(json.dumps(tags, ensure_ascii=False))
        if not fields:
            return self.get_template(template_id)
        fields.append("updated_at = ?")
        params.append(datetime.datetime.now())
        params.append(template_id)
        with self._conn() as con:
            con.execute(
                f"UPDATE attribution_template SET {', '.join(fields)} WHERE template_id = ?",
                params,
            )
        return self.get_template(template_id)

    def publish_new_version(
        self,
        template_id: str,
        steps: List[Dict[str, Any]],
        changelog: str,
        created_by: str,
    ) -> int:
        """发布新版本：current_version + 1，写入新快照"""
        with self._conn() as con:
            row = con.execute(
                "SELECT current_version FROM attribution_template WHERE template_id = ?",
                [template_id],
            ).fetchone()
            if not row:
                raise ValueError(f"Template not found: {template_id}")
            new_version = row[0] + 1
            now = datetime.datetime.now()
            con.execute(
                """
                INSERT INTO attribution_template_version
                    (template_id, version, steps_json, status, changelog, created_by, created_at)
                VALUES (?, ?, ?, 'published', ?, ?, ?)
                """,
                [template_id, new_version, json.dumps(steps, ensure_ascii=False), changelog, created_by, now],
            )
            con.execute(
                "UPDATE attribution_template SET current_version = ?, updated_at = ? WHERE template_id = ?",
                [new_version, now, template_id],
            )
            return new_version

    def archive_template(self, template_id: str) -> bool:
        with self._conn() as con:
            cur = con.execute(
                "UPDATE attribution_template SET is_archived = TRUE, updated_at = ? WHERE template_id = ?",
                [datetime.datetime.now(), template_id],
            )
            # DuckDB 的 rowcount 不一定准，回查
            row = con.execute(
                "SELECT is_archived FROM attribution_template WHERE template_id = ?",
                [template_id],
            ).fetchone()
            return row is not None and row[0]

    # =====================================================================
    # 模板版本（attribution_template_version）
    # =====================================================================
    def get_version(self, template_id: str, version: int) -> Optional[TemplateVersion]:
        with self._conn() as con:
            row = con.execute(
                "SELECT * FROM attribution_template_version WHERE template_id = ? AND version = ?",
                [template_id, version],
            ).fetchone()
            if not row:
                return None
            return self._row_to_version(row)

    def get_current_version(self, template_id: str) -> Optional[TemplateVersion]:
        tpl = self.get_template(template_id)
        if not tpl:
            return None
        return self.get_version(template_id, tpl.current_version)

    def list_versions(self, template_id: str) -> List[TemplateVersion]:
        with self._conn() as con:
            rows = con.execute(
                "SELECT * FROM attribution_template_version WHERE template_id = ? ORDER BY version DESC",
                [template_id],
            ).fetchall()
            return [self._row_to_version(r) for r in rows]

    # =====================================================================
    # 运行实例（attribution_template_run）
    # =====================================================================
    def create_run(
        self,
        template_id: str,
        template_version: int,
        user_query: str,
        params: Dict[str, Any],
        total_steps: int,
        created_by: str,
    ) -> TemplateRun:
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        now = datetime.datetime.now()
        with self._conn() as con:
            con.execute(
                """
                INSERT INTO attribution_template_run
                    (run_id, template_id, template_version, user_query, params_json,
                     status, total_steps, completed_steps, started_at, created_by, created_at)
                VALUES (?, ?, ?, ?, ?, 'pending', ?, 0, ?, ?, ?)
                """,
                [run_id, template_id, template_version, user_query,
                 json.dumps(params, ensure_ascii=False), total_steps, now, created_by, now],
            )
        run = self.get_run(run_id)
        assert run is not None
        return run

    def get_run(self, run_id: str) -> Optional[TemplateRun]:
        with self._conn() as con:
            row = con.execute(
                "SELECT * FROM attribution_template_run WHERE run_id = ?",
                [run_id],
            ).fetchone()
            if not row:
                return None
            return self._row_to_run(row)

    def list_runs(
        self,
        template_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[TemplateRun]:
        sql = "SELECT * FROM attribution_template_run WHERE 1=1"
        params: List[Any] = []
        if template_id:
            sql += " AND template_id = ?"; params.append(template_id)
        if status:
            sql += " AND status = ?"; params.append(status)
        sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        with self._conn() as con:
            rows = con.execute(sql, params).fetchall()
            return [self._row_to_run(r) for r in rows]

    def update_run_status(
        self,
        run_id: str,
        status: str,
        completed_steps: Optional[int] = None,
        summary: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ) -> None:
        fields, params = ["status = ?"], [status]
        if completed_steps is not None:
            fields.append("completed_steps = ?"); params.append(completed_steps)
        if summary is not None:
            fields.append("summary_json = ?"); params.append(json.dumps(summary, ensure_ascii=False))
        if error_message is not None:
            fields.append("error_message = ?"); params.append(error_message)
        if status in (RunStatus.SUCCESS.value, RunStatus.FAILED.value, RunStatus.CANCELLED.value):
            fields.append("finished_at = ?"); params.append(datetime.datetime.now())
        params.append(run_id)
        with self._conn() as con:
            con.execute(
                f"UPDATE attribution_template_run SET {', '.join(fields)} WHERE run_id = ?",
                params,
            )

    def finalize_run(
        self,
        run_id: str,
        status: str,
        summary: Dict[str, Any],
        duration_ms: int,
    ) -> None:
        """结束 run（写 summary + 耗时）"""
        with self._conn() as con:
            con.execute(
                """
                UPDATE attribution_template_run
                SET status = ?, summary_json = ?, duration_ms = ?,
                    completed_steps = total_steps, finished_at = ?
                WHERE run_id = ?
                """,
                [status, json.dumps(summary, ensure_ascii=False), duration_ms,
                 datetime.datetime.now(), run_id],
            )

    # =====================================================================
    # 步骤执行明细（attribution_step_execution）
    # =====================================================================
    def create_step_execution(
        self,
        run_id: str,
        step_index: int,
        step_name: str,
        step_type: str,
        input_data: Dict[str, Any],
    ) -> str:
        step_exec_id = f"se_{uuid.uuid4().hex[:12]}"
        now = datetime.datetime.now()
        with self._conn() as con:
            con.execute(
                """
                INSERT INTO attribution_step_execution
                    (step_execution_id, run_id, step_index, step_name, step_type,
                     input_json, output_json, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, NULL, 'pending', ?)
                """,
                [step_exec_id, run_id, step_index, step_name, step_type,
                 json.dumps(input_data, ensure_ascii=False, default=str), now],
            )
        return step_exec_id

    def complete_step_execution(
        self,
        step_execution_id: str,
        output_data: Dict[str, Any],
        duration_ms: int,
    ) -> None:
        with self._conn() as con:
            con.execute(
                """
                UPDATE attribution_step_execution
                SET output_json = ?, status = 'success', duration_ms = ?
                WHERE step_execution_id = ?
                """,
                [json.dumps(output_data, ensure_ascii=False, default=str), duration_ms, step_execution_id],
            )

    def fail_step_execution(
        self,
        step_execution_id: str,
        error_message: str,
    ) -> None:
        with self._conn() as con:
            con.execute(
                """
                UPDATE attribution_step_execution
                SET status = 'failed', error_message = ?
                WHERE step_execution_id = ?
                """,
                [error_message, step_execution_id],
            )

    def list_step_executions(self, run_id: str) -> List[StepExecution]:
        with self._conn() as con:
            rows = con.execute(
                "SELECT * FROM attribution_step_execution WHERE run_id = ? ORDER BY step_index ASC",
                [run_id],
            ).fetchall()
            return [self._row_to_step(r) for r in rows]

    # =====================================================================
    # 行 → 模型转换
    # =====================================================================
    @staticmethod
    def _row_to_template(row) -> Template:
        cols = ["template_id", "name", "code", "description", "category", "tags",
                "current_version", "is_archived", "is_builtin",
                "created_by", "created_at", "updated_at"]
        d = dict(zip(cols, row))
        d["tags"] = json.loads(d["tags"]) if d["tags"] else []
        return Template(**d)

    @staticmethod
    def _row_to_version(row) -> TemplateVersion:
        cols = ["template_id", "version", "steps_json", "status", "changelog",
                "created_by", "created_at"]
        d = dict(zip(cols, row))
        d["steps"] = json.loads(d.pop("steps_json"))
        return TemplateVersion(**d)

    @staticmethod
    def _row_to_run(row) -> TemplateRun:
        cols = ["run_id", "template_id", "template_version", "user_query", "params_json",
                "status", "total_steps", "completed_steps", "summary_json", "error_message",
                "started_at", "finished_at", "duration_ms", "created_by", "created_at"]
        d = dict(zip(cols, row))
        if d.get("params_json"):
            d["params"] = json.loads(d["params_json"])
        else:
            d["params"] = {}
        d.pop("params_json", None)
        if d.get("summary_json"):
            d["summary"] = json.loads(d["summary_json"])
        else:
            d["summary"] = None
        d.pop("summary_json", None)
        return TemplateRun(**d)

    @staticmethod
    def _row_to_step(row) -> StepExecution:
        cols = ["step_execution_id", "run_id", "step_index", "step_name", "step_type",
                "input_json", "output_json", "status", "error_message", "duration_ms", "created_at"]
        d = dict(zip(cols, row))
        if d.get("input_json"):
            d["input_data"] = json.loads(d["input_json"])
        else:
            d["input_data"] = {}
        d.pop("input_json", None)
        if d.get("output_json"):
            d["output_data"] = json.loads(d["output_json"])
        else:
            d["output_data"] = None
        d.pop("output_json", None)
        return StepExecution(**d)
