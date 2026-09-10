"""
广汽集团经营分析数仓高仿真数据生成脚本 (双引擎架构：优先 DuckDB，自适应标准 SQLite3)
基于真实汽车主机厂季节性与经营特征：
1. 2月春节淡季（交付量与客流普遍下滑 30%~45%）
2. 3月节后开门红与春季车展反弹
3. 9-10月金九银十与四季度冲刺翘尾
4. 埃安、传祺、昊铂品牌不同的价格区间、毛利、折扣率与渠道偏好
"""

import os
import random
import datetime
import sqlite3

# 尝试载入 DuckDB，若无则平滑回退至 Python 内置 sqlite3，确保零环境依赖 100% 成功生成
try:
    import duckdb
    HAS_DUCKDB = True
except ImportError:
    HAS_DUCKDB = False

random.seed(42)

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DUCKDB_PATH = os.path.join(CURRENT_DIR, "gac_bi.duckdb")
SQLITE_PATH = os.path.join(CURRENT_DIR, "gac_bi.db")
SCHEMA_PATH = os.path.join(CURRENT_DIR, "schema.sql")

# 广汽品牌及车型矩阵（车型、均价指导价范围）
BRAND_MODELS = {
    "广汽埃安": [
        ("AION Y", 119800, 145800, 0.06),
        ("AION S", 139800, 169800, 0.08),
        ("AION V", 159800, 199800, 0.07),
    ],
    "广汽传祺": [
        ("传祺GS8", 186800, 269800, 0.10),
        ("传祺M8", 179800, 329800, 0.05),
        ("传祺影豹", 98300, 138000, 0.12),
    ],
    "昊铂": [
        ("昊铂GT", 219900, 259900, 0.09),
        ("昊铂HT", 213900, 286900, 0.08),
    ],
}

REGIONS = [
    ("华南区", ["广东省", "广西壮族自治区", "海南省"], 1.35),
    ("华东区", ["江苏省", "浙江省", "上海市", "山东省"], 1.20),
    ("华北区", ["北京市", "河北省", "天津市"], 0.85),
    ("华中区", ["湖北省", "湖南省", "河南省"], 0.95),
    ("西南区", ["四川省", "重庆市", "云南省"], 0.90),
]

CHANNELS = [
    ("懂车帝垂直类", "线上公域投放", 0.35, 120),
    ("抖音信息流", "线上公域投放", 0.30, 95),
    ("商圈巡展外拓", "线下巡展体验", 0.20, 260),
    ("区域广播与电梯屏", "终端促销补贴", 0.15, 180),
]

def get_season_factor(date_obj: datetime.date) -> float:
    m = date_obj.month
    if m == 2:  # 春节淡季
        return 0.62
    elif m in [3, 4]:  # 春季回暖
        return 1.10
    elif m in [9, 10]:  # 金九银十
        return 1.25
    elif m == 12:  # 年末冲刺
        return 1.38
    elif m in [7, 8]:  # 夏季淡季
        return 0.92
    return 1.0

