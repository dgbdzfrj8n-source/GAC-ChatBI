"""
v2.0 数据生成脚本（纯Python实现，无外部依赖）
生成新增的两张表：
1. fact_dealer_traffic - 渠道客流事实表（约8000行）
2. fact_inventory - 经销商库存事实表（约5000行）
"""

import csv
import random
import os
from datetime import date, timedelta
from collections import OrderedDict

# 设置随机种子，保证可复现
random.seed(42)

# 维度定义
BRANDS = ["广汽埃安", "广汽传祺", "昊铂"]
REGIONS = ["华东区", "华南区", "华北区", "西南区", "华中区"]
CHANNELS = ["自然到店", "抖音线索", "汽车之家", "懂车帝", "老客转介绍"]

MODELS_BY_BRAND = {
    "广汽埃安": ["AION Y", "AION S", "AION V", "AION LX"],
    "广汽传祺": ["传祺GS8", "传祺M8", "传祺影豹", "传祺GS4"],
    "昊铂": ["昊铂GT", "昊铂HT", "昊铂SSR"]
}

DEALERS = {
    "华东区": ["D-SH-001", "D-SH-002", "D-SH-003", "D-NJ-001", "D-HZ-001"],
    "华南区": ["D-GZ-001", "D-GZ-002", "D-SZ-001", "D-FZ-001", "D-GZ-003"],
    "华北区": ["D-BJ-001", "D-BJ-002", "D-TJ-001", "D-JN-001"],
    "西南区": ["D-CD-001", "D-CD-002", "D-CQ-001", "D-YN-001"],
    "华中区": ["D-WH-001", "D-WH-002", "D-CS-001", "D-ZZ-001"]
}

DEALER_NAMES = {
    "D-SH-001": "上海浦东埃安体验中心", "D-SH-002": "上海静安广汽新能源店", "D-SH-003": "上海嘉定传祺专营店",
    "D-NJ-001": "南京鼓楼埃安体验中心", "D-HZ-001": "杭州西湖昊铂旗舰店",
    "D-GZ-001": "广州天河埃安中心", "D-GZ-002": "广州白云传祺4S店", "D-SZ-001": "深圳南山埃安体验店",
    "D-FZ-001": "福州仓山广汽店", "D-GZ-003": "广州番禺埃安新城",
    "D-BJ-001": "北京朝阳埃安体验中心", "D-BJ-002": "北京海淀传祺店", "D-TJ-001": "天津河西昊铂店",
    "D-JN-001": "济南历下广汽店",
    "D-CD-001": "成都锦江埃安体验店", "D-CD-002": "成都武侯传祺专营", "D-CQ-001": "重庆渝北埃安中心",
    "D-YN-001": "昆明五华广汽店",
    "D-WH-001": "武汉武昌埃安体验中心", "D-WH-002": "武汉汉口传祺店", "D-CS-001": "长沙岳麓昊铂店",
    "D-ZZ-001": "郑州金水广汽店"
}


def daterange(start_date, end_date):
    """日期迭代器"""
    for n in range(int((end_date - start_date).days) + 1):
        yield start_date + timedelta(n)


def generate_dealer_traffic():
    """生成渠道客流事实表"""
    print("生成 fact_dealer_traffic 表...")
    
    records = []
    
    start_date = date(2024, 4, 1)
    end_date = date(2025, 4, 30)
    
    for traffic_date in daterange(start_date, end_date):
        for brand in BRANDS:
            for region in REGIONS:
                region_dealers = DEALERS.get(region, [])
                
                for dealer_id in region_dealers:
                    dealer_name = DEALER_NAMES.get(dealer_id, dealer_id)
                    
                    # 客流基础值
                    if brand == "广汽埃安":
                        base_visits = random.randint(30, 80)
                    elif brand == "广汽传祺":
                        base_visits = random.randint(20, 60)
                    else:
                        base_visits = random.randint(10, 35)
                    
                    # 季节性调整
                    month = traffic_date.month
                    if month in [9, 10, 11, 12, 1]:
                        base_visits = int(base_visits * 1.3)
                    elif month in [2, 3, 7, 8]:
                        base_visits = int(base_visits * 1.1)
                    elif month in [6]:
                        base_visits = int(base_visits * 1.2)
                    
                    store_visits = base_visits + random.randint(-10, 15)
                    store_visits = max(5, store_visits)
                    
                    # 留资率（50-70%）
                    leads_rate = random.uniform(0.50, 0.70)
                    leads_count = int(store_visits * leads_rate)
                    
                    # 试驾率（30-50%）
                    test_drive_rate = random.uniform(0.30, 0.50)
                    test_drives = int(leads_count * test_drive_rate)
                    
                    # 成交率（15-30%）
                    deal_rate = random.uniform(0.15, 0.30)
                    deals_closed = int(leads_count * deal_rate)
                    
                    # 漏斗约束
                    if deals_closed > test_drives:
                        deals_closed = test_drives
                    if test_drives > leads_count:
                        test_drives = leads_count
                    if leads_count > store_visits:
                        leads_count = store_visits
                    
                    # 客流来源（加权随机）
                    channel_weights = [0.35, 0.25, 0.20, 0.12, 0.08]
                    channel_source = random.choices(CHANNELS, weights=channel_weights, k=1)[0]
                    
                    # 停留时长
                    if brand == "昊铂":
                        avg_dwell = random.uniform(25, 45)
                    elif brand == "广汽传祺":
                        avg_dwell = random.uniform(18, 30)
                    else:
                        avg_dwell = random.uniform(15, 25)
                    
                    records.append([
                        traffic_date.strftime("%Y-%m-%d"),
                        brand,
                        region,
                        dealer_id,
                        dealer_name,
                        channel_source,
                        store_visits,
                        leads_count,
                        test_drives,
                        deals_closed,
                        round(avg_dwell, 1)
                    ])
    
    return records


