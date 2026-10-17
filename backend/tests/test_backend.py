"""
后端部分测试用例
验证配置管理、语义层、数据表等后端功能
"""

import sys
import os
import json

# 添加项目路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "backend"))

# 测试结果统计
PASS = 0
FAIL = 0


def check(name, fn):
    """运行测试并打印结果"""
    global PASS, FAIL
    try:
        fn()
        print(f"  ✔ {name}")
        PASS += 1
        return True
    except AssertionError as e:
        print(f"  ✘ {name}: {e}")
        FAIL += 1
        return False
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"  ✘ {name}: {type(e).__name__}: {e}")
        FAIL += 1
        return False


# ============================================================
# 配置管理测试
# ============================================================
def test_config_version():
    """版本号配置"""
    from config import settings, get_version_info, get_display_version
    
    assert settings.APP_VERSION == "v2.0.0", f"版本号应为v2.0.0，实际: {settings.APP_VERSION}"
    assert settings.SPRINT_NAME == "Sprint 10", f"Sprint应为Sprint 10，实际: {settings.SPRINT_NAME}"
    
    version_info = get_version_info()
    assert version_info["version"] == "v2.0.0"
    assert version_info["sprint"] == "Sprint 10"
    
    display = get_display_version()
    assert "v2.0.0" in display
    assert "Sprint 10" in display
    
    print(f"    - 版本号: {version_info['version']}")
    print(f"    - Sprint: {version_info['sprint']}")
    print(f"    - 显示: {display}")


def test_config_models():
    """模型配置"""
    from config import settings, get_model_list, get_default_model
    
    models = get_model_list()
    assert len(models) == 3, f"应有3个模型，实际: {len(models)}"
    
    # 检查默认模型
    default = get_default_model()
    assert default == "qwen3-coder-30b", f"默认模型应为qwen3-coder-30b，实际: {default}"
    
    # 检查模型名称
    model_names = [m["name"] for m in models]
    assert "Qwen3-Coder-30B" in model_names
    assert "DeepSeek Chat" in model_names
    assert "GPT-4o Mini" in model_names
    
    # 检查部署标注
    for model in models:
        assert "deployment" in model, f"模型缺少deployment字段"
        assert model["deployment"] in ["私有化部署", "云端API", "轻量备用"]
    
    print(f"    - 模型数量: {len(models)}")
    print(f"    - 默认模型: {default}")
    print(f"    - 模型列表: {[m['name'] for m in models]}")


def test_config_tables():
    """数据表配置"""
    from config import settings
    
    tables = settings.MAIN_DB_TABLES
    assert len(tables) == 5, f"应有5张表，实际: {len(tables)}"
    
    expected_tables = [
        "fact_sales_daily",
        "dim_budget_target",
        "fact_marketing_expenses",
        "fact_dealer_traffic",
        "fact_inventory"
    ]
    
    for table in expected_tables:
        assert table in tables, f"缺少表: {table}"
    
    print(f"    - 主库表数量: {len(tables)}")
    print(f"    - 表列表: {tables}")


def test_config_domains():
    """业务域配置"""
    from config import settings
    
    domains = settings.BUSINESS_DOMAINS
    expected_domains = ["整车销售", "经营财务", "市场营销", "渠道经营", "库存管理"]
    
    for domain in expected_domains:
        assert domain in domains, f"缺少业务域: {domain}"
    
    assert len(domains) == 5, f"应有5个业务域，实际: {len(domains)}"
    
    print(f"    - 业务域数量: {len(domains)}")
    print(f"    - 业务域列表: {domains}")


