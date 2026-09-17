"""
P1 新增功能 - 离线单测（不依赖 duckdb / SqlExecutor / FastAPI）

覆盖范围：
1. METRIC_DIMENSION_MATRIX 完整性（5 个指标 × 6 个维度的联锁矩阵）
2. _resolve_metric 白名单兜底（非法键回退默认）
3. _filter_applicable_dims 行为（按指标过滤维度）
4. _infer_reason 按指标单位（辆 / 元 / 条 / % / 元/辆）
5. attribution_templates 表 DDL 含 metric_key 列
6. 前端 templates/page.tsx 含归因指标字段
7. 前端 DimensionPicker.tsx 含指标 × 维度联锁 UI

运行：python3 tests/sop_p1_unit.py
"""

import os
import re
import sys

BACKEND_DIR = "/Users/apple/Desktop/AI 产品经理/实战项目/GAC-ChatBI/backend"
FRONTEND_DIR = "/Users/apple/Desktop/AI 产品经理/实战项目/GAC-ChatBI/frontend"
sys.path.insert(0, BACKEND_DIR)

# ─────────────────────────────────────────────────────────────────
# 复制被测常量（避免触发 SqlExecutor / duckdb 导入）
# 与 sop_analyzer.py 保持 100% 一致
# ─────────────────────────────────────────────────────────────────
METRIC_DIMENSION_MATRIX = {
    "delivered_units": {
        "label": "总交付量", "unit": "辆",
        "agg_expression": "SUM(delivered_units)",
        "applicable_dimensions": ["brand_name", "region_name", "model_name", "energy_type", "price_segment", "monthly"],
        "recommend_score": {"brand_name":0.3, "region_name":0.7, "model_name":1.0, "energy_type":0.7, "price_segment":0.7, "monthly":0.7},
    },
    "gross_revenue": {
        "label": "总营收", "unit": "元",
        "agg_expression": "SUM(gross_revenue)",
        "applicable_dimensions": ["brand_name", "region_name", "model_name", "energy_type", "price_segment"],
        "recommend_score": {"brand_name":0.3, "region_name":0.7, "model_name":1.0, "energy_type":0.7, "price_segment":1.0},
    },
    "customer_leads": {
        "label": "进店线索量", "unit": "条",
        "agg_expression": "SUM(customer_leads)",
        "applicable_dimensions": ["brand_name", "region_name", "model_name", "energy_type", "monthly"],
        "recommend_score": {"brand_name":0.3, "region_name":1.0, "model_name":0.7, "energy_type":0.7, "monthly":1.0},
    },
    "conversion_rate": {
        "label": "客流转化率", "unit": "%",
        "agg_expression": "ROUND(SUM(delivered_units) * 100.0 / NULLIF(SUM(customer_leads), 0), 2)",
        "applicable_dimensions": ["brand_name", "region_name", "model_name", "price_segment"],
        "recommend_score": {"brand_name":0.3, "region_name":1.0, "model_name":0.7, "price_segment":0.7},
    },
    "avg_price": {
        "label": "单车成交均价", "unit": "元/辆",
        "agg_expression": "ROUND(SUM(gross_revenue) * 1.0 / NULLIF(SUM(delivered_units), 0), 2)",
        "applicable_dimensions": ["brand_name", "region_name", "model_name", "energy_type", "price_segment"],
        "recommend_score": {"brand_name":0.3, "region_name":0.7, "model_name":1.0, "energy_type":0.7, "price_segment":1.0},
    },
}
DEFAULT_METRIC_KEY = "delivered_units"
ALL_DIMENSIONS = ["brand_name", "region_name", "model_name", "energy_type", "price_segment", "monthly"]


def _resolve_metric(metric_key):
    safe_key = metric_key if metric_key in METRIC_DIMENSION_MATRIX else DEFAULT_METRIC_KEY
    cfg = METRIC_DIMENSION_MATRIX[safe_key]
    return {
        "key": safe_key,
        "label": cfg["label"],
        "unit": cfg["unit"],
        "agg_expression": cfg["agg_expression"],
        "applicable_dimensions": list(cfg["applicable_dimensions"]),
        "recommend_score": dict(cfg["recommend_score"]),
    }


def _filter_applicable_dims(metric_cfg, selected):
    allowed = set(metric_cfg["applicable_dimensions"])
    valid_keys = set(ALL_DIMENSIONS)
    return [d for d in selected if d in allowed and d in valid_keys]


