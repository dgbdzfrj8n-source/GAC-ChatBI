"""P2-1: 数据管理服务（CSV 导入 / 导出 / 列表 / 预览 / 删除）

设计原则：
  1. 严格遵守只读契约 —— 业务主库 gac_bi.duckdb 永远不动
  2. 用户上传数据 → 独立 user_data.duckdb 文件，存放在 data/user_uploads/
  3. 用户表名前缀统一 user_，避免与业务表名冲突
  4. CSV 智能识别：自动检测 header / 类型推断 / 大小写归一化
  5. 配额限制：单文件 ≤ 20MB，单表 ≤ 10万行，命名只允许 [a-z0-9_]

调用方：
  - GET    /api/data/uploads               列出用户表
  - POST   /api/data/upload                CSV 上传
  - GET    /api/data/preview/{table}       预览前 N 行
  - GET    /api/data/export/{table}        导出 CSV 下载
  - DELETE /api/data/{table}              删除用户表
  - GET    /api/data/stats                 库容量统计
"""

import csv
import io
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# 依赖
try:
    import duckdb
    HAS_DUCKDB = True
except ImportError:
    HAS_DUCKDB = False

# 路径
BACKEND_DIR = Path(__file__).parent.parent
DATA_DIR = BACKEND_DIR / "data"
USER_DIR = DATA_DIR / "user_uploads"
USER_DB_PATH = DATA_DIR / "user_data.duckdb"

# 配额
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20MB
MAX_ROWS_PER_TABLE = 100_000
MAX_TABLES = 50
TABLE_PREFIX = "user_"
TABLE_NAME_RE = re.compile(r"^[a-z0-9_]{2,40}$")

# 业务主库表名（用于冲突检测）
BUSINESS_TABLES = {
    "fact_sales_daily",
    "dim_budget_target",
    "fact_marketing_expenses",
}


def _ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    USER_DIR.mkdir(parents=True, exist_ok=True)


