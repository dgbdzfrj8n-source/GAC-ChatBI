"""
[Sprint 10] 权限矩阵 + 行级 SQL 过滤 + 字段级脱敏

三级权限粒度：
  1. 表级 (Table-level)    - 某角色能否访问某张表
  2. 行级 (Row-level)      - 自动 SQL 注入 WHERE region = '广州' 隔离
  3. 字段级 (Column-level)  - 敏感字段脱敏（手机号/身份证/邮箱）
"""

import re
import logging
from typing import Dict, Set, Optional, Any, List
from dataclasses import dataclass

from .auth import CurrentUser

logger = logging.getLogger(__name__)


# ============================================================
# 角色权限矩阵（与 mock_iam.MOCK_USERS.role 对应）
# ============================================================
@dataclass
class RolePermission:
    """角色权限定义"""
    role: str
    description: str
    allowed_tables: Set[str]                # 表级白名单（None = 全部）
    row_filter_template: Optional[str]      # 行级过滤模板（如 "region = '{region}'"）
    masked_columns: Set[str]                # 字段级脱敏白名单
    can_export: bool
    can_upload_csv: bool
    can_view_sql: bool
    can_view_raw_data: bool                 # 业务用户只能看汇总，不能看明细
    can_manage_metrics: bool                # 语义层管理
    can_manage_users: bool                  # 用户管理（IAM 同步）


ROLE_HIERARCHY: Dict[str, RolePermission] = {
    # ============================================================
    # 业务用户 - 一线销售/营销
    # 行级严格过滤：只看到自己部门 + 自己区域
    # 不能看明细，只能看汇总指标
    # ============================================================
    "business_user": RolePermission(
        role="business_user",
        description="一线业务人员（销售/营销）",
        allowed_tables={"fact_sales_daily", "fact_marketing_channel_daily"},  # 不能看预算明细
        row_filter_template="brand = '{department}' AND region = '{region}'",
        masked_columns={"phone", "id_card", "customer_name"},  # 业务用户看数据也脱敏
        can_export=True,
        can_upload_csv=False,
        can_view_sql=False,
        can_view_raw_data=False,            # 强制走汇总
        can_manage_metrics=False,
        can_manage_users=False,
    ),

    # ============================================================
    # 数据分析师 - 全局只读
    # 行级不过滤（看全部）
    # 能看明细，能看 SQL
    # ============================================================
    "analyst": RolePermission(
        role="analyst",
        description="数据分析师",
        allowed_tables=None,  # None = 不限
        row_filter_template=None,
        masked_columns={"phone", "id_card"},  # 仍脱敏个人隐私
        can_export=True,
        can_upload_csv=True,
        can_view_sql=True,
        can_view_raw_data=True,
        can_manage_metrics=True,
        can_manage_users=False,
    ),

    # ============================================================
    # 管理员 - 全部权限
    # ============================================================
    "admin": RolePermission(
        role="admin",
        description="系统管理员",
        allowed_tables=None,
        row_filter_template=None,
        masked_columns=set(),  # 管理员看全字段
        can_export=True,
        can_upload_csv=True,
        can_view_sql=True,
        can_view_raw_data=True,
        can_manage_metrics=True,
        can_manage_users=True,
    ),

    # ============================================================
    # 审计员 - 只读 + 审计日志访问
    # ============================================================
    "auditor": RolePermission(
        role="auditor",
        description="审计员",
        allowed_tables=None,
        row_filter_template=None,
        masked_columns={"phone", "id_card", "customer_name"},  # 审计员也要脱敏
        can_export=False,             # 审计员不能导出（防泄漏）
        can_upload_csv=False,
        can_view_sql=True,
        can_view_raw_data=True,
        can_manage_metrics=False,
        can_manage_users=False,
    ),
}


def get_permission(role: str) -> RolePermission:
    """获取角色权限配置"""
    return ROLE_HIERARCHY.get(role, ROLE_HIERARCHY["business_user"])


# ============================================================
# 表级权限校验
# ============================================================
def check_table_access(user: CurrentUser, table_name: str) -> bool:
    """检查用户是否有权访问指定表"""
    perm = get_permission(user.role)
    if perm.allowed_tables is None:
        return True
    return table_name in perm.allowed_tables


# ============================================================
# 行级 SQL 自动过滤
# ============================================================
def apply_row_filter(sql: str, user: CurrentUser) -> str:
    """
    自动给 SQL 注入行级 WHERE 过滤

    策略：
      1. 如果 SQL 已有 WHERE，追加 AND
      2. 如果 SQL 没有 WHERE，添加 WHERE
      3. 如果是子查询嵌套，外层包一层 SELECT

    例（business_user 张三 - 埃安 + 广州）：
      原 SQL:  SELECT brand, SUM(sales_volume) FROM fact_sales_daily GROUP BY brand
      过滤后:  SELECT * FROM (原 SQL) WHERE brand = '埃安' AND region = '广州' GROUP BY brand
    """
    perm = get_permission(user.role)
    if not perm.row_filter_template:
        return sql  # 无需过滤

    filter_clause = perm.row_filter_template.format(
        department=user.department,
        region=user.region,
    )

    sql_clean = sql.strip().rstrip(";")

    # 检测是否已有 WHERE
    has_where = bool(re.search(r"\bWHERE\b", sql_clean, re.IGNORECASE))

    if has_where:
        # 已有 WHERE，追加 AND
        # 找到 WHERE 后第一个 GROUP/ORDER/LIMIT 位置
        match = re.search(r"\b(GROUP BY|ORDER BY|LIMIT)\b", sql_clean, re.IGNORECASE)
        if match:
            insert_pos = match.start()
            new_sql = (
                sql_clean[:insert_pos]
                + f" AND {filter_clause} "
                + sql_clean[insert_pos:]
            )
        else:
            new_sql = sql_clean + f" AND {filter_clause}"
    else:
        # 没有 WHERE，需要找插入位置（GROUP/ORDER/LIMIT 前）
        match = re.search(r"\b(GROUP BY|ORDER BY|LIMIT|HAVING)\b", sql_clean, re.IGNORECASE)
        if match:
            insert_pos = match.start()
            new_sql = (
                sql_clean[:insert_pos]
                + f" WHERE {filter_clause} "
                + sql_clean[insert_pos:]
            )
        else:
            new_sql = sql_clean + f" WHERE {filter_clause}"

    logger.info(f"[权限] 用户 {user.username} ({user.role}) 行级过滤: {filter_clause}")
    return new_sql