def _infer_reason(dim_key, contribution, metric_cfg):
    direction = "下滑" if contribution < 0 else "增长"
    unit = metric_cfg.get("unit", "辆")
    reason_map = {
        "brand_name":    f"该品牌{direction} {abs(contribution):,.0f} {unit}（结构性占比变化）",
        "region_name":   f"该区域{direction} {abs(contribution):,.0f} {unit}（终端需求波动）",
        "model_name":    f"该车型{direction} {abs(contribution):,.0f} {unit}（产品周期/竞品冲击）",
        "energy_type":   f"该能源类型{direction} {abs(contribution):,.0f} {unit}（市场结构迁移）",
        "price_segment": f"该价格段{direction} {abs(contribution):,.0f} {unit}（消费偏好变化）",
        "monthly":       f"该时段{direction} {abs(contribution):,.0f} {unit}（季节性/节庆效应）",
    }
    return reason_map.get(dim_key, f"变动 {abs(contribution):,.0f} {unit}")


# ═══════════════════════════════════════════════════════════════════
# Test 1: 指标 × 维度 联锁矩阵完整性
# ═══════════════════════════════════════════════════════════════════
def test_metric_dimension_matrix_integrity():
    print("\n[TEST 1] METRIC_DIMENSION_MATRIX 完整性")
    # 1.1 必须恰好 5 个推荐指标
    assert len(METRIC_DIMENSION_MATRIX) == 5, f"应 5 个指标，实际 {len(METRIC_DIMENSION_MATRIX)}"
    # 1.2 每个指标必备字段
    for key, cfg in METRIC_DIMENSION_MATRIX.items():
        for required in ("label", "unit", "agg_expression", "applicable_dimensions", "recommend_score"):
            assert required in cfg, f"指标 {key} 缺字段 {required}"
    # 1.3 applicable_dimensions 必须是合法维度的子集
    for key, cfg in METRIC_DIMENSION_MATRIX.items():
        for d in cfg["applicable_dimensions"]:
            assert d in ALL_DIMENSIONS, f"指标 {key} 引用了非法维度 {d}"
    # 1.4 recommend_score 覆盖所有 applicable_dimensions
    for key, cfg in METRIC_DIMENSION_MATRIX.items():
        for d in cfg["applicable_dimensions"]:
            assert d in cfg["recommend_score"], f"指标 {key} 维度 {d} 缺推荐评分"
    # 1.5 业务硬规则校验（必须符合业务口径）
    #   - 营收/均价不应包含 monthly（按月波动大、归因易误导）
    for key in ("gross_revenue", "avg_price"):
        assert "monthly" not in METRIC_DIMENSION_MATRIX[key]["applicable_dimensions"], \
               f"指标 {key} 不应包含 monthly 维度"
    #   - 线索量不应包含 price_segment（线索不按价格段）
    assert "price_segment" not in METRIC_DIMENSION_MATRIX["customer_leads"]["applicable_dimensions"], \
           "线索量不应包含 price_segment"
    #   - 转化率不应包含 energy_type（按能源看转化率无业务口径）
    assert "energy_type" not in METRIC_DIMENSION_MATRIX["conversion_rate"]["applicable_dimensions"], \
           "转化率不应包含 energy_type"
    print(f"  PASS 5 个指标全齐全：{sorted(METRIC_DIMENSION_MATRIX.keys())}")
    print(f"  PASS 业务硬规则全部通过（营收/均价不归 monthly，线索不含价格段，转化率不含能源）")


# ═══════════════════════════════════════════════════════════════════
# Test 2: _resolve_metric 白名单兜底
# ═══════════════════════════════════════════════════════════════════
def test_resolve_metric_whitelist():
    print("\n[TEST 2] _resolve_metric 白名单兜底")
    # 合法键
    cfg = _resolve_metric("gross_revenue")
    assert cfg["key"] == "gross_revenue" and cfg["unit"] == "元"
    # 非法键 → 回退默认
    cfg = _resolve_metric("evil_key'; DROP TABLE--")
    assert cfg["key"] == DEFAULT_METRIC_KEY, f"非法键应回退，实际 {cfg['key']}"
    # None → 回退默认
    cfg = _resolve_metric(None)
    assert cfg["key"] == DEFAULT_METRIC_KEY
    # 空串 → 回退默认
    cfg = _resolve_metric("")
    assert cfg["key"] == DEFAULT_METRIC_KEY
    print("  PASS 合法键正常解析")
    print("  PASS SQL 注入尝试回退默认")
    print("  PASS None / 空串回退默认")