def build_database():
    engine_name = "DuckDB" if HAS_DUCKDB else "SQLite3 (Python内置标准库，零依赖)"
    db_file = DUCKDB_PATH if HAS_DUCKDB else SQLITE_PATH

    if os.path.exists(db_file):
        os.remove(db_file)

    if HAS_DUCKDB:
        con = duckdb.connect(db_file)
    else:
        con = sqlite3.connect(db_file)

    cursor = con.cursor()
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()
        if HAS_DUCKDB:
            con.execute(schema_sql)
        else:
            cursor.executescript(schema_sql)

    print(f">>> [引擎: {engine_name}] 正在生成广汽经营数仓数据 (2024.01 - 2025.04)...")

    start_date = datetime.date(2024, 1, 1)
    end_date = datetime.date(2025, 4, 30)
    delta_days = (end_date - start_date).days + 1

    sales_rows = []
    daily_brand_units = {}

    for d in range(delta_days):
        current_date = start_date + datetime.timedelta(days=d)
        date_str = current_date.strftime("%Y-%m-%d")
        ym = current_date.strftime("%Y-%m")
        season = get_season_factor(current_date)
        is_weekend = current_date.weekday() >= 5
        day_factor = 1.3 if is_weekend else 1.0

        for brand, models in BRAND_MODELS.items():
            for model_name, min_p, max_p, base_discount in models:
                for region_name, provinces, reg_weight in REGIONS:
                    prov = random.choice(provinces)
                    
                    if brand == "广汽埃安":
                        base_units = random.randint(4, 12)
                    elif brand == "广汽传祺":
                        base_units = random.randint(3, 9)
                    else:
                        base_units = random.randint(1, 4)

                    actual_units = int(base_units * season * reg_weight * day_factor)
                    if actual_units < 0:
                        actual_units = 0

                    leads = int(actual_units * random.uniform(8.0, 16.0) + random.randint(5, 20))
                    test_drives = int(actual_units * random.uniform(2.5, 4.5))
                    
                    unit_price = random.uniform(min_p, max_p)
                    discount = round(base_discount + random.uniform(-0.02, 0.03), 3)
                    discount = max(0.01, min(discount, 0.20))
                    
                    revenue = round(actual_units * unit_price * (1 - discount), 2)

                    sales_rows.append((
                        date_str, brand, model_name, region_name, prov,
                        actual_units, revenue, discount, leads, test_drives
                    ))

                    daily_brand_units.setdefault((ym, brand), 0)
                    daily_brand_units[(ym, brand)] += actual_units

    cursor.executemany("""
        INSERT INTO fact_sales_daily VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, sales_rows)
    print(f"✔ fact_sales_daily 写入完成，共 {len(sales_rows):,} 条记录。")

    # 2. 生成 dim_budget_target 数据
    budget_rows = []
    for (ym, brand), total_delivered in daily_brand_units.items():
        rate = random.uniform(0.80, 1.06)
        if ym in ["2024-02", "2025-02"]:
            rate = random.uniform(0.72, 0.88)
        elif ym in ["2024-12"]:
            rate = random.uniform(1.02, 1.12)

        target_units = int(total_delivered / rate)
        target_rev = round(target_units * (140000 if brand == "广汽埃安" else (180000 if brand == "广汽传祺" else 240000)), 2)
        expense_limit = round(target_rev * random.uniform(0.045, 0.065), 2)

        budget_rows.append((ym, brand, target_units, target_rev, expense_limit))

    cursor.executemany("""
        INSERT INTO dim_budget_target VALUES (?, ?, ?, ?, ?)
    """, budget_rows)
    print(f"✔ dim_budget_target 写入完成，共 {len(budget_rows):,} 个月度预算目标。")

    # 3. 生成 fact_marketing_expenses 数据
    marketing_rows = []
    for d in range(delta_days):
        current_date = start_date + datetime.timedelta(days=d)
        date_str = current_date.strftime("%Y-%m-%d")
        season = get_season_factor(current_date)

        for brand in BRAND_MODELS.keys():
            for channel_name, category, spend_share, base_cpl in CHANNELS:
                if brand == "广汽埃安":
                    base_daily = 35000
                elif brand == "广汽传祺":
                    base_daily = 28000
                else:
                    base_daily = 16000

                spend = round(base_daily * spend_share * season * random.uniform(0.85, 1.25), 2)
                cpl = base_cpl * random.uniform(0.85, 1.15)
                leads = int(spend / cpl)

                marketing_rows.append((
                    date_str, brand, channel_name, category, spend, leads
                ))

    cursor.executemany("""
        INSERT INTO fact_marketing_expenses VALUES (?, ?, ?, ?, ?, ?)
    """, marketing_rows)
    print(f"✔ fact_marketing_expenses 写入完成，共 {len(marketing_rows):,} 条投放流水。")

    con.commit()
    con.close()
    print(f"🎉 广汽数仓生成成功，数据库保存在: {db_file}")

if __name__ == "__main__":
    build_database()