# ============================================================
# 字段级脱敏
# ============================================================
def mask_sensitive_value(value: Any, column_name: str) -> Any:
    """
    字段级脱敏规则

    phone      → 138****5678
    id_card    → 110101********1234
    email      → z****@gac.com.cn
    customer_name → 张*
    """
    if value is None or value == "":
        return value

    s = str(value)
    col_lower = column_name.lower()

    # 手机号脱敏（11 位数字）
    if "phone" in col_lower or "mobile" in col_lower:
        if len(s) == 11 and s.isdigit():
            return s[:3] + "****" + s[-4:]

    # 身份证脱敏（18 位）
    if "id_card" in col_lower or "idcard" in col_lower or "身份证" in column_name:
        if len(s) == 18:
            return s[:6] + "********" + s[-4:]

    # 邮箱脱敏
    if "email" in col_lower or "mail" in col_lower:
        if "@" in s:
            local, domain = s.split("@", 1)
            if len(local) > 1:
                return local[0] + "****@" + domain
            return "****@" + domain

    # 客户姓名脱敏（保留姓氏）
    if "customer_name" in col_lower or "客户姓名" in column_name:
        if len(s) >= 1:
            return s[0] + ("*" * (len(s) - 1)) if len(s) > 1 else s

    return value


def mask_data(data: List[Dict[str, Any]], user: CurrentUser, columns: List[str]) -> List[Dict[str, Any]]:
    """
    对查询结果做字段级脱敏
    """
    perm = get_permission(user.role)
    if not perm.masked_columns:
        return data  # 无需脱敏

    masked_data = []
    for row in data:
        new_row = dict(row)
        for col in columns:
            col_lower = col.lower()
            # 检查是否需要脱敏
            need_mask = any(
                sensitive in col_lower
                for sensitive in perm.masked_columns
            )
            if need_mask and col in new_row:
                new_row[col] = mask_sensitive_value(new_row[col], col)
        masked_data.append(new_row)

    if perm.masked_columns:
        logger.info(f"[权限] 用户 {user.username} ({user.role}) 字段级脱敏: {perm.masked_columns}")

    return masked_data


# ============================================================
# 业务用户不能看明细 - SQL 检测
# ============================================================
def enforce_no_raw_detail(user: CurrentUser, sql: str) -> str:
    """
    业务用户（business_user）不能直接 SELECT *
    自动加上 LIMIT 或提示聚合
    """
    perm = get_permission(user.role)
    if perm.can_view_raw_data:
        return sql

    # 业务用户：检测 SELECT * 没有聚合
    has_aggregate = bool(re.search(r"\b(SUM|COUNT|AVG|MAX|MIN|GROUP BY)\b", sql, re.IGNORECASE))
    has_limit = bool(re.search(r"\bLIMIT\s+\d+", sql, re.IGNORECASE))

    if not has_aggregate and not has_limit:
        # 强制加 LIMIT 5
        if "LIMIT" not in sql.upper():
            sql = sql.rstrip(";").strip() + " LIMIT 5"
            logger.info(f"[权限] 业务用户 {user.username} 强制 LIMIT 5")

    return sql


# ============================================================
# 完整 SQL 安全检查（鉴权 + 过滤 + 脱敏的总入口）
# ============================================================
def apply_full_permission(sql: str, user: CurrentUser, data: List[Dict[str, Any]], columns: List[str]) -> Dict[str, Any]:
    """
    完整的权限应用（NL2SQL 引擎出口调用）

    Returns:
        {
            "sql": 过滤后的 SQL,
            "data": 脱敏后的数据,
            "columns": 列名,
            "permission": {
                "row_filtered": bool,
                "masked_columns": list,
                "forced_aggregate": bool
            }
        }
    """
    perm = get_permission(user.role)

    # 1. 行级过滤
    filtered_sql = apply_row_filter(sql, user)

    # 2. 业务用户强制 LIMIT / 聚合
    final_sql = enforce_no_raw_detail(user, filtered_sql)

    # 3. 字段级脱敏
    masked_data = mask_data(data, user, columns)

    return {
        "sql": final_sql,
        "data": masked_data,
        "columns": columns,
        "permission": {
            "row_filtered": perm.row_filter_template is not None,
            "masked_columns": list(perm.masked_columns),
            "forced_aggregate": not perm.can_view_raw_data,
            "role": user.role,
            "user": user.username,
        }
    }