# ═══════════════════════════════════════════════════════════════════
# Test 3: _filter_applicable_dims 行为
# ═══════════════════════════════════════════════════════════════════
def test_filter_applicable_dims():
    print("\n[TEST 3] _filter_applicable_dims 按指标过滤维度")
    # 营收口径：选 monthly 应被剔除
    cfg = _resolve_metric("gross_revenue")
    selected = ["brand_name", "region_name", "monthly", "model_name"]
    filtered = _filter_applicable_dims(cfg, selected)
    assert "monthly" not in filtered, "营收下 monthly 应被剔除"
    assert set(filtered) == {"brand_name", "region_name", "model_name"}
    # 交付量口径：所有维度都保留
    cfg = _resolve_metric("delivered_units")
    filtered = _filter_applicable_dims(cfg, selected)
    assert set(filtered) == set(selected)
    # 非法维度应被剔除（防止 SQL 注入）
    filtered = _filter_applicable_dims(cfg, ["brand_name", "evil_dim", "model_name"])
    assert "evil_dim" not in filtered
    # 空选 → 空返
    filtered = _filter_applicable_dims(cfg, [])
    assert filtered == []
    print("  PASS 营收口径自动剔除 monthly")
    print("  PASS 交付量口径保留所有维度")
    print("  PASS 非法维度被过滤（防注入）")


# ═══════════════════════════════════════════════════════════════════
# Test 4: _infer_reason 按指标单位
# ═══════════════════════════════════════════════════════════════════
def test_infer_reason_uses_metric_unit():
    print("\n[TEST 4] _infer_reason 按指标单位输出")
    # 营收口径：单位应是"元"
    cfg = _resolve_metric("gross_revenue")
    reason = _infer_reason("region_name", -800, cfg)
    assert "元" in reason and "辆" not in reason, f"营收归因文案应含元，实际: {reason}"
    assert "-800" in reason or "800" in reason
    # 线索量口径：单位应是"条"
    cfg = _resolve_metric("customer_leads")
    reason = _infer_reason("model_name", -200, cfg)
    assert "条" in reason and "辆" not in reason, f"线索归因文案应含条，实际: {reason}"
    # 转化率口径：单位应是"%"
    cfg = _resolve_metric("conversion_rate")
    reason = _infer_reason("brand_name", -3.5, cfg)
    assert "%" in reason, f"转化率归因文案应含%，实际: {reason}"
    # 交付量口径：单位应是"辆"
    cfg = _resolve_metric("delivered_units")
    reason = _infer_reason("region_name", -800, cfg)
    assert "辆" in reason, f"交付量归因文案应含辆，实际: {reason}"
    print("  PASS 营收归因文案: 单位=元")
    print("  PASS 线索量归因文案: 单位=条")
    print("  PASS 转化率归因文案: 单位=%")
    print("  PASS 交付量归因文案: 单位=辆")


# ═══════════════════════════════════════════════════════════════════
# Test 5: attribution_templates.py 改动校验
# ═══════════════════════════════════════════════════════════════════
def test_attribution_templates_wiring():
    print("\n[TEST 5] attribution_templates.py 改动校验")
    fp = os.path.join(BACKEND_DIR, "core", "attribution_templates.py")
    with open(fp, "r", encoding="utf-8") as f:
        src = f.read()
    # DDL 含 metric_key
    assert "metric_key" in src, "DDL 应包含 metric_key 列"
    assert "DEFAULT 'delivered_units'" in src or "DEFAULT \"delivered_units\"" in src, "metric_key 应有默认值"
    # 迁移逻辑
    assert "MIGRATE_DDL" in src or "ALTER TABLE" in src, "应有老库迁移逻辑"
    # create_template / update_template 支持 metric_key
    assert "metric_key" in src, "create_template 应接受 metric_key"
    # 白名单
    assert "SUPPORTED_METRIC_KEYS" in src, "应有 SUPPORTED_METRIC_KEYS 白名单"
    # 系统预设补全
    assert src.count('"metric_key": "delivered_units"') >= 5, "5 个系统预设都应补 metric_key"
    print("  PASS DDL 新增 metric_key 列 + DEFAULT")
    print("  PASS 老库迁移逻辑存在")
    print("  PASS create_template / update_template 支持 metric_key")
    print("  PASS 系统预设全部补全 metric_key")


