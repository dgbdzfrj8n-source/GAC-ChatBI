#!/usr/bin/env python3
"""
GAC-ChatBI v2.0 数据库初始化脚本
将CSV数据导入DuckDB数据库
"""

import os
import sys

# 尝试多种方式导入duckdb
try:
    import duckdb
except ImportError:
    print("❌ 未安装duckdb，正在安装...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "duckdb", "-q"])
    import duckdb

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
DUCKDB_PATH = os.path.join(DATA_DIR, "gac_bi.duckdb")

print("=" * 60)
print("   GAC-ChatBI v2.0 数据库初始化")
print("=" * 60)
print()

def get_connection(read_only=False):
    return duckdb.connect(DUCKDB_PATH, read_only=read_only)

def create_tables():
    """创建v2.0新增的表结构"""
    print("📋 创建表结构...")
    
    con = get_connection()
    
    # 渠道客流事实表【v2.0新增】
    con.execute("""
        CREATE TABLE IF NOT EXISTS fact_dealer_traffic (
            traffic_date DATE,
            brand_name VARCHAR,
            region_name VARCHAR,
            dealer_id VARCHAR,
            dealer_name VARCHAR,
            channel_source VARCHAR,
            store_visits INTEGER,
            leads_count INTEGER,
            test_drives INTEGER,
            deals_closed INTEGER,
            avg_dwell_minutes DOUBLE
        )
    """)
    
    # 经销商库存事实表【v2.0新增】
    con.execute("""
        CREATE TABLE IF NOT EXISTS fact_inventory (
            snapshot_month VARCHAR,
            brand_name VARCHAR,
            model_name VARCHAR,
            region_name VARCHAR,
            stock_units INTEGER,
            in_transit_units INTEGER,
            avg_stock_days DOUBLE,
            stock_coefficient DOUBLE,
            aging_over_90d_units INTEGER,
            shortage_flag BOOLEAN
        )
    """)
    
    con.close()
    print("  ✅ 表结构创建完成")

def import_csv_data():
    """导入CSV数据"""
    print("\n📥 导入CSV数据...")
    
    con = get_connection()
    
    # 导入渠道客流数据
    csv_traffic = os.path.join(DATA_DIR, "fact_dealer_traffic.csv")
    if os.path.exists(csv_traffic):
        print(f"  📤 导入 {csv_traffic}...")
        con.execute(f"""
            COPY fact_dealer_traffic FROM '{csv_traffic}' 
            (FORMAT CSV, HEADER TRUE, DELIMITER ',')
        """)
        count = con.execute("SELECT COUNT(*) FROM fact_dealer_traffic").fetchone()[0]
        print(f"  ✅ fact_dealer_traffic: {count:,} 条记录")
    else:
        print(f"  ⚠️  文件不存在: {csv_traffic}")
    
    # 导入库存数据
    csv_inventory = os.path.join(DATA_DIR, "fact_inventory.csv")
    if os.path.exists(csv_inventory):
        print(f"  📤 导入 {csv_inventory}...")
        con.execute(f"""
            COPY fact_inventory FROM '{csv_inventory}' 
            (FORMAT CSV, HEADER TRUE, DELIMITER ',')
        """)
        count = con.execute("SELECT COUNT(*) FROM fact_inventory").fetchone()[0]
        print(f"  ✅ fact_inventory: {count:,} 条记录")
    else:
        print(f"  ⚠️  文件不存在: {csv_inventory}")
    
    con.close()

def verify_data():
    """验证数据"""
    print("\n🔍 验证数据...")
    
    con = get_connection(read_only=True)
    
    # 获取所有表
    tables = con.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'main'
        ORDER BY table_name
    """).fetchall()
    
    print("\n  数据库中的表：")
    for (table_name,) in tables:
        try:
            count = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            print(f"    - {table_name}: {count:,} 条")
        except Exception as e:
            print(f"    - {table_name}: 读取失败 ({e})")
    
    con.close()
    
    # 验证v2.0新增表
    print("\n  v2.0 新增表验证：")
    for table in ['fact_dealer_traffic', 'fact_inventory']:
        try:
            count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            if count > 0:
                print(f"    ✅ {table}: {count:,} 条")
            else:
                print(f"    ⚠️  {table}: 空表")
        except Exception as e:
            print(f"    ❌ {table}: {e}")

def check_sample_data():
    """检查样本数据"""
    print("\n📊 样本数据检查...")
    
    con = get_connection(read_only=True)
    
    # 渠道客流样本
    print("\n  【fact_dealer_traffic 样本】")
    result = con.execute("""
        SELECT traffic_date, brand_name, region_name, channel_source, 
               store_visits, leads_count, deals_closed
        FROM fact_dealer_traffic 
        LIMIT 3
    """).fetchall()
    for row in result:
        print(f"    {row}")
    
    # 库存样本
    print("\n  【fact_inventory 样本】")
    result = con.execute("""
        SELECT snapshot_month, brand_name, model_name, stock_units, 
               stock_coefficient, shortage_flag
        FROM fact_inventory 
        LIMIT 3
    """).fetchall()
    for row in result:
        print(f"    {row}")
    
    # 统计预警
    print("\n  【库存预警统计】")
    shortage = con.execute("SELECT COUNT(*) FROM fact_inventory WHERE shortage_flag = TRUE").fetchone()[0]
    high_stock = con.execute("SELECT COUNT(*) FROM fact_inventory WHERE stock_coefficient > 2.0").fetchone()[0]
    print(f"    缺货预警: {shortage} 条")
    print(f"    高库存(>2.0): {high_stock} 条")
    
    con.close()

def main():
    if not os.path.exists(DUCKDB_PATH):
        print(f"❌ 数据库文件不存在: {DUCKDB_PATH}")
        print("   请先运行 generate_mock_data.py 生成基础数据库")
        sys.exit(1)
    
    print(f"📁 数据库路径: {DUCKDB_PATH}")
    print(f"📁 数据目录: {DATA_DIR}")
    print()
    
    # 步骤1: 创建表结构
    create_tables()
    
    # 步骤2: 导入CSV数据
    import_csv_data()
    
    # 步骤3: 验证数据
    verify_data()
    
    # 步骤4: 检查样本
    check_sample_data()
    
    print("\n" + "=" * 60)
    print("✅ 数据库初始化完成！")
    print("=" * 60)

if __name__ == "__main__":
    main()
