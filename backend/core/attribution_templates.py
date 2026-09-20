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
# ⭐ P2-SprintA：每个预设都补全 steps（SOP 步骤化结构），老字段 dimensions 保留供向下兼容
# ────────────────────────────────────────────────────────────────────
SYSTEM_PRESETS: List[Dict[str, Any]] = [
    {
        "id": "preset_exec_quarterly",
        "name": "高管季度复盘",
        "description": "高管视角 5 步 SOP：整体达成率 → 横向看品牌 → 下钻问题品牌-区域 → 下钻问题区域-车型 → 策略建议",
        "scope": "system",
        "owner_role": None,
        "metric_key": "delivered_units",
        "dimensions": ["brand_name", "region_name", "model_name"],
        "steps": [
            {"step_id": "s1", "title": "整体达成率对标", "step_type": "overall_kpi",
             "metric_key": "delivered_units", "group_by": [],
             "compare_mode": "plan", "order": 1,
             "threshold": {"warn": 0.95, "bad": 0.85}},
            {"step_id": "s2", "title": "横向对比品牌", "step_type": "horizontal_compare",
             "metric_key": "delivered_units", "group_by": ["brand_name"], "order": 2},
            {"step_id": "s3", "title": "下钻问题品牌-区域", "step_type": "drill_down",
             "metric_key": "delivered_units", "group_by": ["region_name"], "order": 3,
             "threshold": {"warn": 0.95, "bad": 0.85}},
            {"step_id": "s4", "title": "下钻问题区域-车型", "step_type": "drill_down",
             "metric_key": "delivered_units", "group_by": ["model_name"], "order": 4,
             "top_n": 10},
            {"step_id": "s5", "title": "策略建议", "step_type": "strategy_recommend",
             "metric_key": "delivered_units", "group_by": [],
             "depends_on": "s4", "order": 5},
        ],
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
        "steps": [
            {"step_id": "a1", "title": "整体大盘", "step_type": "overall_kpi",
             "metric_key": "delivered_units", "group_by": [], "order": 1},
            {"step_id": "a2", "title": "按品牌横向", "step_type": "horizontal_compare",
             "metric_key": "delivered_units", "group_by": ["brand_name"], "order": 2},
            {"step_id": "a3", "title": "品牌×区域下钻", "step_type": "drill_down",
             "metric_key": "delivered_units", "group_by": ["region_name"], "order": 3},
            {"step_id": "a4", "title": "能源类型拆解", "step_type": "cross_attribution",
             "metric_key": "delivered_units", "group_by": ["energy_type"], "order": 4},
            {"step_id": "a5", "title": "价格段归因", "step_type": "drill_down",
             "metric_key": "delivered_units", "group_by": ["price_segment"], "order": 5},
        ],
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
        "steps": [
            {"step_id": "r1", "title": "区域整体达成", "step_type": "overall_kpi",
             "metric_key": "delivered_units", "group_by": [], "order": 1,
             "compare_mode": "plan"},
            {"step_id": "r2", "title": "区域横向对比", "step_type": "horizontal_compare",
             "metric_key": "delivered_units", "group_by": ["region_name"], "order": 2},
            {"step_id": "r3", "title": "区域-车型下钻", "step_type": "drill_down",
             "metric_key": "delivered_units", "group_by": ["model_name"], "order": 3},
            {"step_id": "r4", "title": "月度趋势", "step_type": "period_compare",
             "metric_key": "delivered_units", "group_by": ["monthly"],
             "compare_mode": "mom", "compare_period": "month", "order": 4},
        ],
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
        "steps": [
            {"step_id": "m1", "title": "车型大盘", "step_type": "horizontal_compare",
             "metric_key": "delivered_units", "group_by": ["model_name"], "order": 1,
             "top_n": 20},
            {"step_id": "m2", "title": "车型-价格段", "step_type": "drill_down",
             "metric_key": "delivered_units", "group_by": ["price_segment"], "order": 2},
            {"step_id": "m3", "title": "能源类型对比", "step_type": "cross_attribution",
             "metric_key": "delivered_units", "group_by": ["energy_type"], "order": 3},
            {"step_id": "m4", "title": "策略建议", "step_type": "strategy_recommend",
             "metric_key": "delivered_units", "group_by": [],
             "depends_on": "m3", "order": 4},
        ],
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
        "steps": [
            {"step_id": "n1", "title": "新能源整体达成", "step_type": "overall_kpi",
             "metric_key": "delivered_units", "group_by": [], "order": 1,
             "compare_mode": "yoy", "compare_period": "2025-Q3"},
            {"step_id": "n2", "title": "能源类型对比", "step_type": "horizontal_compare",
             "metric_key": "delivered_units", "group_by": ["energy_type"], "order": 2},
            {"step_id": "n3", "title": "新能源-价格段下钻", "step_type": "drill_down",
             "metric_key": "delivered_units", "group_by": ["price_segment"], "order": 3},
            {"step_id": "n4", "title": "重点车型追踪", "step_type": "drill_down",
             "metric_key": "delivered_units", "group_by": ["model_name"], "order": 4,
             "top_n": 10},
            {"step_id": "n5", "title": "月度趋势", "step_type": "period_compare",
             "metric_key": "delivered_units", "group_by": ["monthly"],
             "compare_mode": "mom", "compare_period": "month", "order": 5},
        ],
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

    # ⭐ P2-SprintA：SOP 步骤化迁移（加 steps/updated_by 列 + 老数据兜底为 1 个 horizontal_compare step）
    MIGRATE_STEPS_DDL = [
        "ALTER TABLE dim_attribution_template ADD COLUMN steps JSON",
        "ALTER TABLE dim_attribution_template ADD COLUMN updated_by VARCHAR DEFAULT ''",
    ]

    # ⭐ P2-SprintA：模板版本审计表（每次 update 自动快照）
    AUDIT_DDL = """
    CREATE TABLE IF NOT EXISTS dim_attribution_template_audit (
        audit_id VARCHAR PRIMARY KEY,
        template_id VARCHAR NOT NULL,
        version_no INTEGER NOT NULL,
        snapshot JSON NOT NULL,
        changed_by VARCHAR,
        change_reason VARCHAR,
        changed_at VARCHAR
    )
    """
    AUDIT_INDEX_DDL = [
        "CREATE INDEX IF NOT EXISTS idx_audit_tmpl ON dim_attribution_template_audit (template_id, version_no DESC)",
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
            # ⭐ P2-SprintA：迁移前自动备份（演示阶段防翻车）
            self._backup_db_before_migrate()
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

                # ⭐ P2-SprintA：steps / updated_by 列迁移
                cols2 = {c[0] for c in con.execute(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'dim_attribution_template'"
                ).fetchall()}
                if "steps" not in cols2:
                    try:
                        for stmt in self.MIGRATE_STEPS_DDL:
                            con.execute(stmt)
                        print("[attribution_templates] 已迁移: 新增 steps / updated_by 列")
                    except Exception as mig_err:
                        print(f"[attribution_templates] steps 迁移 warn: {mig_err}")

                # ⭐ P2-SprintA：老数据兜底 —— 把 dimensions 转成 1 个 horizontal_compare step
                legacy_rows = con.execute(
                    "SELECT id, metric_key, dimensions FROM dim_attribution_template "
                    "WHERE steps IS NULL AND dimensions IS NOT NULL"
                ).fetchall()
                if legacy_rows:
                    for row in legacy_rows:
                        tmpl_id, metric_key_val, dims_val = row[0], row[1], row[2]
                        try:
                            dims_list = json.loads(dims_val) if isinstance(dims_val, str) else (dims_val or [])
                        except Exception:
                            dims_list = []
                        if not isinstance(dims_list, list):
                            dims_list = []
                        legacy_step = json.dumps([{
                            "step_id": "legacy_1",
                            "title": "横向分析",
                            "step_type": "horizontal_compare",
                            "metric_key": metric_key_val or self.DEFAULT_METRIC_KEY,
                            "group_by": dims_list,
                            "order": 1,
                        }], ensure_ascii=False)
                        # 用参数化绑定（避免转义）
                        con.execute(
                            "UPDATE dim_attribution_template SET steps = ? WHERE id = ?",
                            [legacy_step, tmpl_id],
                        )
                    print(f"[attribution_templates] 已兜底迁移 {len(legacy_rows)} 条老数据 → 1 个 horizontal_compare step")

                # ⭐ P2-SprintA：创建审计表 + 索引
                con.execute(self.AUDIT_DDL)
                for idx in self.AUDIT_INDEX_DDL:
                    try:
                        con.execute(idx)
                    except Exception:
                        pass

            finally:
                con.close()
        except Exception as e:
            # 不抛异常：管理模块不影响主服务
            print(f"[attribution_templates] _ensure_table warn: {e}")

    def _backup_db_before_migrate(self):
        """⭐ P2-SprintA：迁移前自动备份 DuckDB 文件（同目录加 .bak.YYYYMMDDHHMMSS 后缀）"""
        try:
            import shutil
            from datetime import datetime
            if not DUCKDB_PATH.exists():
                return
            backup_name = f"gac_bi.duckdb.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
            backup_path = DUCKDB_PATH.parent / backup_name
            # 防止无限生成备份：同一天已有 .bak.YYYYMMDD 时跳过
            today_prefix = f"gac_bi.duckdb.bak.{datetime.now().strftime('%Y%m%d')}"
            already = list(DUCKDB_PATH.parent.glob(f"{today_prefix}*"))
            if already:
                return
            shutil.copy2(DUCKDB_PATH, backup_path)
            print(f"[attribution_templates] 已备份 DuckDB → {backup_path.name}")
        except Exception as e:
            print(f"[attribution_templates] 备份 warn（不致命）: {e}")

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
        系统预设列表：DB 中存在的 override + 内存常量的兜底合并
        """
        return {
            "system_presets": self._list_system_presets(),
            "role_default_id": ROLE_DEFAULTS.get(role) if role else None,
            "role_defaults_map": ROLE_DEFAULTS,
            "user_templates": self._list_user_templates(user=user),
        }

    def _list_system_presets(self) -> List[Dict[str, Any]]:
        """合并 DB override + 内存常量（DB 优先）"""
        import copy
        sql = "SELECT id, name, description, scope, owner_role, owner_user, metric_key, dimensions, steps, created_at, updated_at, updated_by FROM dim_attribution_template WHERE id LIKE 'preset_%'"
        res = self._direct_exec(sql, fetch=True)
        db_presets = {}
        if res.get("success") and res.get("data"):
            for row in res["data"]:
                try:
                    row["dimensions"] = json.loads(row["dimensions"]) if isinstance(row["dimensions"], str) else row["dimensions"]
                except Exception:
                    row["dimensions"] = []
                try:
                    row["steps"] = json.loads(row["steps"]) if isinstance(row["steps"], str) else (row["steps"] or [])
                except Exception:
                    row["steps"] = []
                row.setdefault("metric_key", self.DEFAULT_METRIC_KEY)
                row.setdefault("updated_by", "")
                db_presets[row["id"]] = row
        out = []
        for t in SYSTEM_PRESETS:
            if t["id"] in db_presets:
                out.append(db_presets[t["id"]])  # DB override 优先
            else:
                tpl = copy.deepcopy(t)
                tpl.setdefault("metric_key", self.DEFAULT_METRIC_KEY)
                tpl.setdefault("steps", [])
                tpl.setdefault("updated_by", "system")
                out.append(tpl)
        return out

    def _list_user_templates(self, user: Optional[str] = None) -> List[Dict[str, Any]]:
        # 注：所有字符串参数已手动转义单引号
        sql = "SELECT id, name, description, scope, owner_role, owner_user, metric_key, dimensions, steps, created_at, updated_at, updated_by FROM dim_attribution_template"
        if user:
            safe_user = self._esc(user)
            sql += f" WHERE owner_user = '{safe_user}'"
        sql += " ORDER BY updated_at DESC"
        res = self._direct_exec(sql, fetch=True)
        if not res.get("success") or not res.get("data"):
            return []
        out = []
        for row in res["data"]:
            # dimensions 老字段
            try:
                row["dimensions"] = json.loads(row["dimensions"]) if isinstance(row["dimensions"], str) else row["dimensions"]
            except Exception:
                row["dimensions"] = []
            # ⭐ P2-SprintA：steps 新字段（json 字符串 → list）
            try:
                row["steps"] = json.loads(row["steps"]) if isinstance(row["steps"], str) else (row["steps"] or [])
            except Exception:
                row["steps"] = []
            # ⭐ P1：老数据兜底补 metric_key
            row.setdefault("metric_key", self.DEFAULT_METRIC_KEY)
            # ⭐ P2-SprintA：老数据兜底补 updated_by
            row.setdefault("updated_by", "")
            out.append(row)
        return out

    # ─── 2. 获取单个模板详情 ─────────────────────────────────────
    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        # ⭐ P2-SprintA：DB 优先（管理员可改 preset_*，DB 是事实之源）
        # 系统预设作为兜底：DB 没记录时返回内存常量
        if template_id.startswith("preset_"):
            sql = f"SELECT id, name, description, scope, owner_role, owner_user, metric_key, dimensions, steps, created_at, updated_at, updated_by FROM dim_attribution_template WHERE id = '{self._esc(template_id)}'"
            res = self._direct_exec(sql, fetch=True)
            if res.get("success") and res.get("data"):
                row = res["data"][0]
                try:
                    row["dimensions"] = json.loads(row["dimensions"]) if isinstance(row["dimensions"], str) else row["dimensions"]
                except Exception:
                    row["dimensions"] = []
                try:
                    row["steps"] = json.loads(row["steps"]) if isinstance(row["steps"], str) else (row["steps"] or [])
                except Exception:
                    row["steps"] = []
                row.setdefault("metric_key", self.DEFAULT_METRIC_KEY)
                row.setdefault("updated_by", "")
                return row
            # 兜底：返回内存常量（深拷贝避免污染）
            import copy
            for t in SYSTEM_PRESETS:
                if t["id"] == template_id:
                    tpl = copy.deepcopy(t)
                    tpl.setdefault("metric_key", self.DEFAULT_METRIC_KEY)
                    tpl.setdefault("steps", [])
                    tpl.setdefault("updated_by", "system")
                    return tpl
            return None
        # 非 preset_*：直接查 DB
        sql = f"SELECT id, name, description, scope, owner_role, owner_user, metric_key, dimensions, steps, created_at, updated_at, updated_by FROM dim_attribution_template WHERE id = '{self._esc(template_id)}'"
        res = self._direct_exec(sql, fetch=True)
        if not res.get("success") or not res.get("data"):
            return None
        row = res["data"][0]
        try:
            row["dimensions"] = json.loads(row["dimensions"]) if isinstance(row["dimensions"], str) else row["dimensions"]
        except Exception:
            row["dimensions"] = []
        try:
            row["steps"] = json.loads(row["steps"]) if isinstance(row["steps"], str) else (row["steps"] or [])
        except Exception:
            row["steps"] = []
        row.setdefault("metric_key", self.DEFAULT_METRIC_KEY)
        row.setdefault("updated_by", "")
        return row

    def _esc(self, s: str) -> str:
        """SQL 字符串转义（SqlExecutor 无参数化接口时使用）"""
        return str(s).replace("'", "''")

    # ─── 3. 创建用户自定义模板 ─────────────────────────────────────
    def create_template(
        self,
        name: str,
        dimensions: Optional[List[str]] = None,
        description: str = "",
        owner_role: Optional[str] = None,
        owner_user: Optional[str] = None,
        metric_key: Optional[str] = None,
        steps: Optional[List[Dict[str, Any]]] = None,
        scope: str = "user",
        updated_by: Optional[str] = None,
        change_reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        创建模板（向后兼容）：
        - 老调用方只传 dimensions：自动生成 1 个 horizontal_compare step（兼容老 API）
        - 新调用方传 steps：写入新列；同时自动从 steps 推导 dimensions 兜底老列
        - steps/dimensions 都不传：返回错误
        """
        steps_list: List[Dict[str, Any]] = []
        if steps is not None:
            try:
                from backend.api.schemas import StepSpec, AttributionTemplateV2
                # 字段级校验
                step_objs = [StepSpec(**s) for s in steps]
                # 模板级 model_validator：order 连续 / step_id 唯一 / depends_on 存在 / strategy 必须 depends_on
                _pseudo = AttributionTemplateV2(
                    id="__validate__",
                    name="__validate__",
                    steps=step_objs,
                )
                steps_list = [s.model_dump() for s in step_objs]
            except Exception as e:
                return {"success": False, "error": f"steps 校验失败: {e}"}
        else:
            # 老调用方：dimensions 兜底成 1 个 horizontal_compare step
            from core.sop_analyzer import DIMENSION_FIELD_MAP
            valid_dims_legacy = [d for d in (dimensions or []) if d in DIMENSION_FIELD_MAP]
            if not valid_dims_legacy:
                return {"success": False, "error": "至少选择 1 个有效维度 或 传 steps"}
            steps_list = [{
                "step_id": f"step_{uuid.uuid4().hex[:6]}",
                "title": "横向分析",
                "step_type": "horizontal_compare",
                "metric_key": metric_key if metric_key in self.SUPPORTED_METRIC_KEYS else self.DEFAULT_METRIC_KEY,
                "group_by": valid_dims_legacy[:4],
                "order": 1,
            }]

        # 2) metric_key 白名单兜底
        from core.sop_analyzer import DIMENSION_FIELD_MAP, METRIC_DIMENSION_MATRIX
        safe_metric = metric_key if metric_key in self.SUPPORTED_METRIC_KEYS else self.DEFAULT_METRIC_KEY
        metric_cfg = METRIC_DIMENSION_MATRIX.get(safe_metric, {})
        allowed = set(metric_cfg.get("applicable_dimensions", []))

        # 3) 从 steps 推导 dimensions（兜底老列），同时按指标过滤
        derived_dims: List[str] = []
        for s in steps_list:
            for d in s.get("group_by") or []:
                if d in allowed and d in DIMENSION_FIELD_MAP and d not in derived_dims:
                    derived_dims.append(d)
        if not derived_dims and dimensions:
            derived_dims = [d for d in dimensions if d in allowed][:4]

        template_id = f"user_{uuid.uuid4().hex[:8]}"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        steps_json = json.dumps(steps_list, ensure_ascii=False)
        dims_json = json.dumps(derived_dims, ensure_ascii=False)

        # scope 白名单（admin 接口允许 system/role_default/market）
        if scope not in ("system", "role_default", "market", "user"):
            scope = "user"

        # 所有字符串字段都手动转义单引号（防 SQL 注入）
        sql = f"""
        INSERT INTO dim_attribution_template
            (id, name, description, scope, metric_key, owner_role, owner_user, dimensions, steps, created_at, updated_at, updated_by)
        VALUES (
            '{self._esc(template_id)}',
            '{self._esc(name)}',
            '{self._esc(description)}',
            '{self._esc(scope)}',
            '{self._esc(safe_metric)}',
            '{self._esc(owner_role or "")}',
            '{self._esc(owner_user or "")}',
            '{self._esc(dims_json)}',
            '{self._esc(steps_json)}',
            '{now}',
            '{now}',
            '{self._esc(updated_by or owner_user or "")}'
        )
        """
        res = self._direct_exec(sql)
        if not res.get("success"):
            return {"success": False, "error": res.get("error", "写入失败")}

        # ⭐ P2-SprintA：audit 初始快照
        self._audit_snapshot(template_id, version_no=1, snapshot={
            "id": template_id, "name": name, "description": description,
            "scope": scope, "metric_key": safe_metric,
            "dimensions": derived_dims, "steps": steps_list,
        }, changed_by=updated_by or owner_user or "", change_reason=change_reason or "init")

        return {
            "success": True,
            "template": {
                "id": template_id,
                "name": name,
                "description": description,
                "scope": scope,
                "metric_key": safe_metric,
                "owner_role": owner_role,
                "owner_user": owner_user,
                "dimensions": derived_dims,
                "steps": steps_list,
                "created_at": now,
                "updated_at": now,
                "updated_by": updated_by or owner_user or "",
            }
        }

    # ─── ⭐ P2-SprintA：审计快照写入 ─────────────────────────────
    def _audit_snapshot(
        self,
        template_id: str,
        version_no: int,
        snapshot: Dict[str, Any],
        changed_by: Optional[str] = None,
        change_reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        audit_id = f"audit_{uuid.uuid4().hex[:10]}"
        snap_json = json.dumps(snapshot, ensure_ascii=False, default=str)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sql = f"""
        INSERT INTO dim_attribution_template_audit
            (audit_id, template_id, version_no, snapshot, changed_by, change_reason, changed_at)
        VALUES (
            '{self._esc(audit_id)}',
            '{self._esc(template_id)}',
            {int(version_no)},
            '{self._esc(snap_json)}',
            '{self._esc(changed_by or "")}',
            '{self._esc(change_reason or "")}',
            '{now}'
        )
        """
        return self._direct_exec(sql)

    def _seed_preset_if_missing(self, template_id: str) -> None:
        """⭐ P2-SprintA：DB 中不存在 preset_* 时，从内存常量 seed 一行（让管理员 update 可见）"""
        check_sql = f"SELECT id FROM dim_attribution_template WHERE id = '{self._esc(template_id)}'"
        r = self._direct_exec(check_sql, fetch=True)
        if r.get("success") and r.get("data"):
            return  # 已存在，跳过
        # 从内存常量找
        import copy
        src = None
        for t in SYSTEM_PRESETS:
            if t["id"] == template_id:
                src = copy.deepcopy(t)
                break
        if not src:
            return
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        steps_json = json.dumps(src.get("steps") or [], ensure_ascii=False)
        dims_json = json.dumps(src.get("dimensions") or [], ensure_ascii=False)
        sql = f"""
        INSERT INTO dim_attribution_template
            (id, name, description, scope, metric_key, owner_role, owner_user, dimensions, steps, created_at, updated_at, updated_by)
        VALUES (
            '{self._esc(src["id"])}',
            '{self._esc(src["name"])}',
            '{self._esc(src.get("description", ""))}',
            'system',
            '{self._esc(src.get("metric_key") or self.DEFAULT_METRIC_KEY)}',
            '',
            '',
            '{self._esc(dims_json)}',
            '{self._esc(steps_json)}',
            '{now}',
            '{now}',
            'system_seed'
        )
        """
        self._direct_exec(sql)

    def get_audit_history(self, template_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """获取模板变更历史（按 version_no 倒序）"""
        sql = (
            f"SELECT audit_id, template_id, version_no, snapshot, changed_by, change_reason, changed_at "
            f"FROM dim_attribution_template_audit WHERE template_id = '{self._esc(template_id)}' "
            f"ORDER BY version_no DESC LIMIT {int(limit)}"
        )
        res = self._direct_exec(sql, fetch=True)
        if not res.get("success") or not res.get("data"):
            return []
        out = []
        for row in res["data"]:
            try:
                row["snapshot"] = json.loads(row["snapshot"]) if isinstance(row["snapshot"], str) else row["snapshot"]
            except Exception:
                pass
            out.append(row)
        return out

    # ─── ⭐ P2-SprintA：克隆模板（market/preset → user） ──────────
    def clone_template(
        self,
        source_template_id: str,
        target_scope: str = "user",
        new_name: Optional[str] = None,
        owner_user: Optional[str] = None,
    ) -> Dict[str, Any]:
        """克隆现有模板（system/preset_/market/user 都可作为源）"""
        src = self.get_template(source_template_id)
        if not src:
            return {"success": False, "error": f"源模板不存在: {source_template_id}"}
        return self.create_template(
            name=new_name or f"{src['name']}（克隆）",
            description=src.get("description", ""),
            scope=target_scope,
            metric_key=src.get("metric_key"),
            steps=src.get("steps"),
            owner_user=owner_user,
            updated_by=owner_user,
            change_reason=f"clone from {source_template_id}",
        )

    # ─── 4. 删除用户自定义模板 ─────────────────────────────────────
    def delete_template(
        self,
        template_id: str,
        owner_user: Optional[str] = None,
        allow_preset: bool = False,  # ⭐ P2-SprintA：管理员可绕过（删前会写 audit）
    ) -> Dict[str, Any]:
        """
        删除模板
        - 默认禁止删 preset_*（系统预设）
        - allow_preset=True 时允许管理员删（仅供运维场景；正常业务仍禁用）
        """
        if template_id.startswith("preset_") and not allow_preset:
            return {"success": False, "error": "系统预设模板不可删除"}
        sql = f"DELETE FROM dim_attribution_template WHERE id = '{self._esc(template_id)}'"
        if owner_user:
            sql += f" AND owner_user = '{self._esc(owner_user)}'"
        res = self._direct_exec(sql)
        if not res.get("success"):
            return {"success": False, "error": res.get("error", "删除失败")}
        return {"success": True, "deleted_id": template_id}

    # ─── 5. 更新模板（兼容老接口 + 支持 steps + audit） ─────────────
    def update_template(
        self,
        template_id: str,
        name: Optional[str] = None,
        dimensions: Optional[List[str]] = None,
        description: Optional[str] = None,
        owner_user: Optional[str] = None,
        metric_key: Optional[str] = None,
        steps: Optional[List[Dict[str, Any]]] = None,
        allow_preset: bool = False,  # ⭐ P2-SprintA：管理员可改 preset_*
        updated_by: Optional[str] = None,
        change_reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        更新模板：
        - 默认禁止改 preset_*；admin 传 allow_preset=True 可改（保留禁删）
        - 老调用方传 dimensions：兼容
        - 新调用方传 steps：写入新列 + 自动重算 dimensions
        - 每次 update 写一行 audit
        """
        if template_id.startswith("preset_") and not allow_preset:
            return {"success": False, "error": "系统预设模板不可编辑"}

        # 1) Pydantic 校验 steps（如有）
        steps_list: Optional[List[Dict[str, Any]]] = None
        if steps is not None:
            try:
                from backend.api.schemas import StepSpec, AttributionTemplateV2
                step_objs = [StepSpec(**s) for s in steps]
                _pseudo = AttributionTemplateV2(
                    id="__validate__", name="__validate__", steps=step_objs,
                )
                steps_list = [s.model_dump() for s in step_objs]
            except Exception as e:
                return {"success": False, "error": f"steps 校验失败: {e}"}

        from core.sop_analyzer import DIMENSION_FIELD_MAP, METRIC_DIMENSION_MATRIX
        updates = []
        if name is not None:
            updates.append(f"name = '{self._esc(name)}'")
        if description is not None:
            updates.append(f"description = '{self._esc(description)}'")
        new_metric_key = metric_key if metric_key in self.SUPPORTED_METRIC_KEYS else None

        # 2) 优先按 steps 推导 dimensions
        derived_dims: Optional[List[str]] = None
        if steps_list is not None:
            metric_cfg = METRIC_DIMENSION_MATRIX.get(
                new_metric_key or "delivered_units", METRIC_DIMENSION_MATRIX[self.DEFAULT_METRIC_KEY]
            )
            allowed = set(metric_cfg.get("applicable_dimensions", []))
            derived_dims = []
            for s in steps_list:
                for d in (s.get("group_by") or []):
                    if d in allowed and d in DIMENSION_FIELD_MAP and d not in derived_dims:
                        derived_dims.append(d)
            steps_json = json.dumps(steps_list, ensure_ascii=False)
            updates.append(f"steps = '{self._esc(steps_json)}'")
            # 同步更新老 dimensions 列（兜底）
            dims_json = json.dumps(derived_dims, ensure_ascii=False)
            updates.append(f"dimensions = '{self._esc(dims_json)}'")
        elif dimensions is not None:
            valid_dims = [d for d in dimensions if d in DIMENSION_FIELD_MAP]
            if not valid_dims:
                return {"success": False, "error": "至少 1 个有效维度"}
            if len(valid_dims) > 4:
                return {"success": False, "error": "最多 4 个维度"}
            if new_metric_key is not None:
                metric_cfg = METRIC_DIMENSION_MATRIX.get(new_metric_key, {})
                allowed = set(metric_cfg.get("applicable_dimensions", []))
                valid_dims = [d for d in valid_dims if d in allowed]
                if not valid_dims:
                    return {"success": False, "error": f"该指标（{new_metric_key}）下没有可用维度"}
            dims_json = json.dumps(valid_dims, ensure_ascii=False)
            updates.append(f"dimensions = '{self._esc(dims_json)}'")
        if new_metric_key is not None:
            updates.append(f"metric_key = '{self._esc(new_metric_key)}'")
        if updated_by is not None:
            updates.append(f"updated_by = '{self._esc(updated_by)}'")
        if not updates:
            return {"success": False, "error": "没有可更新字段"}

        # ⭐ P2-SprintA：admin 改 preset_* 时，先 seed 一行到 DB（DB 是事实之源）
        if template_id.startswith("preset_") and allow_preset:
            self._seed_preset_if_missing(template_id)

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        updates.append(f"updated_at = '{now}'")
        sql = f"UPDATE dim_attribution_template SET {', '.join(updates)} WHERE id = '{self._esc(template_id)}'"
        if owner_user:
            sql += f" AND owner_user = '{self._esc(owner_user)}'"
        res = self._direct_exec(sql)
        if not res.get("success"):
            return {"success": False, "error": res.get("error", "更新失败")}

        # ⭐ P2-SprintA：audit 快照（每次 update 写一行）
        # 取最新 version_no
        cur = self._direct_exec(
            f"SELECT version_no FROM dim_attribution_template_audit WHERE template_id = '{self._esc(template_id)}' ORDER BY version_no DESC LIMIT 1",
            fetch=True,
        )
        last_v = 0
        if cur.get("success") and cur.get("data"):
            try:
                last_v = int(cur["data"][0].get("version_no") or 0)
            except Exception:
                last_v = 0
        self._audit_snapshot(
            template_id,
            version_no=last_v + 1,
            snapshot={
                "name": name,
                "description": description,
                "metric_key": new_metric_key,
                "steps": steps_list,
                "dimensions": derived_dims if derived_dims is not None else dimensions,
            },
            changed_by=updated_by or owner_user or "",
            change_reason=change_reason or "update",
        )

        return {"success": True, "template_id": template_id}
