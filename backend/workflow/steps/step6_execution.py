"""
Step6: 执行校验
谁做：规则（DuckDB执行器 + AST安全检查 + 校验规则，不用LLM）
输入：sql
输出：result + execution_time_ms + validation_passed + validation_errors

执行顺序（4层校验）：
1. AST安全检查
2. DuckDB执行
3. 结果非空校验
4. 数据合理性校验
"""

import re
import time
from typing import Tuple, Optional
from workflow.context import WorkflowContext, QueryResult


# AST安全检查：允许和禁止的关键字
ALLOWED_KEYWORDS = ["SELECT", "WITH", "AS", "FROM", "WHERE", "JOIN", "LEFT", "RIGHT", 
                    "INNER", "OUTER", "ON", "GROUP", "BY", "ORDER", "ASC", "DESC",
                    "LIMIT", "OFFSET", "HAVING", "UNION", "ALL", "DISTINCT",
                    "AND", "OR", "NOT", "IN", "BETWEEN", "LIKE", "IS", "NULL",
                    "CASE", "WHEN", "THEN", "ELSE", "END",
                    "SUM", "COUNT", "AVG", "MAX", "MIN", "ROUND", "NULLIF",
                    "STRFTIME", "DATE", "CAST", "COALESCE", "ABS"]

FORBIDDEN_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "REPLACE",
    "TRUNCATE", "GRANT", "REVOKE", "EXEC", "EXECUTE",
]


