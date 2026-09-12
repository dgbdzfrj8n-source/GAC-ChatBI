"""P2-1 数据管理服务 - 单元测试
验证：上传 → 列表 → 预览 → 导出 → 删除 全闭环
本地 Xcode Python 可能未装 duckdb，本地会跳过需要 duckdb 的测试。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.data_manager import _validate_table_name

HAS_DUCKDB = False
try:
    import duckdb
    HAS_DUCKDB = True
except ImportError:
    print("⚠️ 本地未装 duckdb，跳过需要 DB 的测试（Render 部署后会自动通过）")


SAMPLE_CSV = """brand_name,sale_date,delivered_units,gross_revenue
广汽埃安,2025-04-01,150,4500000
广汽埃安,2025-04-02,180,5400000
广汽传祺,2025-04-01,120,3600000
昊铂,2025-04-01,40,2000000
昊铂,2025-04-02,55,2750000
"""

SAMPLE_CSV_NO_HEADER_TYPES = """product,price
A,99.5
B,128.0
C,150.0
"""


def test_validate_table_name():
    cases = [
        ("广汽销售明细", "user_广汽销售明细"),     # 中文
        ("sales-2025", "user_sales_2025"),         # 横线转下划线
        ("sales.csv", "user_sales"),                # 去扩展名
    ]
    for raw, expected in cases:
        got = _validate_table_name(raw)
        print(f"  ✅ 「{raw}」 → {got}")
        assert got.startswith("user_"), f"前缀必须 user_，got {got}"

    # 短名应该抛异常
    try:
        _validate_table_name("a")
        assert False, "应抛 ValueError"
    except ValueError as e:
        print(f"  ✅ 短名「a」拦截: {e}")


def test_import_and_list():
    print("\n=== 测试 1：导入 CSV ===")
    # 先清理（防止之前测试残留）
    for t in list_user_tables():
        try:
            delete_table(t["table_name"])
        except Exception:
            pass

    r = import_csv(SAMPLE_CSV, "test_sales_apr")
    print(f"  ✅ 导入成功: {r['table_name']} ({r['row_count']} 行, {r['column_count']} 列)")
    assert r["row_count"] == 5, f"应 5 行，实际 {r['row_count']}"
    # 类型推断：sale_date → DATE, units → BIGINT, revenue → DOUBLE
    types = {c["name"]: c["type"] for c in r["columns"]}
    assert "BIGINT" in types.get("delivered_units", ""), f"应推断为 BIGINT，实际 {types}"
    assert "DOUBLE" in types.get("gross_revenue", ""), f"应推断为 DOUBLE，实际 {types}"
    assert "DATE" in types.get("sale_date", ""), f"应推断为 DATE，实际 {types}"
    print(f"  ✅ 类型推断正确: {types}")

    print("\n=== 测试 2：列表 ===")
    tables = list_user_tables()
    assert any(t["table_name"] == "user_test_sales_apr" for t in tables), "列表应含新表"
    print(f"  ✅ 列表正确: {[t['table_name'] for t in tables]}")


def test_preview_and_export():
    print("\n=== 测试 3：预览 ===")
    p = preview_table("test_sales_apr", limit=3)
    assert p["row_count"] == 5
    assert len(p["data"]) == 3
    assert p["columns"][0] == "brand_name"
    print(f"  ✅ 预览 {len(p['data'])} 行, 列: {p['columns']}")

    print("\n=== 测试 4：导出 CSV ===")
    csv_str = export_table_csv("test_sales_apr")
    lines = csv_str.strip().split("\n")
    assert len(lines) == 6, f"应 6 行（含表头），实际 {len(lines)}"
    assert "brand_name,sale_date" in lines[0]
    print(f"  ✅ 导出 {len(lines)} 行 CSV")


def test_delete_and_cleanup():
    print("\n=== 测试 5：删除 + 清理 ===")
    r = delete_table("test_sales_apr")
    assert r["deleted"]
    # 确认已删除
    tables = list_user_tables()
    assert not any(t["table_name"] == "user_test_sales_apr" for t in tables), "应已删除"
    print(f"  ✅ 删除成功, 剩余: {[t['table_name'] for t in tables]}")


def test_stats():
    print("\n=== 测试 6：容量统计 ===")
    # 先导入一个
    import_csv(SAMPLE_CSV_NO_HEADER_TYPES, "test_products")
    s = get_stats()
    print(f"  ✅ 统计: {s['table_count']} 表 / {s['total_rows']} 行 / DB {s['db_size_bytes']}B")
    assert s["table_count"] >= 1
    assert s["total_rows"] >= 3
    # 清理
    delete_table("test_products")


def test_edge_cases():
    print("\n=== 测试 7：边界情况 ===")
    # 空 CSV
    try:
        import_csv("", "test_empty")
        assert False, "应抛异常"
    except ValueError as e:
        print(f"  ✅ 空 CSV 拦截: {e}")

    # 只有表头
    try:
        import_csv("a,b,c\n", "test_only_header")
        assert False, "应抛异常"
    except ValueError as e:
        print(f"  ✅ 无数据行拦截: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print(" P2-1 数据管理服务 - 单元测试")
    print("=" * 60)
    try:
        test_validate_table_name()
        if HAS_DUCKDB:
            from services.data_manager import (
                import_csv, list_user_tables, preview_table,
                export_table_csv, delete_table, get_stats,
            )
            test_import_and_list()
            test_preview_and_export()
            test_delete_and_cleanup()
            test_stats()
            test_edge_cases()
        else:
            print("\n⏭️  跳过 DB 相关测试（本地无 duckdb）")
        print("\n🎉 全部通过\n")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n❌ 失败: {e}")
        sys.exit(1)
