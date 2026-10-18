"""
TC-BE-RD / TC-BE-LT 测试用例
对应 BUG-003 修复：产品经理角色默认模板改为 preset_model_product

参考：
- SDD §3.3.1 修复方案
- SDD_TEST_CASES_TEMPLATES_BUGFIX.md §2.1 / §3.1
- 测试报告 TC-TPL-036 / TC-TPL-038
"""
import sys
from pathlib import Path

# 添加 backend 到 path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.attribution_templates import (
    ROLE_DEFAULTS,
    SYSTEM_PRESETS,
)


# ════════════════════════════════════════════════════════
# TC-BE-RD-001 ~ 006：ROLE_DEFAULTS 字典单测（BUG-003 核心）
# ════════════════════════════════════════════════════════


def test_TC_BE_RD_001_executive_default_is_quarterly():
    """TC-BE-RD-001: 高管角色默认 = 高管季度复盘"""
    assert ROLE_DEFAULTS.get("executive") == "preset_exec_quarterly"


def test_TC_BE_RD_002_analyst_default_is_deep_drill():
    """TC-BE-RD-002: 分析师角色默认 = 深度下钻"""
    assert ROLE_DEFAULTS.get("analyst") == "preset_analyst_deep"


def test_TC_BE_RD_003_product_default_is_model_product():
    """TC-BE-RD-003 [P0/BUG-003 核心]: 产品经理默认必须是 preset_model_product
    不能等于 analyst 的默认 preset_analyst_deep
    """
    # 主断言：产品经理必须指向专属模板
    assert ROLE_DEFAULTS.get("product") == "preset_model_product"
    # 防御性检查：不应等于 analyst 的默认
    assert ROLE_DEFAULTS.get("product") != ROLE_DEFAULTS.get("analyst")
    # 防御性检查：不应等于 executive 的默认
    assert ROLE_DEFAULTS.get("product") != ROLE_DEFAULTS.get("executive")


def test_TC_BE_RD_004_visitor_default_is_quarterly():
    """TC-BE-RD-004: 访客角色默认 = 高管季度复盘"""
    assert ROLE_DEFAULTS.get("visitor") == "preset_exec_quarterly"


def test_TC_BE_RD_005_three_core_roles_have_distinct_defaults():
    """TC-BE-RD-005 [P0/BUG-003 验收]: 3 个核心角色默认模板必须互不相同"""
    core_roles = ["executive", "analyst", "product"]
    defaults = [ROLE_DEFAULTS.get(r) for r in core_roles]
    # 3 个值必须互不相同
    assert len(set(defaults)) == 3, (
        f"3 个核心角色默认模板必须互不相同，实际: "
        f"{dict(zip(core_roles, defaults))}"
    )


def test_TC_BE_RD_006_all_default_template_ids_exist_in_system_presets():
    """TC-BE-RD-006: 所有默认模板 ID 必须在 SYSTEM_PRESETS 中真实存在（防 typo）"""
    preset_ids = {p["id"] for p in SYSTEM_PRESETS}
    for role, tpl_id in ROLE_DEFAULTS.items():
        assert tpl_id in preset_ids, (
            f"角色 {role} 默认模板 {tpl_id} 不在 SYSTEM_PRESETS 中。"
            f"已知模板: {sorted(preset_ids)}"
        )


# ════════════════════════════════════════════════════════
# TC-BE-LT-001 ~ 003：list_templates 集成验证（用项目主 DuckDB）
# ════════════════════════════════════════════════════════


def test_TC_BE_LT_001_list_templates_product_role_default():
    """TC-BE-LT-001 [P0]: list_templates(role='product') 返回正确默认"""
    from core.attribution_templates import AttributionTemplateManager

    # 用项目主 DB（已存在的 gac_bi.duckdb）
    mgr = AttributionTemplateManager()
    result = mgr.list_templates(role="product", user="zhangsan")
    role_default_id = result.get("role_default_id")
    assert role_default_id == "preset_model_product", (
        f"产品经理 role_default_id 应为 preset_model_product，实际: {role_default_id}"
    )


def test_TC_BE_LT_002_list_templates_analyst_role_default():
    """TC-BE-LT-002: list_templates(role='analyst') 返回正确默认"""
    from core.attribution_templates import AttributionTemplateManager

    mgr = AttributionTemplateManager()
    result = mgr.list_templates(role="analyst", user="zhangsan")
    assert result.get("role_default_id") == "preset_analyst_deep"


def test_TC_BE_LT_003_list_templates_4_roles_distinct_defaults():
    """TC-BE-LT-003 [P0/BUG-003 集成验证]: 4 角色调用 list_templates 返回的默认互不相同"""
    from core.attribution_templates import AttributionTemplateManager

    mgr = AttributionTemplateManager()

    defaults = {}
    for role in ["executive", "analyst", "product", "visitor"]:
        result = mgr.list_templates(role=role, user="zhangsan")
        defaults[role] = result.get("role_default_id")

    # 3 个核心角色必须互不相同
    core = [defaults["executive"], defaults["analyst"], defaults["product"]]
    assert len(set(core)) == 3, f"3 核心角色默认必须互不相同，实际: {defaults}"

    # 产品经理必须指向专属模板
    assert defaults["product"] == "preset_model_product"


# ════════════════════════════════════════════════════════
# TC-BE-RD-007 ~ 008：防御性测试
# ════════════════════════════════════════════════════════


def test_TC_BE_RD_007_preset_model_product_exists_in_system_presets():
    """TC-BE-RD-007: 目标模板 preset_model_product 必须在 SYSTEM_PRESETS 中"""
    preset_ids = [p["id"] for p in SYSTEM_PRESETS]
    assert "preset_model_product" in preset_ids, (
        f"目标模板 preset_model_product 不在 SYSTEM_PRESETS 中，"
        f"无法作为默认模板。已知: {preset_ids}"
    )


def test_TC_BE_RD_008_preset_model_product_is_system_scope():
    """TC-BE-RD-008: 目标模板的 scope 必须是 system（不能是 user）"""
    target = next(
        (p for p in SYSTEM_PRESETS if p["id"] == "preset_model_product"),
        None,
    )
    assert target is not None, "preset_model_product 不存在"
    assert target.get("scope") in ("system", "role_default"), (
        f"目标模板 scope 应为 system/role_default，实际: {target.get('scope')}"
    )


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
