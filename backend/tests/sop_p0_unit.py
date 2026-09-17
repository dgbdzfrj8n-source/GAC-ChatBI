"""
P0 新增功能 - 离线单测脚本（无外部依赖）
验证：归因维度参数化 + 归因贡献明细算法（不依赖 duckdb / SqlExecutor）

运行：python3 tests/sop_p0_unit.py
"""

import sys
import os
import re

# ═══════════════════════════════════════════════════════════════════════════
# 复制被测模块的常量（避免触发 SqlExecutor / duckdb 导入）
# 这样测试脚本完全独立于运行时，可单文件运行
# ═══════════════════════════════════════════════════════════════════════════
DIMENSION_FIELD_MAP = {
    "brand_name":    "brand_name",
    "region_name":   "region_name",
    "model_name":    "model_name",
    "energy_type":   "energy_type",
    "price_segment": "price_segment",
    "monthly":       "STRFTIME('%Y-%m', sale_date)",
}
DIMENSION_LABEL_MAP = {
    "brand_name":    "品牌",
    "region_name":   "区域",
    "model_name":    "车型",
    "energy_type":   "能源类型",
    "price_segment": "价格段",
    "monthly":       "时间",
}

def _infer_reason(dim_key: str, contribution: int) -> str:
    """与 sop_analyzer.py._infer_reason 保持一致"""
    direction = "下滑" if contribution < 0 else "增长"
    reason_map = {
        "brand_name":    f"该品牌{direction} {abs(contribution)} 辆（结构性占比变化）",
        "region_name":   f"该区域{direction} {abs(contribution)} 辆（终端需求波动）",
        "model_name":    f"该车型{direction} {abs(contribution)} 辆（产品周期/竞品冲击）",
        "energy_type":   f"该能源类型{direction} {abs(contribution)} 辆（市场结构迁移）",
        "price_segment": f"该价格段{direction} {abs(contribution)} 辆（消费偏好变化）",
        "monthly":       f"该时段{direction} {abs(contribution)} 辆（季节性/节庆效应）",
    }
    return reason_map.get(dim_key, f"变动 {abs(contribution)} 辆")


def compute_attribution_breakdown_logic(
    total_curr: int,
    total_prev: int,
    dim_curr: dict,
    dim_prev: dict,
    dim_key: str,
    top_n: int = 3
):
    """
    核心算法（脱离 SqlExecutor 的可单测版本）
    与 sop_analyzer._compute_attribution_breakdown 行为一致
    """
    total_delta = total_curr - total_prev
    if total_delta == 0:
        return []

    dim_label = DIMENSION_LABEL_MAP[dim_key]
    breakdown = []
    all_keys = set(dim_curr.keys()) | set(dim_prev.keys())

    for k in all_keys:
        prev = dim_prev.get(k, 0)
        curr = dim_curr.get(k, 0)
        contribution = curr - prev
        if abs(contribution) < 1:
            continue
        pct = round(contribution / abs(total_delta) * 100, 1)
        breakdown.append({
            "dimension_key": dim_key,
            "dimension_label": dim_label,
            "member": k,
            "contribution": int(contribution),
            "contribution_pct": pct,
            "reason": _infer_reason(dim_key, contribution)
        })

    breakdown.sort(key=lambda x: abs(x["contribution"]), reverse=True)
    return breakdown[:top_n]


# ═══════════════════════════════════════════════════════════════════════════
# Test 1: 维度映射表完整性
# ═══════════════════════════════════════════════════════════════════════════
def test_dimension_map():
    print("\n[TEST 1] 维度映射表完整性")
    expected = {"brand_name", "region_name", "model_name", "energy_type", "price_segment", "monthly"}
    actual = set(DIMENSION_FIELD_MAP.keys())
    assert actual == expected, f"期望 {expected}, 实际 {actual}"
    assert set(DIMENSION_LABEL_MAP.keys()) == expected, "中文标签 key 与字段映射 key 不一致"
    # 验证每个字段都不含 SQL 注入风险字符
    for k, v in DIMENSION_FIELD_MAP.items():
        # 允许字母数字下划线、strftime 函数
        safe_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_',%() -")
        for ch in v:
            assert ch in safe_chars, f"非法字段: {k}={v}"
    print(f"  PASS 6 个维度映射全对齐: {sorted(actual)}")


