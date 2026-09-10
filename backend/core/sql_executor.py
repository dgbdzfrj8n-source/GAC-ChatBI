"""
SQL 执行器与安全防护模块
核心职责：
1. 安全拦截（AST/正则级过滤）：严禁任何 DDL/DML（INSERT/UPDATE/DELETE/DROP/ALTER/TRUNCATE），只允许只读分析（SELECT/WITH）；
2. 双引擎支持：自动探测优先连接 DuckDB，平滑兼容原生 SQLite3，确保 0 配置即开即跑；
3. 执行监控：捕获耗时、扫描行数与错误堆栈，为自愈重试提供精确定位。
"""

import os
import re
import time
import sqlite3
from typing import Dict, Any, List, Tuple

# 探测 DuckDB
try:
    import duckdb
    HAS_DUCKDB = True
except ImportError:
    HAS_DUCKDB = False

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(CURRENT_DIR), "data")
DUCKDB_PATH = os.path.join(DATA_DIR, "gac_bi.duckdb")
SQLITE_PATH = os.path.join(DATA_DIR, "gac_bi.db")

FORBIDDEN_PATTERNS = [
    r"\bDROP\b",
    r"\bDELETE\b",
    r"\bUPDATE\b",
    r"\bINSERT\b",
    r"\bALTER\b",
    r"\bTRUNCATE\b",
    r"\bCREATE\b",
    r"\bREPLACE\b",
    r"\bGRANT\b",
    r"\bREVOKE\b",
    r"\bEXEC\b",
    r"\bEXECUTE\b",
    r"--",        # 单行注释注入
    r";\s*\S",    # 多语句堆叠注入
]

class SqlExecutor:
    def __init__(self):
        if HAS_DUCKDB and os.path.exists(DUCKDB_PATH):
            self.engine_type = "DuckDB"
            self.db_path = DUCKDB_PATH
        else:
            self.engine_type = "SQLite3"
            self.db_path = SQLITE_PATH

    def validate_safe_sql(self, raw_sql: str) -> Tuple[bool, str, str]:
        """
        只读语法拦截，防止恶意注入或破坏性变更
        """
        clean_sql = raw_sql.strip()
        # 去除首尾反引号或分号
        clean_sql = re.sub(r"^```(sql)?", "", clean_sql, flags=re.IGNORECASE).strip()
        clean_sql = re.sub(r"```$", "", clean_sql).strip()
        
        if not clean_sql:
            return False, "SQL 语句为空", ""

        # 检查是否包含危险关键字
        for pattern in FORBIDDEN_PATTERNS:
            if re.search(pattern, clean_sql, re.IGNORECASE):
                return False, f"安全策略拦截：检测到非法操作或未授权关键字 [{pattern}]，仅允许执行只读分析（SELECT/WITH）", ""

        # 必须以 SELECT 或 WITH 开头
        upper_first = clean_sql.split()[0].upper()
        if upper_first not in ["SELECT", "WITH"]:
            return False, f"安全策略拦截：查询必须以 SELECT 或 WITH 引导，当前为 [{upper_first}]", ""

        # 清除结尾的分号
        if clean_sql.endswith(";"):
            clean_sql = clean_sql[:-1].strip()

        return True, "校验通过", clean_sql

    def execute_query(self, raw_sql: str) -> Dict[str, Any]:
        """
        执行只读 SQL 查询，返回结构化数据与执行耗时
        """
        is_safe, msg, clean_sql = self.validate_safe_sql(raw_sql)
        if not is_safe:
            return {
                "success": False,
                "error": msg,
                "engine": self.engine_type,
                "sql": raw_sql,
                "data": [],
                "columns": [],
                "row_count": 0,
                "execution_time_ms": 0
            }

        start_time = time.perf_counter()
        try:
            if self.engine_type == "DuckDB":
                con = duckdb.connect(self.db_path, read_only=True)
                cursor = con.execute(clean_sql)
                col_names = [desc[0] for desc in cursor.description] if cursor.description else []
                raw_rows = cursor.fetchall()
                con.close()
            else:
                con = sqlite3.connect(self.db_path)
                con.row_factory = sqlite3.Row
                cursor = con.cursor()
                cursor.execute(clean_sql)
                col_names = [col[0] for col in cursor.description] if cursor.description else []
                raw_rows = [list(row) for row in cursor.fetchall()]
                con.close()

            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

            # 转换为 dict records
            records = []
            for row in raw_rows:
                records.append(dict(zip(col_names, row)))

            return {
                "success": True,
                "engine": self.engine_type,
                "sql": clean_sql,
                "columns": col_names,
                "data": records,
                "row_count": len(records),
                "execution_time_ms": elapsed_ms,
                "error": None
            }

        except Exception as e:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return {
                "success": False,
                "engine": self.engine_type,
                "sql": clean_sql,
                "error": f"数据库执行异常: {str(e)}",
                "columns": [],
                "data": [],
                "row_count": 0,
                "execution_time_ms": elapsed_ms
            }

if __name__ == "__main__":
    executor = SqlExecutor()
    print(f"当前运行引擎: {executor.engine_type} ({executor.db_path})")

    # 1. 测试安全拦截
    bad_sql = "DROP TABLE fact_sales_daily;"
    res = executor.execute_query(bad_sql)
    print("恶意 SQL 拦截测试:", "拦截成功" if not res["success"] else "失败", res["error"])

    # 2. 测试合法查询
    good_sql = "SELECT brand_name, sum(delivered_units) as units FROM fact_sales_daily GROUP BY brand_name ORDER BY units DESC"
    res = executor.execute_query(good_sql)
    print(f"合法 SQL 执行测试: 成功={res['success']}, 行数={res['row_count']}, 耗时={res['execution_time_ms']}ms")
    print("数据样例:", res["data"][:2])