def _validate_table_name(raw: str) -> str:
    """校验并返回合法表名（自动加 user_ 前缀）"""
    name = raw.strip().lower()
    # 移除文件扩展名
    name = re.sub(r"\.csv$", "", name)
    # 允许中文 + 字母数字下划线，去除其他字符
    name = re.sub(r"[^a-z0-9_\u4e00-\u9fa5]", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    if not name or len(name) < 2:
        raise ValueError("表名至少 2 个有效字符")
    if len(name) > 36:
        name = name[:36]
    full = TABLE_PREFIX + name
    if full in BUSINESS_TABLES:
        raise ValueError(f"表名 {full} 与业务表冲突")
    return full


def _normalize_col(col: str) -> str:
    """列名归一化：snake_case + 去除非法字符"""
    c = col.strip().lower()
    # 中文列名转拼音暂不支持，统一用拼音替换为 transliteration 友好字符
    c = re.sub(r"[\s\-\.\(\)（）]", "_", c)
    c = re.sub(r"[^a-z0-9_\u4e00-\u9fa5]", "", c)
    c = re.sub(r"_+", "_", c).strip("_")
    return c or "col"


def _infer_csv_columns(content: str) -> Tuple[List[str], List[str]]:
    """读取 CSV 第一行，返回 (原始列名, 归一化列名)"""
    reader = csv.reader(io.StringIO(content))
    try:
        header = next(reader)
    except StopIteration:
        raise ValueError("CSV 文件为空")
    raw_cols = [h.strip() for h in header]
    norm_cols = []
    seen = set()
    for c in raw_cols:
        n = _normalize_col(c)
        # 处理重名列
        original = n
        i = 2
        while n in seen:
            n = f"{original}_{i}"
            i += 1
        seen.add(n)
        norm_cols.append(n)
    if len(set(norm_cols)) != len(norm_cols):
        raise ValueError("列名归一化后仍有冲突，请规范化 CSV 表头")
    return raw_cols, norm_cols


def _count_csv_rows(content: str) -> int:
    """统计 CSV 行数（不含表头）"""
    return sum(1 for _ in csv.reader(io.StringIO(content))) - 1


def list_user_tables() -> List[Dict[str, Any]]:
    """列出所有用户上传的表"""
    _ensure_dirs()
    if not USER_DB_PATH.exists():
        return []
    if not HAS_DUCKDB:
        raise RuntimeError("DuckDB 未安装")
    con = duckdb.connect(str(USER_DB_PATH), read_only=True)
    try:
        rows = con.execute(
            f"SELECT table_name FROM information_schema.tables "
            f"WHERE table_schema = 'main' AND table_name LIKE '{TABLE_PREFIX}%' "
            f"ORDER BY table_name"
        ).fetchall()
        result = []
        for (tname,) in rows:
            try:
                cnt = con.execute(f'SELECT COUNT(*) FROM "{tname}"').fetchone()[0]
                cols = con.execute(
                    f"SELECT column_name, data_type FROM information_schema.columns "
                    f"WHERE table_name = ? ORDER BY ordinal_position",
                    [tname],
                ).fetchall()
                result.append({
                    "table_name": tname,
                    "row_count": cnt,
                    "column_count": len(cols),
                    "columns": [{"name": c, "type": t} for c, t in cols[:10]],
                })
            except Exception as e:
                result.append({
                    "table_name": tname,
                    "error": str(e),
                })
        return result
    finally:
        con.close()


def import_csv(content: str, table_name: str) -> Dict[str, Any]:
    """
    导入 CSV 到用户库
    返回：表名 / 行数 / 列数 / 列定义 / 耗时
    """
    _ensure_dirs()
    if not HAS_DUCKDB:
        raise RuntimeError("DuckDB 未安装")
    if len(content.encode("utf-8")) > MAX_FILE_SIZE_BYTES:
        raise ValueError(f"文件超过 {MAX_FILE_SIZE_BYTES // 1024 // 1024}MB 限制")

    full_name = _validate_table_name(table_name)

    # 检查重名（业务表 + 用户表）
    existing = {t["table_name"] for t in list_user_tables()}
    if full_name in existing:
        raise ValueError(f"表 {full_name} 已存在，请先删除或换名")
    if len(existing) >= MAX_TABLES:
        raise ValueError(f"用户表数量已达上限 {MAX_TABLES}")

    raw_cols, norm_cols = _infer_csv_columns(content)
    row_count = _count_csv_rows(content)
    if row_count == 0:
        raise ValueError("CSV 没有数据行")
    if row_count > MAX_ROWS_PER_TABLE:
        raise ValueError(f"行数 {row_count} 超过 {MAX_ROWS_PER_TABLE} 上限")

    # 写入临时文件，CREATE TABLE + COPY
    tmp_csv = USER_DIR / f"_tmp_{int(time.time())}_{full_name}.csv"
    tmp_csv.write_text(content, encoding="utf-8")

    start = time.perf_counter()
    con = duckdb.connect(str(USER_DB_PATH))
    try:
        col_defs = ", ".join(f'"{c}" VARCHAR' for c in norm_cols)
        con.execute(f'CREATE TABLE "{full_name}" ({col_defs})')
        # COPY 自动类型推断（VARCHAR 入库）
        con.execute(
            f"COPY \"{full_name}\" FROM '{tmp_csv.as_posix()}' (HEADER TRUE, DELIMITER ',', QUOTE '\"')"
        )
        # 智能类型推断：尝试转数字 / 日期
        _auto_cast_types(con, full_name, norm_cols, content)
        elapsed_ms = round((time.perf_counter() - start) * 1000, 1)

        # 统计结果
        cnt = con.execute(f'SELECT COUNT(*) FROM "{full_name}"').fetchone()[0]
        cols_info = con.execute(
            f"SELECT column_name, data_type FROM information_schema.columns "
            f"WHERE table_name = ? ORDER BY ordinal_position",
            [full_name],
        ).fetchall()
        # 保存原始 CSV 副本（用于导出）
        archive_path = USER_DIR / f"{full_name}.csv"
        tmp_csv.rename(archive_path)
    finally:
        con.close()
        # 清理临时（如果 rename 失败）
        if tmp_csv.exists():
            try:
                tmp_csv.unlink()
            except Exception:
                pass

    return {
        "table_name": full_name,
        "row_count": cnt,
        "column_count": len(cols_info),
        "raw_columns": raw_cols,
        "columns": [{"name": c, "type": t} for c, t in cols_info],
        "elapsed_ms": elapsed_ms,
        "imported_at": datetime.now().isoformat(timespec="seconds"),
    }


def _auto_cast_types(con, table: str, cols: List[str], content: str) -> None:
    """智能类型推断：扫前 100 行，如果全是数字就转 DOUBLE，全是日期就转 DATE"""
    # 取前 100 行做样本
    lines = content.split("\n")
    sample = "\n".join(lines[1:101]) if len(lines) > 1 else ""
    if not sample.strip():
        return

    reader = csv.reader(io.StringIO(sample))
    rows = list(reader)
    if not rows:
        return
    n_cols = len(cols)
    for i, col in enumerate(cols):
        if i >= n_cols:
            break
        col_values = [r[i] for r in rows if i < len(r) and r[i].strip()]
        if not col_values:
            continue
        # 检测 INTEGER
        if all(_is_int(v) for v in col_values[:50]):
            try:
                con.execute(f'ALTER TABLE "{table}" ALTER COLUMN "{col}" TYPE BIGINT')
                continue
            except Exception:
                pass
        # 检测 DOUBLE
        if all(_is_float(v) for v in col_values[:50]):
            try:
                con.execute(f'ALTER TABLE "{table}" ALTER COLUMN "{col}" TYPE DOUBLE')
                continue
            except Exception:
                pass
        # 检测 DATE（YYYY-MM-DD）
        if all(_is_date(v) for v in col_values[:50]):
            try:
                con.execute(f'ALTER TABLE "{table}" ALTER COLUMN "{col}" TYPE DATE')
                continue
            except Exception:
                pass


def _is_int(v: str) -> bool:
    try:
        int(v.strip())
        return True
    except Exception:
        return False


def _is_float(v: str) -> bool:
    try:
        float(v.strip())
        return True
    except Exception:
        return False


def _is_date(v: str) -> bool:
    return bool(re.match(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}", v.strip()))


def preview_table(table_name: str, limit: int = 50) -> Dict[str, Any]:
    """预览表前 N 行"""
    _ensure_dirs()
    if not USER_DB_PATH.exists():
        raise ValueError("用户库为空")
    full = _validate_table_name(table_name)  # 自动加前缀
    con = duckdb.connect(str(USER_DB_PATH), read_only=True)
    try:
        cnt = con.execute(f'SELECT COUNT(*) FROM "{full}"').fetchone()[0]
        cursor = con.execute(f'SELECT * FROM "{full}" LIMIT ?', [limit])
        cols = [d[0] for d in cursor.description]
        data = [dict(zip(cols, row)) for row in cursor.fetchall()]
        return {"table_name": full, "row_count": cnt, "columns": cols, "data": data, "preview_limit": limit}
    finally:
        con.close()


def export_table_csv(table_name: str) -> str:
    """导出表为 CSV 字符串"""
    _ensure_dirs()
    full = _validate_table_name(table_name)
    con = duckdb.connect(str(USER_DB_PATH), read_only=True)
    try:
        cursor = con.execute(f'SELECT * FROM "{full}"')
        cols = [d[0] for d in cursor.description]
        rows = cursor.fetchall()
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(cols)
        for r in rows:
            writer.writerow(["" if v is None else v for v in r])
        return buf.getvalue()
    finally:
        con.close()


def delete_table(table_name: str) -> Dict[str, Any]:
    """删除用户表 + 归档 CSV"""
    _ensure_dirs()
    full = _validate_table_name(table_name)
    con = duckdb.connect(str(USER_DB_PATH))
    try:
        con.execute(f'DROP TABLE IF EXISTS "{full}"')
    finally:
        con.close()
    # 删除归档 CSV
    archive = USER_DIR / f"{full}.csv"
    if archive.exists():
        try:
            archive.unlink()
        except Exception:
            pass
    return {"table_name": full, "deleted": True}


def get_stats() -> Dict[str, Any]:
    """库容量统计"""
    _ensure_dirs()
    tables = list_user_tables()
    total_rows = sum(t.get("row_count", 0) for t in tables)
    # 数据库文件大小
    db_size = 0
    if USER_DB_PATH.exists():
        db_size = USER_DB_PATH.stat().st_size
    # CSV 归档总大小
    csv_size = sum(
        f.stat().st_size for f in USER_DIR.glob("*.csv") if f.is_file()
    )
    return {
        "table_count": len(tables),
        "total_rows": total_rows,
        "db_size_bytes": db_size,
        "csv_size_bytes": csv_size,
        "quota": {
            "max_tables": MAX_TABLES,
            "max_rows_per_table": MAX_ROWS_PER_TABLE,
            "max_file_size_bytes": MAX_FILE_SIZE_BYTES,
        },
        "tables": [t["table_name"] for t in tables],
    }