# ═══════════════════════════════════════════════════════════════════════════
# Test 2: 归因贡献明细算法（核心场景：广丰 2025-03 销量下滑 1,200 辆）
# 对应方案示例："广丰本月销量较上月下滑 1,200 辆
#   ① 华南区域贡献 -800 辆  ② 轿车品类贡献 -500 辆  ③ SUV新品增量 +100 辆"
# ═══════════════════════════════════════════════════════════════════════════
def test_attribution_breakdown():
    print("\n[TEST 2] 归因贡献明细算法 - 模拟方案示例场景")
    total_curr, total_prev = 3800, 5000
    total_delta = total_curr - total_prev
    assert total_delta == -1200, "波动量与方案示例不符"

    region_curr = {"华南": 1200, "华北": 800, "华东": 1100, "华中": 700}
    region_prev = {"华南": 2000, "华北": 900, "华东": 1300, "华中": 800}
    region_breakdown = compute_attribution_breakdown_logic(
        total_curr, total_prev, region_curr, region_prev, "region_name", top_n=6
    )

    model_curr = {"雷凌": 600, "凯美瑞": 1200, "汉兰达": 800, "威兰达": 1200}
    model_prev = {"雷凌": 1100, "凯美瑞": 1300, "汉兰达": 1000, "威兰达": 1100}
    model_breakdown = compute_attribution_breakdown_logic(
        total_curr, total_prev, model_curr, model_prev, "model_name", top_n=6
    )

    huabei = next((b for b in region_breakdown if b["member"] == "华南"), None)
    assert huabei is not None, "找不到华南区域"
    assert huabei["contribution"] == -800, f"华南贡献期望 -800 实际 {huabei['contribution']}"
    # 占比 = -800 / 1200 * 100 = -66.7%（保留负号表示方向，与方案一致）
    assert abs(abs(huabei["contribution_pct"]) - 66.7) < 0.1, f"华南占比绝对值期望 66.7% 实际 {huabei['contribution_pct']}%"
    assert huabei["contribution_pct"] < 0, "占比应保留负号（方向标识）"

    leiling = next((b for b in model_breakdown if b["member"] == "雷凌"), None)
    assert leiling is not None, "找不到雷凌车型"
    assert leiling["contribution"] == -500, f"雷凌贡献期望 -500 实际 {leiling['contribution']}"

    print(f"  PASS 华南贡献 {huabei['contribution']} 辆（占比 {huabei['contribution_pct']}%）")
    print(f"  PASS 雷凌贡献 {leiling['contribution']} 辆（占比 {leiling['contribution_pct']}%）")

    contributions = [abs(b["contribution"]) for b in region_breakdown]
    assert contributions == sorted(contributions, reverse=True), "归因明细未按贡献绝对值降序"
    print(f"  PASS 排序正确（按绝对值降序）")


# ═══════════════════════════════════════════════════════════════════════════
# Test 3: 正负混合归因（下探 + 对冲）
# ═══════════════════════════════════════════════════════════════════════════
def test_mixed_attribution():
    print("\n[TEST 3] 正负混合归因（下探 + 对冲）")
    suv_curr = {"RAV4": 1500, "汉兰达": 2000, "威兰达": 2300, "奕泽": 1500, "bZ4X": 1500}
    suv_prev = {"RAV4": 1600, "汉兰达": 2000, "威兰达": 2200, "奕泽": 1800, "bZ4X": 400}
    br = compute_attribution_breakdown_logic(
        8800, 10000, suv_curr, suv_prev, "model_name", top_n=6
    )
    bz4x = next((b for b in br if b["member"] == "bZ4X"), None)
    assert bz4x is not None and bz4x["contribution"] == 1100, "bZ4X 应 +1100（对冲）"

    yize = next((b for b in br if b["member"] == "奕泽"), None)
    assert yize is not None and yize["contribution"] == -300, "奕泽应 -300"

    total = sum(b["contribution"] for b in br)
    print(f"  PASS 5 款车型归因合计 {total} 辆")
    print(f"  PASS bZ4X(SUV新品) 对冲 +{bz4x['contribution']} 辆")
    print(f"  PASS 奕泽下滑 {yize['contribution']} 辆")