def generate_inventory():
    """生成经销商库存事实表"""
    print("生成 fact_inventory 表...")
    
    records = []
    
    # 生成月份列表
    months = []
    current = date(2024, 4, 1)
    end = date(2025, 4, 1)
    while current <= end:
        months.append(current.strftime("%Y-%m"))
        # 下一月
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)
    
    for snapshot_month in months:
        for brand in BRANDS:
            models = MODELS_BY_BRAND.get(brand, [])
            
            for model in models:
                for region in REGIONS:
                    # 基础库存
                    if "AION Y" in model or "影豹" in model or "GT" in model:
                        base_stock = random.randint(80, 180)
                    elif "AION S" in model or "GS4" in model or "HT" in model:
                        base_stock = random.randint(50, 120)
                    elif "AION V" in model or "GS8" in model or "M8" in model:
                        base_stock = random.randint(30, 80)
                    else:
                        base_stock = random.randint(10, 40)
                    
                    # 区域差异
                    if region in ["华东区", "华南区"]:
                        base_stock = int(base_stock * 1.2)
                    elif region in ["华北区", "华中区"]:
                        base_stock = int(base_stock * 0.9)
                    
                    # 季节性
                    month_num = int(snapshot_month.split("-")[1])
                    if month_num in [9, 10, 11]:
                        base_stock = int(base_stock * 1.5)
                    elif month_num in [12, 1]:
                        base_stock = int(base_stock * 1.3)
                    elif month_num in [3, 4]:
                        base_stock = int(base_stock * 0.7)
                    
                    stock_units = base_stock + random.randint(-15, 25)
                    stock_units = max(5, stock_units)
                    
                    # 在途
                    in_transit_rate = random.uniform(0.10, 0.30)
                    in_transit_units = int(stock_units * in_transit_rate)
                    
                    # 周转天数
                    if "AION Y" in model or "GS8" in model:
                        avg_stock_days = random.uniform(25, 45)
                    elif "AION S" in model or "影豹" in model:
                        avg_stock_days = random.uniform(30, 55)
                    else:
                        avg_stock_days = random.uniform(40, 80)
                    
                    # 库存系数
                    stock_coefficient = random.uniform(0.8, 2.2)
                    
                    # 库龄超90天
                    if stock_coefficient > 1.8:
                        aging_over_90d_units = int(stock_units * random.uniform(0.10, 0.25))
                    elif stock_coefficient > 1.5:
                        aging_over_90d_units = int(stock_units * random.uniform(0.03, 0.10))
                    else:
                        aging_over_90d_units = int(stock_units * random.uniform(0, 0.03))
                    
                    # 缺货标记（10%概率缺货）
                    shortage_flag = "true" if random.random() < 0.10 or stock_coefficient < 0.8 else "false"
                    
                    records.append([
                        snapshot_month,
                        brand,
                        model,
                        region,
                        stock_units,
                        in_transit_units,
                        round(avg_stock_days, 1),
                        round(stock_coefficient, 2),
                        aging_over_90d_units,
                        shortage_flag
                    ])
    
    return records


def write_csv(filepath, headers, records):
    """写入CSV文件"""
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(records)


def main():
    """主函数"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = current_dir
    
    print("\n" + "=" * 50)
    print("开始生成 v2.0 数据...")
    print("=" * 50 + "\n")
    
    # 1. 渠道客流表
    traffic_headers = [
        "traffic_date", "brand_name", "region_name", "dealer_id", "dealer_name",
        "channel_source", "store_visits", "leads_count", "test_drives", 
        "deals_closed", "avg_dwell_minutes"
    ]
    traffic_records = generate_dealer_traffic()
    traffic_path = os.path.join(output_dir, "fact_dealer_traffic.csv")
    write_csv(traffic_path, traffic_headers, traffic_records)
    print(f"  已保存到: {traffic_path}")
    print(f"  记录数: {len(traffic_records)}")
    
    # 2. 库存表
    inventory_headers = [
        "snapshot_month", "brand_name", "model_name", "region_name",
        "stock_units", "in_transit_units", "avg_stock_days", 
        "stock_coefficient", "aging_over_90d_units", "shortage_flag"
    ]
    inventory_records = generate_inventory()
    inventory_path = os.path.join(output_dir, "fact_inventory.csv")
    write_csv(inventory_path, inventory_headers, inventory_records)
    print(f"  已保存到: {inventory_path}")
    print(f"  记录数: {len(inventory_records)}")
    
    # 统计信息
    print("\n" + "=" * 50)
    print("生成完成！")
    print("=" * 50)
    
    # 客流表统计
    print(f"\nfact_dealer_traffic:")
    brand_counts = {}
    for r in traffic_records:
        brand = r[1]
        brand_counts[brand] = brand_counts.get(brand, 0) + 1
    for brand, count in brand_counts.items():
        print(f"  {brand}: {count} 条")
    
    # 库存表统计
    print(f"\nfact_inventory:")
    shortage_count = sum(1 for r in inventory_records if r[9] == "true")
    high_stock_count = sum(1 for r in inventory_records if float(r[7]) > 2.0)
    print(f"  总记录: {len(inventory_records)}")
    print(f"  缺货预警: {shortage_count} 条")
    print(f"  高库存(>2.0): {high_stock_count} 条")


if __name__ == "__main__":
    main()
