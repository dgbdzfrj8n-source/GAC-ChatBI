"""P2-2 语义层服务 - 单元测试
直接调用 service 函数，验证三层快照 / 编辑 / 召回 三大能力。
运行：cd backend && python3 tests/test_semantic_layer.py
"""
import sys
from pathlib import Path

# tests 的父目录 = backend/，加入 sys.path 让 `services` `core` 模块可导入
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_snapshot():
    from services.semantic_layer import get_full_snapshot
    s = get_full_snapshot()
    assert "version" in s, "快照必须含 version"
    assert len(s["metrics"]) == 6, f"应有 6 个指标，实际 {len(s['metrics'])}"
    assert len(s["dimensions"]) >= 15, f"维度应>=15，实际 {len(s['dimensions'])}"
    assert len(s["glossary"]) == 9, f"应有 9 个术语，实际 {len(s['glossary'])}"
    # 维度必须含 table/field/type
    d0 = s["dimensions"][0]
    assert all(k in d0 for k in ["table", "field", "type", "description"])
    print(f"  ✅ 快照: {len(s['metrics'])} 指标 / {len(s['dimensions'])} 维度 / {len(s['glossary'])} 术语")


def test_recall():
    from services.semantic_layer import preview_query
    cases = [
        ("广汽埃安3月销量达成率", "M01"),  # 业务术语→指标
        ("CPL 是多少", "M05"),               # 同义词命中
        ("广汽传祺的折扣率", "M04"),         # 终端折扣 → M04 营销费用
    ]
    for q, expect_metric in cases:
        r = preview_query(q)
        ids = [m["metric_id"] for m in r["matched_metrics"]]
        assert expect_metric in ids, f"Q={q!r} 应命中 {expect_metric}, 实际 {ids}"
        print(f"  ✅ 「{q}」 → {ids[:2]}")


def test_update_metric_and_restore():
    """编辑 + 还原测试（保证测试不破坏数据）"""
    from services.semantic_layer import update_metric
    import json
    p = Path("/Users/apple/Desktop/AI 产品经理/实战项目/GAC-ChatBI/backend/core/metrics_dict.json")
    orig = json.loads(p.read_text(encoding="utf-8"))
    orig_def = orig["metrics"][0]["definition"]

    # 修改
    new_def = orig_def + "【P2-2 测试标记】"
    updated = update_metric("M01", {"definition": new_def})
    assert "P2-2 测试标记" in updated["definition"]
    print(f"  ✅ 编辑 M01.definition 成功")

    # 还原
    updated2 = update_metric("M01", {"definition": orig_def})
    assert "P2-2 测试标记" not in updated2["definition"]
    print(f"  ✅ 还原 M01.definition 成功")


def test_update_glossary_and_restore():
    from services.semantic_layer import update_glossary
    import json
    p = Path("/Users/apple/Desktop/AI 产品经理/实战项目/GAC-ChatBI/backend/knowledge/glossary.json")
    orig = json.loads(p.read_text(encoding="utf-8"))
    orig_syns = orig["terms"][0]["synonyms"]

    new_syns = orig_syns + ["P2-2 测试同义词"]
    updated = update_glossary("达成率", {"synonyms": new_syns})
    assert "P2-2 测试同义词" in updated["synonyms"]
    print(f"  ✅ 编辑「达成率」synonyms 成功")

    update_glossary("达成率", {"synonyms": orig_syns})
    print(f"  ✅ 还原「达成率」synonyms 成功")


if __name__ == "__main__":
    print("\n=== P2-2 语义层单元测试 ===\n")
    print("[1] 三层快照")
    test_snapshot()
    print("\n[2] 召回命中")
    test_recall()
    print("\n[3] 指标编辑")
    test_update_metric_and_restore()
    print("\n[4] 术语编辑")
    test_update_glossary_and_restore()
    print("\n🎉 全部通过\n")