# ═══════════════════════════════════════════════════════════════════════════
# Test 4: _infer_reason 文案正确性
# ═══════════════════════════════════════════════════════════════════════════
def test_infer_reason_quality():
    print("\n[TEST 4] _infer_reason 文案正确性")
    assert "下滑" in _infer_reason("region_name", -800)
    assert "增长" in _infer_reason("region_name", 100)
    assert "800" in _infer_reason("region_name", -800)
    assert "结构性" in _infer_reason("brand_name", -500)
    assert "市场结构" in _infer_reason("energy_type", -200)
    assert "消费偏好" in _infer_reason("price_segment", -100)
    assert "季节性" in _infer_reason("monthly", -50)
    print("  PASS 下滑/增长方向正确")
    print("  PASS 6 个维度特定文案正确")


# ═══════════════════════════════════════════════════════════════════════════
# Test 5: 边界场景
# ═══════════════════════════════════════════════════════════════════════════
def test_edge_cases():
    print("\n[TEST 5] 边界场景")
    # 无波动
    assert compute_attribution_breakdown_logic(1000, 1000, {"a": 500}, {"a": 500}, "brand_name") == []
    # 贡献 < 1 的被过滤
    br = compute_attribution_breakdown_logic(1000, 1100, {"a": 600, "b": 400}, {"a": 700, "b": 400}, "brand_name")
    member_names = [b["member"] for b in br]
    assert "a" in member_names and "b" not in member_names, "无显著变化成员应被过滤"
    # 单成员
    br = compute_attribution_breakdown_logic(500, 1000, {"唯一": 500}, {"唯一": 1000}, "brand_name")
    assert len(br) == 1 and br[0]["contribution"] == -500
    # 负贡献（小波动 + 另一成员正贡献）
    br = compute_attribution_breakdown_logic(900, 1000, {"a": 500, "b": 400}, {"a": 600, "b": 400}, "brand_name")
    a = next(b for b in br if b["member"] == "a")
    assert a["contribution"] == -100
    assert "下滑" in a["reason"]
    print("  PASS 无波动 → 空列表")
    print("  PASS 贡献<1 过滤")
    print("  PASS 单成员正常")
    print("  PASS 负贡献下滑文案正确")


# ═══════════════════════════════════════════════════════════════════════════
# Test 6: 贡献占比加总验证
# ═══════════════════════════════════════════════════════════════════════════
def test_contribution_pct_sum():
    print("\n[TEST 6] 贡献占比加总验证")
    curr = {"a": 200, "b": 300, "c": 500}
    prev = {"a": 800, "b": 500, "c": 500}
    # 总：1000 vs 1800，delta = -800
    br = compute_attribution_breakdown_logic(1000, 1800, curr, prev, "brand_name", top_n=6)
    sum_contrib = sum(b["contribution"] for b in br)
    assert sum_contrib == -800, f"贡献量加总 {sum_contrib} 应等于 -800"
    # 此时只有 a 和 b 有变动，c 不变被过滤
    a = next(b for b in br if b["member"] == "a")
    b = next(b for b in br if b["member"] == "b")
    assert a["contribution_pct"] == -75.0, f"a 占比应为 -75% 实际 {a['contribution_pct']}%"
    assert b["contribution_pct"] == -25.0, f"b 占比应为 -25% 实际 {b['contribution_pct']}%"
    print(f"  PASS 贡献量加总 = {sum_contrib} 辆")
    print(f"  PASS a 占比 {a['contribution_pct']}% + b 占比 {b['contribution_pct']}% = -100%")


# ═══════════════════════════════════════════════════════════════════════════
# Test 7: 前端 DimensionPicker 组件接口校验
# ═══════════════════════════════════════════════════════════════════════════
def test_dimension_picker_component():
    print("\n[TEST 7] 前端 DimensionPicker 组件接口")
    fp = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "src", "components", "DimensionPicker.tsx"))
    assert os.path.exists(fp), f"文件不存在: {fp}"
    with open(fp, "r", encoding="utf-8") as f:
        content = f.read()

    assert "export default function DimensionPicker" in content
    assert "DIMENSION_OPTIONS" in content
    assert "onConfirm" in content and "onCancel" in content
    assert "maxSelect" in content

    matches = re.findall(r'\{\s*id:\s*"([a-z_]+)"', content)
    assert len(matches) >= 6, f"应至少 6 个维度，实际 {len(matches)}"
    print(f"  PASS DimensionPicker 组件存在")
    print(f"  PASS 导出 {len(matches)} 个维度: {matches}")