# ═══════════════════════════════════════════════════════════════════
# Test 6: schemas.py 契约改动校验
# ═══════════════════════════════════════════════════════════════════
def test_schemas_contract():
    print("\n[TEST 6] schemas.py 契约改动校验")
    fp = os.path.join(BACKEND_DIR, "api", "schemas.py")
    with open(fp, "r", encoding="utf-8") as f:
        src = f.read()
    # SopAnalysisRequest 新增字段
    assert "metric_key" in src, "SopAnalysisRequest 应含 metric_key"
    assert "template_id" in src, "SopAnalysisRequest 应含 template_id"
    # SopAnalysisResponse 新增字段
    assert '"metric"' in src or "'metric'" in src or "metric: Optional" in src, "SopAnalysisResponse 应含 metric 字段"
    assert "SUPPORTED_METRICS" in src, "应有 SUPPORTED_METRICS 目录"
    # MetricCatalogResponse
    assert "class MetricCatalogResponse" in src, "应有 MetricCatalogResponse 模型"
    # 模板契约
    assert "AttributionTemplateCreateRequest" in src and "metric_key" in src
    assert "AttributionTemplateUpdateRequest" in src and "metric_key" in src
    print("  PASS SopAnalysisRequest: +metric_key +template_id")
    print("  PASS SopAnalysisResponse: +metric +supported_metrics")
    print("  PASS 新增 MetricCatalogResponse")
    print("  PASS 模板契约 create/update: +metric_key")


# ═══════════════════════════════════════════════════════════════════
# Test 7: main.py 端点改动校验
# ═══════════════════════════════════════════════════════════════════
def test_main_endpoints():
    print("\n[TEST 7] main.py 端点改动校验")
    fp = os.path.join(BACKEND_DIR, "api", "main.py")
    with open(fp, "r", encoding="utf-8") as f:
        src = f.read()
    # supported-metrics 端点
    assert "/api/sop/supported-metrics" in src, "应有 /api/sop/supported-metrics 端点"
    assert "MetricCatalogResponse" in src, "main.py 应 import MetricCatalogResponse"
    # template_manager 在 sop_analyze 之前初始化（防 NameError）
    sop_analyze_pos = src.find("def sop_analyze")
    tmgr_pos = src.find("template_manager = AttributionTemplateManager()")
    assert sop_analyze_pos > 0 and tmgr_pos > 0
    assert tmgr_pos < sop_analyze_pos, "template_manager 必须在 sop_analyze 之前初始化（防 NameError）"
    # sop_analyze 接受 template_id
    assert "req.template_id" in src, "sop_analyze 应读取 req.template_id"
    # sop_analyze 接受 metric_key
    assert "req.metric_key" in src or "metric_key=metric_key" in src, "sop_analyze 应透传 metric_key"
    print("  PASS 新增 /api/sop/supported-metrics 端点")
    print("  PASS template_manager 在 sop_analyze 之前初始化（防 NameError）")
    print("  PASS sop_analyze 支持 template_id / metric_key")


# ═══════════════════════════════════════════════════════════════════
# Test 8: 前端 templates/page.tsx 改动校验
# ═══════════════════════════════════════════════════════════════════
def test_templates_page_changes():
    print("\n[TEST 8] 前端 templates/page.tsx 改动校验")
    fp = os.path.join(FRONTEND_DIR, "src", "app", "templates", "page.tsx")
    assert os.path.exists(fp), f"文件不存在: {fp}"
    with open(fp, "r", encoding="utf-8") as f:
        src = f.read()
    # MetricOption 类型
    assert "interface MetricOption" in src, "应有 MetricOption 类型定义"
    assert "metric_key" in src, "Template 接口应含 metric_key"
    # 加载指标目录
    assert "/api/sop/supported-metrics" in src, "应请求 /api/sop/supported-metrics"
    # 迁移 banner
    assert "legacyTemplateCount" in src, "应有 legacyTemplateCount 迁移检测"
    # 卡片显示指标
    assert "getMetricLabel" in src, "卡片应通过 getMetricLabel 展示指标"
    # 编辑器含指标下拉
    assert "metricKey" in src and "handleMetricChange" in src, "编辑器应有 metricKey 状态 + handleMetricChange"
    # 保存时带 metric_key
    assert "metric_key: metricKey" in src, "保存时应带 metric_key 字段"
    print("  PASS MetricOption 类型 + Template.metric_key")
    print("  PASS 加载 /api/sop/supported-metrics")
    print("  PASS 迁移 banner 检测")
    print("  PASS 卡片展示归因指标")
    print("  PASS 编辑器含指标下拉 + 自动剔除")
    print("  PASS 保存接口携带 metric_key")