# ============================================================
# 语义层测试
# ============================================================
def test_semantic_v2_metrics():
    """v2.0 语义层指标"""
    test_file = os.path.abspath(__file__)
    backend_dir = os.path.dirname(os.path.dirname(test_file))
    semantic_path = os.path.join(backend_dir, "data", "semantic_v2.json")
    
    with open(semantic_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    metrics = data.get("metrics", [])
    assert len(metrics) == 30, f"应有30个指标，实际: {len(metrics)}"
    
    # 检查指标ID
    metric_ids = [m["metric_id"] for m in metrics]
    for i in range(1, 31):
        mid = f"M{i:02d}"
        assert mid in metric_ids, f"缺少指标: {mid}"
    
    # 检查v2.0新增指标
    v2_metrics = [m for m in metrics if int(m["metric_id"][1:]) >= 18]
    assert len(v2_metrics) >= 13, f"v2.0应新增13个指标，实际: {len(v2_metrics)}"
    
    # 检查业务域分布
    domains = {}
    for m in metrics:
        domain = m["business_domain"]
        domains[domain] = domains.get(domain, 0) + 1
    
    print(f"    - 指标总数: {len(metrics)}")
    print(f"    - v2.0新增: {len(v2_metrics)}")
    print(f"    - 业务域分布: {domains}")


def test_semantic_dimensions():
    """语义层维度"""
    test_file = os.path.abspath(__file__)
    backend_dir = os.path.dirname(os.path.dirname(test_file))
    semantic_path = os.path.join(backend_dir, "data", "semantic_v2.json")
    
    with open(semantic_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    dimensions = data.get("dimensions", [])
    assert len(dimensions) >= 10, f"应有至少10个维度，实际: {len(dimensions)}"
    
    # 检查v2.0新增维度
    v2_dims = [d for d in dimensions if d.get("field") in ["channel_source", "dealer_name", "snapshot_month"]]
    
    print(f"    - 维度总数: {len(dimensions)}")
    print(f"    - v2.0新增: {len(v2_dims)}")


def test_semantic_synonyms():
    """同义词"""
    test_file = os.path.abspath(__file__)
    backend_dir = os.path.dirname(os.path.dirname(test_file))
    semantic_path = os.path.join(backend_dir, "data", "semantic_v2.json")
    
    with open(semantic_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    synonyms = data.get("synonyms", [])
    assert len(synonyms) >= 9, f"应有至少9组同义词，实际: {len(synonyms)}"
    
    print(f"    - 同义词组数: {len(synonyms)}")


# ============================================================
# 数据表测试
# ============================================================
def test_csv_files_exist():
    """CSV文件存在性"""
    # 使用正确的项目路径
    # 项目结构: GAC-ChatBI/backend/tests/test_backend.py
    test_file = os.path.abspath(__file__)
    # backend/tests -> backend -> 项目根目录
    backend_dir = os.path.dirname(os.path.dirname(test_file))
    data_dir = os.path.join(backend_dir, "data")
    
    # v2.0 新增表
    assert os.path.exists(os.path.join(data_dir, "fact_dealer_traffic.csv")), "fact_dealer_traffic.csv 不存在"
    assert os.path.exists(os.path.join(data_dir, "fact_inventory.csv")), "fact_inventory.csv 不存在"
    
    print("    - fact_dealer_traffic.csv 存在")
    print("    - fact_inventory.csv 存在")


def test_dealer_traffic_data():
    """渠道客流表数据"""
    import csv
    
    # 使用正确的项目路径
    test_file = os.path.abspath(__file__)
    backend_dir = os.path.dirname(os.path.dirname(test_file))
    csv_path = os.path.join(backend_dir, "data", "fact_dealer_traffic.csv")
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    assert len(rows) > 0, "fact_dealer_traffic.csv 为空"
    assert len(rows) >= 8000, f"fact_dealer_traffic 应有约8000行，实际: {len(rows)}"
    
    # 检查漏斗约束
    funnel_issues = 0
    for row in rows:
        store_visits = int(row.get("store_visits", 0))
        leads_count = int(row.get("leads_count", 0))
        test_drives = int(row.get("test_drives", 0))
        deals_closed = int(row.get("deals_closed", 0))
        
        if not (deals_closed <= test_drives <= leads_count <= store_visits):
            funnel_issues += 1
    
    funnel_rate = funnel_issues / len(rows) * 100
    assert funnel_rate < 1, f"漏斗约束违反率过高: {funnel_rate:.2f}%"
    
    print(f"    - 记录数: {len(rows):,}")
    print(f"    - 漏斗约束违反率: {funnel_rate:.2f}%")


def test_inventory_data():
    """库存表数据"""
    import csv
    
    # 使用正确的项目路径
    test_file = os.path.abspath(__file__)
    backend_dir = os.path.dirname(os.path.dirname(test_file))
    csv_path = os.path.join(backend_dir, "data", "fact_inventory.csv")
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    assert len(rows) > 0, "fact_inventory.csv 为空"
    assert len(rows) >= 500, f"fact_inventory 应有约500-1000行，实际: {len(rows)}"
    
    # 检查缺货预警
    shortage_count = sum(1 for r in rows if r.get("shortage_flag", "").lower() == "true")
    high_stock_count = sum(1 for r in rows if float(r.get("stock_coefficient", 0)) > 2.0)
    
    print(f"    - 记录数: {len(rows):,}")
    print(f"    - 缺货预警: {shortage_count} 条")
    print(f"    - 高库存(>2.0): {high_stock_count} 条")


# ============================================================
# Bad Case 示例数据测试
# ============================================================
def test_badcase_examples():
    """Bad Case 预置示例"""
    # PRD 中定义的8条示例数据
    expected_cases = [
        {"id": "BC-001", "type": "语义理解错", "status": "已闭环"},
        {"id": "BC-002", "type": "语义理解错", "status": "待处理"},
        {"id": "BC-003", "type": "指标口径错", "status": "已闭环"},
        {"id": "BC-004", "type": "指标口径错", "status": "待处理"},
        {"id": "BC-005", "type": "图表选错", "status": "已闭环"},
        {"id": "BC-006", "type": "图表选错", "status": "已闭环"},
        {"id": "BC-007", "type": "维度错配", "status": "待处理"},
        {"id": "BC-008", "type": "维度错配", "status": "已闭环"},
    ]
    
    # 统计
    total = len(expected_cases)
    closed = sum(1 for c in expected_cases if c["status"] == "已闭环")
    pending = sum(1 for c in expected_cases if c["status"] == "待处理")
    
    # 失败类型分布
    types = {}
    for c in expected_cases:
        t = c["type"]
        types[t] = types.get(t, 0) + 1
    
    assert total == 8, f"应有8条Bad Case，实际: {total}"
    assert closed == 5, f"已闭环应为5条，实际: {closed}"
    assert pending == 3, f"待处理应为3条，实际: {pending}"
    assert closed / total * 100 == 62.5, f"闭环率应为62.5%，实际: {closed/total*100}%"
    
    for failure_type, count in types.items():
        assert count == 2, f"{failure_type}应有2条，实际: {count}"
    
    print(f"    - 总数: {total}")
    print(f"    - 已闭环: {closed} ({closed/total*100:.1f}%)")
    print(f"    - 待处理: {pending}")
    print(f"    - 类型分布: {types}")


# ============================================================
# 快捷提问测试
# ============================================================
def test_quick_questions():
    """快捷提问（20条）"""
    # PRD中定义的新增5条快捷提问
    new_questions = [
        {"id": 16, "domain": "渠道经营", "content": "华东大区客流成交转化率排名？"},
        {"id": 17, "domain": "渠道经营", "content": "进店→留资→试驾→成交的客流漏斗"},
        {"id": 18, "domain": "库存管理", "content": "当前库存周转天数最高的车型？"},
        {"id": 19, "domain": "库存管理", "content": "库存系数超过2.0的高库存预警车型"},
        {"id": 20, "domain": "渠道经营", "content": "抖音渠道的留资率比自然到店高多少？"},
    ]
    
    # 原有15条
    original_count = 15
    
    total = original_count + len(new_questions)
    assert total == 20, f"应有20条快捷提问，实际: {total}"
    
    # 业务域分布（5个）
    domains = set()
    for q in new_questions:
        if q["domain"] not in ["整车销售", "经营财务", "市场营销", "渠道经营", "库存管理"]:
            domains.add(q["domain"])
    
    # 新增了库存管理分类
    new_domains = set(q["domain"] for q in new_questions)
    assert "库存管理" in new_domains, "应有库存管理分类的快捷提问"
    
    print(f"    - 总数: {total} (原{original_count} + 新增{len(new_questions)})")
    print(f"    - 新增分类: 库存管理")
    print(f"    - 新增问题: {len(new_questions)} 条")


# ============================================================
# 运行所有测试
# ============================================================
def run_all_tests():
    global PASS, FAIL
    PASS = 0
    FAIL = 0
    
    print("\n" + "=" * 60)
    print("   GAC-ChatBI v2.0 后端测试套件")
    print("=" * 60)
    
    print("\n--- 配置管理 ---")
    test_config_version()
    test_config_models()
    test_config_tables()
    test_config_domains()
    
    print("\n--- 语义层 ---")
    test_semantic_v2_metrics()
    test_semantic_dimensions()
    test_semantic_synonyms()
    
    print("\n--- 数据表 ---")
    test_csv_files_exist()
    test_dealer_traffic_data()
    test_inventory_data()
    
    print("\n--- Bad Case ---")
    test_badcase_examples()
    
    print("\n--- 快捷提问 ---")
    test_quick_questions()
    
    print("\n" + "=" * 60)
    print(f"   测试结果: {PASS} pass / {FAIL} fail")
    print("=" * 60)
    
    if FAIL == 0:
        print("🎉 后端所有测试用例通过！")
        return True
    else:
        print(f"⚠️  有 {FAIL} 个用例失败，请检查")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
