"""
归因维度模板中心（P0 增强）
=========================

提供三类模板：
1. 系统预设模板（硬编码，可读不可改）
2. 角色默认模板（按 role 绑定默认模板）
3. 用户自定义模板（保存到 DuckDB，可增删改）

注：写入操作直接 duckdb.connect（非只读），绕过 SqlExecutor 的只读约束，
因为 SqlExecutor 是给"业务查询"用的（要求严禁 DML/DDL）。
模板管理是"平台元数据"管理，需要写权限。
"""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# DuckDB 主库路径（与 data_manager.py 同源）
BACKEND_DIR = Path(__file__).resolve().parent.parent
DUCKDB_PATH = BACKEND_DIR / "data" / "gac_bi.duckdb"


# ────────────────────────────────────────────────────────────────────
# 系统预设模板（5 个，覆盖典型业务场景）
# ────────────────────────────────────────────────────────────────────
SYSTEM_PRESETS: List[Dict[str, Any]] = [
    {
        "id": "preset_exec_quarterly",
        "name": "高管季度复盘",
        "description": "高管视角，快速定位品牌 × 区域 × 车型，3 维度宽口径",
        "scope": "system",
        "owner_role": None,
        "metric_key": "delivered_units",
        "dimensions": ["brand_name", "region_name", "model_name"],
        "created_at": "2026-01-01",
    },
    {
        "id": "preset_analyst_deep",
        "name": "分析师深度下钻",
        "description": "5 维度细粒度（品牌 + 区域 + 车型 + 能源 + 价格段），适合专题分析",
        "scope": "system",
        "owner_role": None,
        "metric_key": "delivered_units",
        "dimensions": ["brand_name", "region_name", "model_name", "energy_type", "price_segment"],
        "created_at": "2026-01-01",
    },
    {
        "id": "preset_region_kpi",
        "name": "区域总监 KPI",
        "description": "聚焦区域 × 车型，评估区域总经理经营质量",
        "scope": "system",
        "owner_role": None,
        "metric_key": "delivered_units",
        "dimensions": ["region_name", "model_name", "monthly"],
        "created_at": "2026-01-01",
    },
    {
        "id": "preset_model_product",
        "name": "车型经理产品复盘",
        "description": "聚焦车型 × 价格段 × 能源类型，定位产品定位偏差",
        "scope": "system",
        "owner_role": None,
        "metric_key": "delivered_units",
        "dimensions": ["model_name", "price_segment", "energy_type"],
        "created_at": "2026-01-01",
    },
    {
        "id": "preset_new_energy",
        "name": "新能源专项",
        "description": "新能源转型追踪：能源类型 × 价格段 × 车型",
        "scope": "system",
        "owner_role": None,
        "metric_key": "delivered_units",
        "dimensions": ["energy_type", "price_segment", "model_name", "monthly"],
        "created_at": "2026-01-01",
    },
]

# ────────────────────────────────────────────────────────────────────
# 角色默认模板绑定（4 个角色 → 各 1 个）
# ────────────────────────────────────────────────────────────────────
ROLE_DEFAULTS: Dict[str, str] = {
    "executive": "preset_exec_quarterly",     # 高管 → 季度复盘
    "analyst":   "preset_analyst_deep",        # 分析师 → 深度下钻
    "product":   "preset_analyst_deep",        # 产品经理 → 深度下钻
    "visitor":   "preset_exec_quarterly",      # 访客 → 默认宽口径
}