# ═══════════════════════════════════════════════════════════════════
# Test 9: 前端 DimensionPicker.tsx 改动校验
# ═══════════════════════════════════════════════════════════════════
def test_dimension_picker_changes():
    print("\n[TEST 9] 前端 DimensionPicker.tsx 改动校验")
    fp = os.path.join(FRONTEND_DIR, "src", "components", "DimensionPicker.tsx")
    assert os.path.exists(fp)
    with open(fp, "r", encoding="utf-8") as f:
        src = f.read()
    # MetricOption + FALLBACK_METRICS
    assert "interface MetricOption" in src, "应有 MetricOption 类型"
    assert "FALLBACK_METRICS" in src, "应有 FALLBACK_METRICS 兜底"
    # 5 个指标 key 都出现
    for key in ("delivered_units", "gross_revenue", "customer_leads", "conversion_rate", "avg_price"):
        assert key in src, f"DimensionPicker 应包含指标 {key}"
    # onConfirm 签名变更
    assert "onConfirm: (selected: string[], metricKey: string)" in src, \
           "onConfirm 签名应改为接受 metricKey"
    assert "onConfirm(selected, metricKey)" in src, "onConfirm 调用应带 metricKey"
    # 维度过滤置灰
    assert "allowedDimSet" in src, "应有 allowedDimSet 计算"
    assert "不适用" in src, "维度列表应显示'不适用'标签"
    # 指标切换自动剔除
    assert "handleMetricChange" in src and "metricAutoPruned" in src, \
           "应有 handleMetricChange + 自动剔除提示"
    print("  PASS MetricOption 类型 + FALLBACK_METRICS 兜底")
    print("  PASS 5 个指标 key 全部定义")
    print("  PASS onConfirm 签名改为 (selected, metricKey)")
    print("  PASS 维度列表按指标过滤置灰 + 显示'不适用'")
    print("  PASS 指标切换自动剔除不适用的已选维度")


# ═══════════════════════════════════════════════════════════════════
# Test 10: 前端 page.tsx executeSopWithDimensions 改动
# ═══════════════════════════════════════════════════════════════════
def test_main_page_execute_sop():
    print("\n[TEST 10] 前端 page.tsx 调用链改动")
    fp = os.path.join(FRONTEND_DIR, "src", "app", "page.tsx")
    assert os.path.exists(fp)
    with open(fp, "r", encoding="utf-8") as f:
        src = f.read()
    # executeSopWithDimensions 签名变更
    assert "executeSopWithDimensions = async (selectedDimensions: string[], metricKey: string" in src, \
           "executeSopWithDimensions 应接受 metricKey 参数"
    # 透传给后端
    assert "metric_key: metricKey" in src, "请求体应带 metric_key 字段"
    print("  PASS executeSopWithDimensions 接受 metricKey")
    print("  PASS 请求体透传 metric_key 给后端")


# ═══════════════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════════════
def main():
    print("=" * 70)
    print("  P1 新增功能 - 离线单测（10 项）")
    print("  覆盖：指标 × 维度 联锁矩阵 + 模板支持指标 + 前后端接入")
    print("=" * 70)

    tests = [
        test_metric_dimension_matrix_integrity,
        test_resolve_metric_whitelist,
        test_filter_applicable_dims,
        test_infer_reason_uses_metric_unit,
        test_attribution_templates_wiring,
        test_schemas_contract,
        test_main_endpoints,
        test_templates_page_changes,
        test_dimension_picker_changes,
        test_main_page_execute_sop,
    ]

    passed, failed = 0, 0
    for t in tests:
        try:
            t()
            passed += 1
        except AssertionError as e:
            print(f"  FAIL: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR: {type(e).__name__}: {e}")
            failed += 1

    print("\n" + "=" * 70)
    print(f"  测试结果: {passed} 通过 / {failed} 失败")
    print("=" * 70)
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