def validate_sql_syntax(sql: str) -> Tuple[bool, str, str]:
    """
    SQL 语法基础校验（正则级）
    
    Returns:
        (is_valid, error_message, cleaned_sql)
    """
    if not sql or not sql.strip():
        return False, "SQL 语句为空", ""
    
    cleaned = sql.strip()
    
    # 去除首尾反引号和 markdown 代码块标记
    cleaned = re.sub(r"^```(?:sql)?", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    
    # 必须以 SELECT 或 WITH 开头
    first_word = cleaned.split()[0].upper() if cleaned.split() else ""
    if first_word not in ["SELECT", "WITH"]:
        return False, f"SQL 必须以 SELECT 或 WITH 开头，当前为 {first_word}", ""
    
    # 检查危险关键字
    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(rf'\b{keyword}\b', cleaned, re.IGNORECASE):
            return False, f"检测到未授权关键字 [{keyword}]，仅允许 SELECT 查询", ""
    
    # 检查多语句（分号后有内容）
    parts = cleaned.split(';')
    if len(parts) > 1:
        non_empty_parts = [p.strip() for p in parts if p.strip()]
        if len(non_empty_parts) > 1:
            return False, "检测到多语句执行，仅支持单条 SELECT 查询", ""
    
    # 去除结尾分号
    if cleaned.endswith(';'):
        cleaned = cleaned[:-1].strip()
    
    # SQL 长度检查
    if len(cleaned) > 5000:
        return False, f"SQL 语句过长（{len(cleaned)} 字符），最大支持 5000 字符", ""
    
    return True, "", cleaned


def execute_ast_check(sql: str) -> Tuple[bool, str]:
    """
    AST 安全检查（使用 sqlglot 如果可用）
    """
    try:
        import sqlglot
        
        # 解析 SQL
        try:
            statements = sqlglot.parse(sql, dialect="duckdb")
        except:
            statements = sqlglot.parse(sql)
        
        if not statements:
            return False, "SQL 解析失败"
        
        for stmt in statements:
            # 只允许 SELECT
            if not isinstance(stmt, sqlglot.exp.Select):
                return False, f"仅允许 SELECT 语句，不允许 {type(stmt).__name__}"
        
        return True, ""
    
    except ImportError:
        # 如果没有 sqlglot，使用正则校验
        return validate_sql_syntax(sql)
    
    except Exception as e:
        return False, f"AST 检查异常: {str(e)}"


def execute_query(sql: str) -> Tuple[bool, dict]:
    """
    执行 SQL 查询
    
    Returns:
        (success, result_dict)
    """
    try:
        # 导入执行器
        from core.sql_executor import SqlExecutor
        
        executor = SqlExecutor()
        result = executor.execute_query(sql)
        
        return result["success"], result
    
    except Exception as e:
        return False, {
            "error": f"查询执行异常: {str(e)}",
            "columns": [],
            "data": [],
            "row_count": 0,
            "execution_time_ms": 0
        }


def validate_result(result: dict) -> Tuple[bool, list]:
    """
    验证查询结果的合理性
    
    Returns:
        (is_valid, warnings)
    """
    warnings = []
    
    if not result.get("success"):
        return False, ["查询执行失败"]
    
    data = result.get("data", [])
    columns = result.get("columns", [])
    
    # 检查空结果
    if not data or len(data) == 0:
        warnings.append("查询结果为空")
    
    # 检查数值列的合理性
    for row in data:
        for col_idx, col_name in enumerate(columns):
            if col_name and any(keyword in col_name.lower() for keyword in ["率", "ratio", "rate", "pct"]):
                if col_idx < len(row) and row[col_idx] is not None:
                    try:
                        val = float(row[col_idx])
                        if val < 0:
                            warnings.append(f"指标 {col_name} 为负数: {val}")
                        if val > 200:
                            warnings.append(f"指标 {col_name} 异常偏高: {val}%")
                    except (ValueError, TypeError):
                        pass
    
    # 检查行数与粒度是否匹配
    # （简化版：主要靠 SQL 生成保证）
    
    return True, warnings


def execute(context: WorkflowContext) -> bool:
    """
    执行校验步骤
    
    Returns:
        True: 成功，继续下一步
        False: 失败（进入重试或错误分支）
    """
    start_time = time.time()
    
    if not context.sql:
        context.set_error(
            code="SQL_GENERATION_ERROR",
            message="未能生成有效 SQL",
            detail="SQL 生成步骤未产出有效语句",
            suggestion="请换个问法或稍后重试"
        )
        return False
    
    # 第1层：AST 安全检查
    is_safe, error_msg = execute_ast_check(context.sql)
    if not is_safe:
        context.set_error(
            code="SQL_SECURITY_ERROR",
            message=f"SQL 安全检查未通过: {error_msg}",
            detail=f"禁止的 SQL 内容: {context.sql[:200]}",
            suggestion="您的查询包含不允许的操作，请换一种问法"
        )
        return False
    
    # 第2层：DuckDB 执行
    success, exec_result = execute_query(context.sql)
    context.execution_time_ms = exec_result.get("execution_time_ms", 0)
    
    if not success:
        error_msg = exec_result.get("error", "未知错误")
        
        # 判断是否可重试
        context.sql_attempts += 1
        
        if context.sql_attempts < 3:
            # 记录重试信息，但不立即返回
            context.validation_errors.append(f"执行失败（第{context.sql_attempts}次）: {error_msg}")
            # 返回 True 让编排器决定是否重试
            return False
        else:
            context.set_error(
                code="SQL_EXECUTION_ERROR",
                message=f"SQL 执行失败: {error_msg}",
                detail=f"已重试 {context.sql_attempts} 次",
                suggestion="换个问法或简化查询条件"
            )
            return False
    
    # 第3层：结果非空校验
    if not exec_result.get("data") or len(exec_result.get("data", [])) == 0:
        context.validation_errors.append("查询结果为空")
    
    # 第4层：数据合理性校验
    is_valid, warnings = validate_result(exec_result)
    context.validation_errors.extend(warnings)
    
    # 构建 QueryResult
    columns = exec_result.get("columns", [])
    rows = []
    for row in exec_result.get("data", []):
        if isinstance(row, dict):
            rows.append([row.get(col) for col in columns])
        else:
            rows.append(list(row) if row else [])
    
    context.result = QueryResult(
        columns=columns,
        rows=rows,
        row_count=len(rows)
    )
    
    context.validation_passed = is_valid
    
    duration_ms = int((time.time() - start_time) * 1000)
    
    # 记录思考链
    content = f"DuckDB 执行成功，返回 {context.result.row_count} 行 {len(columns)} 列。"
    content += f"耗时 {context.execution_time_ms}ms。"
    
    if context.validation_errors:
        content += f" 警告：{'; '.join(context.validation_errors)}"
    
    context.add_thinking_step(
        step=6,
        name="执行校验",
        content=content,
        status="done",
        duration_ms=duration_ms
    )
    
    return True