class AttributionTemplateManager:
    """
    归因维度模板管理器
    - 系统预设：内存常量，重启保留
    - 角色默认：内存常量，绑定 role
    - 用户自定义：持久化到 DuckDB 的 dim_attribution_template 表
    """

    DDL = """
    CREATE TABLE IF NOT EXISTS dim_attribution_template (
        id VARCHAR PRIMARY KEY,
        name VARCHAR NOT NULL,
        description VARCHAR,
        scope VARCHAR NOT NULL DEFAULT 'user',
        metric_key VARCHAR NOT NULL DEFAULT 'delivered_units',
        owner_role VARCHAR,
        owner_user VARCHAR,
        dimensions JSON,
        created_at VARCHAR,
        updated_at VARCHAR
    )
    """

    # ⭐ P1：迁移 SQL（兼容老库）。ALTER TABLE 用 IF NOT EXISTS 风格（DuckDB 不支持，
    # 因此只在首次 ensure_table 时探测一次）。
    MIGRATE_DDL = [
        "ALTER TABLE dim_attribution_template ADD COLUMN metric_key VARCHAR NOT NULL DEFAULT 'delivered_units'",
    ]

    # ⭐ P1：归因指标白名单（与 sop_analyzer.METRIC_DIMENSION_MATRIX 保持一致）
    SUPPORTED_METRIC_KEYS = {
        "delivered_units",
        "gross_revenue",
        "customer_leads",
        "conversion_rate",
        "avg_price",
    }
    DEFAULT_METRIC_KEY = "delivered_units"

    def __init__(self, executor=None):
        self.executor = executor  # 保留参数以兼容老调用，但实际写操作用直接连接
        self._ensure_table()

    def _ensure_table(self):
        """确保表存在（首次运行时创建 + 老库自动迁移加 metric_key 列）"""
        try:
            import duckdb
            if not DUCKDB_PATH.exists():
                # 主库未初始化时跳过
                return
            con = duckdb.connect(str(DUCKDB_PATH))
            try:
                con.execute(self.DDL)
                # ⭐ P1：探测列是否存在，不存在则补列（兼容老库）
                cols = con.execute(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'dim_attribution_template'"
                ).fetchall()
                col_names = {c[0] for c in cols}
                if "metric_key" not in col_names:
                    try:
                        for stmt in self.MIGRATE_DDL:
                            con.execute(stmt)
                        print("[attribution_templates] 已迁移: 新增 metric_key 列")
                    except Exception as mig_err:
                        # 迁移失败不致命（可能是全新列已存在等情况）
                        print(f"[attribution_templates] 迁移 warn: {mig_err}")
            finally:
                con.close()
        except Exception as e:
            # 不抛异常：管理模块不影响主服务
            print(f"[attribution_templates] _ensure_table warn: {e}")

    def _direct_exec(self, sql: str, fetch: bool = False) -> Dict[str, Any]:
        """
        直接连 DuckDB 执行 SQL（绕过 SqlExecutor 的只读约束）。
        模板表 SQL 都是参数已转义的，安全风险可控。
        """
        try:
            import duckdb
            if not DUCKDB_PATH.exists():
                return {"success": False, "error": f"主库不存在: {DUCKDB_PATH}"}
            con = duckdb.connect(str(DUCKDB_PATH))
            try:
                if fetch:
                    cursor = con.execute(sql)
                    cols = [d[0] for d in cursor.description] if cursor.description else []
                    rows = cursor.fetchall()
                    data = [dict(zip(cols, row)) for row in rows]
                    return {"success": True, "data": data}
                else:
                    con.execute(sql)
                    return {"success": True}
            finally:
                con.close()
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ─── 1. 列出全部模板（系统 + 用户） ─────────────────────────────
    def list_templates(self, role: Optional[str] = None, user: Optional[str] = None) -> Dict[str, Any]:
        """
        返回：
        {
            "system_presets": [...],
            "role_default_id": "preset_xxx" | None,
            "user_templates": [...],
        }
        """
        return {
            "system_presets": SYSTEM_PRESETS,
            "role_default_id": ROLE_DEFAULTS.get(role) if role else None,
            "role_defaults_map": ROLE_DEFAULTS,
            "user_templates": self._list_user_templates(user=user),
        }

    def _list_user_templates(self, user: Optional[str] = None) -> List[Dict[str, Any]]:
        # 注：所有字符串参数已手动转义单引号
        sql = "SELECT id, name, description, scope, owner_role, owner_user, metric_key, dimensions, created_at, updated_at FROM dim_attribution_template"
        if user:
            safe_user = self._esc(user)
            sql += f" WHERE owner_user = '{safe_user}'"
        sql += " ORDER BY updated_at DESC"
        res = self._direct_exec(sql, fetch=True)
        if not res.get("success") or not res.get("data"):
            return []
        out = []
        for row in res["data"]:
            try:
                row["dimensions"] = json.loads(row["dimensions"]) if isinstance(row["dimensions"], str) else row["dimensions"]
            except Exception:
                row["dimensions"] = []
            # ⭐ P1：老数据兜底补 metric_key
            row.setdefault("metric_key", self.DEFAULT_METRIC_KEY)
            out.append(row)
        return out

    # ─── 2. 获取单个模板详情 ─────────────────────────────────────
    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        # 系统预设优先
        for t in SYSTEM_PRESETS:
            if t["id"] == template_id:
                t.setdefault("metric_key", self.DEFAULT_METRIC_KEY)
                return t
        # 用户模板
        sql = f"SELECT id, name, description, scope, owner_role, owner_user, metric_key, dimensions, created_at, updated_at FROM dim_attribution_template WHERE id = '{self._esc(template_id)}'"
        res = self._direct_exec(sql, fetch=True)
        if not res.get("success") or not res.get("data"):
            return None
        row = res["data"][0]
        try:
            row["dimensions"] = json.loads(row["dimensions"]) if isinstance(row["dimensions"], str) else row["dimensions"]
        except Exception:
            row["dimensions"] = []
        row.setdefault("metric_key", self.DEFAULT_METRIC_KEY)
        return row

    def _esc(self, s: str) -> str:
        """SQL 字符串转义（SqlExecutor 无参数化接口时使用）"""
        return str(s).replace("'", "''")

    # ─── 3. 创建用户自定义模板 ─────────────────────────────────────
    def create_template(
        self,
        name: str,
        dimensions: List[str],
        description: str = "",
        owner_role: Optional[str] = None,
        owner_user: Optional[str] = None,
    ) -> Dict[str, Any]:
        if self.executor is None:
            return {"success": False, "error": "数据库未初始化"}
        # 维度白名校验
        from core.sop_analyzer import DIMENSION_FIELD_MAP, METRIC_DIMENSION_MATRIX
        valid_dims = [d for d in dimensions if d in DIMENSION_FIELD_MAP]
        if not valid_dims:
            return {"success": False, "error": "至少选择 1 个有效维度"}
        if len(valid_dims) > 4:
            return {"success": False, "error": "最多 4 个维度"}

        # ⭐ P1：归因指标校验（白名单兜底）
        safe_metric = metric_key if metric_key in self.SUPPORTED_METRIC_KEYS else self.DEFAULT_METRIC_KEY
        metric_cfg = METRIC_DIMENSION_MATRIX.get(safe_metric, {})
        allowed = set(metric_cfg.get("applicable_dimensions", []))
        valid_dims = [d for d in valid_dims if d in allowed]
        if not valid_dims:
            return {"success": False, "error": f"该指标（{safe_metric}）下没有可用维度"}
        if len(valid_dims) > 4:
            valid_dims = valid_dims[:4]

        template_id = f"user_{uuid.uuid4().hex[:8]}"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        dims_json = json.dumps(valid_dims, ensure_ascii=False)
        # 所有字符串字段都手动转义单引号（防 SQL 注入）
        sql = f"""
        INSERT INTO dim_attribution_template
            (id, name, description, scope, metric_key, owner_role, owner_user, dimensions, created_at, updated_at)
        VALUES (
            '{self._esc(template_id)}',
            '{self._esc(name)}',
            '{self._esc(description)}',
            'user',
            '{self._esc(safe_metric)}',
            '{self._esc(owner_role or "")}',
            '{self._esc(owner_user or "")}',
            '{self._esc(dims_json)}',
            '{now}',
            '{now}'
        )
        """
        res = self._direct_exec(sql)
        if not res.get("success"):
            return {"success": False, "error": res.get("error", "写入失败")}
        return {
            "success": True,
            "template": {
                "id": template_id,
                "name": name,
                "description": description,
                "scope": "user",
                "metric_key": safe_metric,
                "owner_role": owner_role,
                "owner_user": owner_user,
                "dimensions": valid_dims,
                "created_at": now,
                "updated_at": now,
            }
        }

    # ─── 4. 删除用户自定义模板 ─────────────────────────────────────
    def delete_template(self, template_id: str, owner_user: Optional[str] = None) -> Dict[str, Any]:
        if template_id.startswith("preset_"):
            return {"success": False, "error": "系统预设模板不可删除"}
        sql = f"DELETE FROM dim_attribution_template WHERE id = '{self._esc(template_id)}'"
        if owner_user:
            sql += f" AND owner_user = '{self._esc(owner_user)}'"
        res = self._direct_exec(sql)
        if not res.get("success"):
            return {"success": False, "error": res.get("error", "删除失败")}
        return {"success": True, "deleted_id": template_id}

    # ─── 5. 更新用户自定义模板 ─────────────────────────────────────
    def update_template(
        self,
        template_id: str,
        name: Optional[str] = None,
        dimensions: Optional[List[str]] = None,
        description: Optional[str] = None,
        owner_user: Optional[str] = None,
        metric_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        if template_id.startswith("preset_"):
            return {"success": False, "error": "系统预设模板不可编辑"}

        from core.sop_analyzer import DIMENSION_FIELD_MAP, METRIC_DIMENSION_MATRIX
        updates = []
        if name is not None:
            updates.append(f"name = '{self._esc(name)}'")
        if description is not None:
            updates.append(f"description = '{self._esc(description)}'")
        # ⭐ P1：先解析新指标（如果同时改维度，需根据新指标过滤维度）
        new_metric_key = metric_key if metric_key in self.SUPPORTED_METRIC_KEYS else None
        if dimensions is not None:
            valid_dims = [d for d in dimensions if d in DIMENSION_FIELD_MAP]
            if not valid_dims:
                return {"success": False, "error": "至少 1 个有效维度"}
            if len(valid_dims) > 4:
                return {"success": False, "error": "最多 4 个维度"}
            # ⭐ P1：如同时传了 metric_key，按新指标过滤维度
            if new_metric_key is not None:
                metric_cfg = METRIC_DIMENSION_MATRIX.get(new_metric_key, {})
                allowed = set(metric_cfg.get("applicable_dimensions", []))
                valid_dims = [d for d in valid_dims if d in allowed]
                if not valid_dims:
                    return {"success": False, "error": f"该指标（{new_metric_key}）下没有可用维度"}
            dims_json = json.dumps(valid_dims, ensure_ascii=False)
            updates.append(f"dimensions = '{self._esc(dims_json)}'")
        # ⭐ P1：单独更新 metric_key（不传 dimensions 时也允许）
        if new_metric_key is not None:
            updates.append(f"metric_key = '{self._esc(new_metric_key)}'")
        if not updates:
            return {"success": False, "error": "没有可更新字段"}

        updates.append(f"updated_at = '{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}'")
        sql = f"UPDATE dim_attribution_template SET {', '.join(updates)} WHERE id = '{self._esc(template_id)}'"
        if owner_user:
            sql += f" AND owner_user = '{self._esc(owner_user)}'"
        res = self._direct_exec(sql)
        if not res.get("success"):
            return {"success": False, "error": res.get("error", "更新失败")}
        return {"success": True, "template_id": template_id}