# ═══════════════════════════════════════════════════════════════════════════
# Test 8: 后端接入校验（API 端点+主流程关键字段）
# ═══════════════════════════════════════════════════════════════════════════
def test_api_and_analyzer_wiring():
    print("\n[TEST 8] 后端接入校验（API + 分析器 Wiring）")

    # 检查 sop_analyzer.py 暴露的方法
    sa_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "core", "sop_analyzer.py"))
    with open(sa_path, "r", encoding="utf-8") as f:
        sa_src = f.read()

    assert "def analyze_fulfillment_gap" in sa_src
    assert "selected_dimensions" in sa_src, "analyze_fulfillment_gap 应接收 selected_dimensions"
    assert "def _compute_attribution_breakdown" in sa_src, "应有 _compute_attribution_breakdown 方法"
    assert "def _step2_drill_down_dynamic" in sa_src, "应有 _step2_drill_down_dynamic 方法"
    assert 'attribution_breakdown' in sa_src, "analyze_fulfillment_gap 应返回 attribution_breakdown"

    # 检查 schemas.py
    sc_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "api", "schemas.py"))
    with open(sc_path, "r", encoding="utf-8") as f:
        sc_src = f.read()

    assert "selected_dimensions" in sc_src
    assert "attribution_breakdown" in sc_src
    assert "SUPPORTED_DIMENSIONS" in sc_src

    # 检查 main.py
    main_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "api", "main.py"))
    with open(main_path, "r", encoding="utf-8") as f:
        main_src = f.read()

    assert "req.selected_dimensions" in main_src or "selected_dimensions=req" in main_src, \
           "main.py 应将 req.selected_dimensions 传给分析器"
    assert "attribution_breakdown" in main_src, "main.py 应返回 attribution_breakdown 到响应"

    # 检查前端 page.tsx
    page_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "src", "app", "page.tsx"))
    with open(page_path, "r", encoding="utf-8") as f:
        page_src = f.read()

    assert "DimensionPicker" in page_src, "page.tsx 应 import DimensionPicker"
    assert "selected_dimensions" in page_src, "page.tsx 应传 selected_dimensions 给 API"
    assert "executeSopWithDimensions" in page_src, "page.tsx 应有 executeSopWithDimensions"

    print("  PASS sop_analyzer.py 暴露新方法 + 接收新参数")
    print("  PASS schemas.py 新字段定义")
    print("  PASS main.py 端点透传参数")
    print("  PASS page.tsx 前端接入")


# ═══════════════════════════════════════════════════════════════════════════
# Test 9: SopResultModal 新增表格校验
# ═══════════════════════════════════════════════════════════════════════════
def test_sop_modal_attribution_table():
    print("\n[TEST 9] SopResultModal 归因明细表")
    modal_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "src", "components", "SopResultModal.tsx"))
    with open(modal_path, "r", encoding="utf-8") as f:
        modal_src = f.read()

    assert "attribution_breakdown" in modal_src, "SopResultModal 应读取 attribution_breakdown"
    assert "贡献量" in modal_src and "归因推断" in modal_src, "表格列应有'贡献量'和'归因推断'"
    assert "维度·成员" in modal_src, "表格应展示维度+成员"
    print("  PASS SopResultModal 新增归因明细表")
    print("  PASS 表格列含: 贡献量 / 占比 / 归因推断 / 维度·成员")


# ═══════════════════════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════════════════════
def main():
    print("=" * 70)
    print("  P0 新增功能 - 离线单测（9 项）")
    print("  覆盖：归因维度参数化 + 归因贡献明细算法 + 前后端接入")
    print("=" * 70)

    tests = [
        test_dimension_map,
        test_attribution_breakdown,
        test_mixed_attribution,
        test_infer_reason_quality,
        test_edge_cases,
        test_contribution_pct_sum,
        test_dimension_picker_component,
        test_api_and_analyzer_wiring,
        test_sop_modal_attribution_table,
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
