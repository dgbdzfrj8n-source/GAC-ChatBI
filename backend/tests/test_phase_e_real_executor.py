"""
Phase E - 真实 NL2SQL 执行器测试（独立可运行版）
不依赖 fastapi，提取执行器核心逻辑到独立函数测试
"""
import sys
import os
import json
import re
import time
import uuid
from typing import Optional

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


# ===== 复制执行器核心逻辑（无 fastapi 依赖）=====
def _resolve_question(step: dict, params: dict) -> str:
    question = step.get("question", "")
    for k, v in params.items():
        question = question.replace("{" + k + "}", str(v))
    return question


def _exec_strategy(step: dict, prev_output, last_sql_result) -> dict:
    strategy = step.get("strategy", "topn")
    n = int(step.get("n", 10))
    threshold = step.get("threshold")
    rows = (last_sql_result or {}).get("rows", []) or []
    columns = (last_sql_result or {}).get("columns", []) or []

    if not rows:
        return {"type": "strategy", "strategy": strategy, "n": n,
                "input_rows": 0, "output_rows": 0,
                "result": {"columns": columns, "rows": []},
                "note": "无 SQL 结果可处理"}

    numeric_idx = None
    for col_idx in range(len(columns)):
        sample = next((r[col_idx] for r in rows if col_idx < len(r)), None)
        if isinstance(sample, (int, float)):
            numeric_idx = col_idx
            break

    processed = list(rows)
    if strategy == "topn":
        if numeric_idx is not None:
            processed = sorted(processed, key=lambda r: (r[numeric_idx] if numeric_idx < len(r) else 0), reverse=True)
        processed = processed[:n]
    elif strategy == "bottomn":
        if numeric_idx is not None:
            processed = sorted(processed, key=lambda r: (r[numeric_idx] if numeric_idx < len(r) else 0))
        processed = processed[:n]
    elif strategy == "threshold_filter":
        if threshold is not None and numeric_idx is not None:
            processed = [r for r in processed if numeric_idx < len(r) and r[numeric_idx] is not None and r[numeric_idx] >= threshold]
    elif strategy == "sort_desc":
        if numeric_idx is not None:
            processed = sorted(processed, key=lambda r: (r[numeric_idx] if numeric_idx < len(r) else 0), reverse=True)
    else:
        return {"type": "strategy", "strategy": strategy,
                "input_rows": len(rows), "output_rows": 0,
                "result": {"columns": columns, "rows": []},
                "warning": f"unknown strategy '{strategy}'"}

    return {"type": "strategy", "strategy": strategy, "n": n, "threshold": threshold,
            "input_rows": len(rows), "output_rows": len(processed),
            "result": {"columns": columns, "rows": processed}}


def _exec_aggregation(step: dict, last_sql_result, prev_output) -> dict:
    aggregation = step.get("aggregation", "sum")
    group_by = step.get("group_by", []) or []
    rows = (last_sql_result or {}).get("rows", []) or []
    columns = (last_sql_result or {}).get("columns", []) or []

    if not rows:
        return {"type": "aggregation", "aggregation": aggregation, "input_rows": 0,
                "result": {"columns": [], "rows": []}}

    numeric_idxs = [i for i in range(len(columns))
                    if any(isinstance(r[i] if i < len(r) else None, (int, float)) for r in rows if r)]

    if not numeric_idxs:
        return {"type": "aggregation", "aggregation": aggregation, "input_rows": len(rows),
                "result": {"columns": columns, "rows": rows},
                "note": "无数值列可聚合，原样返回"}

    def _agg(vals, op):
        nums = [v for v in vals if isinstance(v, (int, float))]
        if not nums:
            return None
        if op == "sum": return round(sum(nums), 4)
        if op == "avg": return round(sum(nums) / len(nums), 4)
        if op == "max": return max(nums)
        if op == "min": return min(nums)
        if op == "count": return len(nums)
        return None

    if not group_by:
        out_row = []
        for col_idx in range(len(columns)):
            if col_idx in numeric_idxs:
                out_row.append(_agg([r[col_idx] for r in rows if col_idx < len(r)], aggregation))
            else:
                out_row.append(None)
        out_columns = [f"{aggregation.upper()}_{c}" if i in numeric_idxs else c for i, c in enumerate(columns)]
        return {"type": "aggregation", "aggregation": aggregation, "group_by": [],
                "input_rows": len(rows), "output_rows": 1,
                "result": {"columns": out_columns, "rows": [out_row]}}

    group_idxs = [columns.index(g) for g in group_by if g in columns]
    if not group_idxs:
        return {"type": "aggregation", "aggregation": aggregation, "group_by": group_by,
                "warning": f"group_by 列不存在: {group_by}",
                "result": {"columns": columns, "rows": rows}}

    groups = {}
    for r in rows:
        key = tuple(r[i] if i < len(r) else None for i in group_idxs)
        groups.setdefault(key, []).append(r)

    out_rows = []
    for key, grp_rows in groups.items():
        out_row = list(key)
        for col_idx in range(len(columns)):
            if col_idx in group_idxs:
                continue
            if col_idx in numeric_idxs:
                out_row.append(_agg([r[col_idx] for r in grp_rows if col_idx < len(r)], aggregation))
            else:
                out_row.append(grp_rows[0][col_idx] if grp_rows and col_idx < len(grp_rows[0]) else None)
        out_rows.append(out_row)

    out_columns = list(group_by) + [f"{aggregation.upper()}_{c}" if i in numeric_idxs else c
                                     for i, c in enumerate(columns) if i not in group_idxs]
    return {"type": "aggregation", "aggregation": aggregation, "group_by": group_by,
            "input_rows": len(rows), "output_rows": len(out_rows),
            "result": {"columns": out_columns, "rows": out_rows}}


def _exec_conclusion(step: dict, prev_output, last_sql_result, all_outputs) -> dict:
    nl2sql_conclusion = None
    for so in reversed(all_outputs):
        out = so.get("output", {})
        if out.get("type") == "nl2sql" and out.get("conclusion"):
            nl2sql_conclusion = out["conclusion"]
            break

    prompt = step.get("prompt", "")
    rows = (last_sql_result or {}).get("rows", []) or []
    columns = (last_sql_result or {}).get("columns", []) or []

    stats = {"row_count": len(rows), "columns": columns}
    if rows and columns:
        for col_idx, col in enumerate(columns):
            nums = [r[col_idx] for r in rows if col_idx < len(r) and isinstance(r[col_idx], (int, float))]
            if nums:
                stats[f"{col}_avg"] = round(sum(nums) / len(nums), 2)
                stats[f"{col}_max"] = max(nums)
                stats[f"{col}_min"] = min(nums)

    if nl2sql_conclusion:
        text = nl2sql_conclusion
    elif prompt:
        text = f"{prompt}\n\n[数据上下文] 行数={len(rows)}; 列={columns}"
    else:
        text = f"已完成 {len(all_outputs)} 个步骤，最终结果包含 {len(rows)} 行 {len(columns)} 列。"

    return {"type": "conclusion", "text": text, "stats": stats,
            "context_step_count": len(all_outputs),
            "used_nl2sql_conclusion": nl2sql_conclusion is not None}


# ===== Tests =====
def test_e2_variable_substitution():
    step = {"question": "{brand} {year_month} 销量"}
    params = {"brand": "埃安", "year_month": "2025-03"}
    q = _resolve_question(step, params)
    assert q == "埃安 2025-03 销量", f"got: {q}"
    print(f"  ✅ 变量替换: {q}")


def test_e3_strategy_topn():
    step = {"type": "strategy", "strategy": "topn", "n": 3}
    last_sql = {"columns": ["brand", "units"],
                "rows": [["A", 100], ["B", 500], ["C", 300], ["D", 200], ["E", 400]]}
    out = _exec_strategy(step, None, last_sql)
    assert out["output_rows"] == 3
    assert out["result"]["rows"][0][1] == 500
    assert out["result"]["rows"][1][1] == 400
    assert out["result"]["rows"][2][1] == 300
    print(f"  ✅ topn: {out['result']['rows']}")


def test_e3b_strategy_threshold():
    step = {"type": "strategy", "strategy": "threshold_filter", "threshold": 300}
    last_sql = {"columns": ["brand", "units"],
                "rows": [["A", 100], ["B", 500], ["C", 300], ["D", 200], ["E", 400]]}
    out = _exec_strategy(step, None, last_sql)
    assert out["output_rows"] == 3
    print(f"  ✅ threshold_filter: {out['output_rows']} 行 (≥300)")


def test_e3c_strategy_bottomn():
    step = {"type": "strategy", "strategy": "bottomn", "n": 2}
    last_sql = {"columns": ["brand", "units"],
                "rows": [["A", 100], ["B", 500], ["C", 300]]}
    out = _exec_strategy(step, None, last_sql)
    assert out["output_rows"] == 2
    assert out["result"]["rows"][0][1] == 100
    assert out["result"]["rows"][1][1] == 300
    print(f"  ✅ bottomn: {out['result']['rows']}")


def test_e4_aggregation_sum():
    step = {"type": "aggregation", "aggregation": "sum"}
    last_sql = {"columns": ["brand", "units"],
                "rows": [["A", 100], ["B", 200], ["C", 300]]}
    out = _exec_aggregation(step, last_sql, None)
    assert out["output_rows"] == 1
    assert out["result"]["rows"][0][1] == 600
    print(f"  ✅ sum: total={out['result']['rows'][0][1]}")


def test_e4b_aggregation_avg():
    step = {"type": "aggregation", "aggregation": "avg"}
    last_sql = {"columns": ["brand", "units"],
                "rows": [["A", 100], ["B", 200], ["C", 300]]}
    out = _exec_aggregation(step, last_sql, None)
    assert out["result"]["rows"][0][1] == 200.0
    print(f"  ✅ avg: {out['result']['rows'][0][1]}")


def test_e4c_aggregation_groupby():
    step = {"type": "aggregation", "aggregation": "sum", "group_by": ["brand"]}
    last_sql = {"columns": ["brand", "model", "units"],
                "rows": [["A", "M1", 100], ["A", "M2", 200], ["B", "M1", 300], ["B", "M2", 50]]}
    out = _exec_aggregation(step, last_sql, None)
    assert out["output_rows"] == 2
    rows_by_brand = {r[0]: r for r in out["result"]["rows"]}
    assert rows_by_brand["A"][-1] == 300
    assert rows_by_brand["B"][-1] == 350
    print(f"  ✅ group_by: A=300, B=350")


def test_e4d_aggregation_max_min():
    step_max = {"type": "aggregation", "aggregation": "max"}
    step_min = {"type": "aggregation", "aggregation": "min"}
    last_sql = {"columns": ["x"], "rows": [[10], [50], [30]]}
    out_max = _exec_aggregation(step_max, last_sql, None)
    out_min = _exec_aggregation(step_min, last_sql, None)
    assert out_max["result"]["rows"][0][0] == 50
    assert out_min["result"]["rows"][0][0] == 10
    print(f"  ✅ max/min: max={out_max['result']['rows'][0][0]}, min={out_min['result']['rows'][0][0]}")


def test_e5_conclusion_uses_nl2sql():
    step = {"type": "conclusion", "prompt": "请总结"}
    all_outputs = [{"index": 0, "name": "查询",
                    "output": {"type": "nl2sql", "conclusion": "3月埃安交付 1234 辆"}}]
    last_sql = {"columns": ["units"], "rows": [[1234]]}
    out = _exec_conclusion(step, None, last_sql, all_outputs)
    assert out["type"] == "conclusion"
    assert out["used_nl2sql_conclusion"] is True
    assert "1234" in out["text"]
    assert "units_avg" in out["stats"]
    print(f"  ✅ conclusion 复用 NL2SQL: '{out['text'][:50]}...'")


def test_e5b_conclusion_no_nl2sql_uses_prompt():
    """当没有 NL2SQL 输出时，conclusion 应用 prompt 模板"""
    step = {"type": "conclusion", "prompt": "请总结数据"}
    all_outputs = []
    last_sql = {"columns": ["x"], "rows": [[1], [2]]}
    out = _exec_conclusion(step, None, last_sql, all_outputs)
    assert out["used_nl2sql_conclusion"] is False
    assert "请总结数据" in out["text"]
    print(f"  ✅ conclusion 用 prompt: '{out['text'][:30]}...'")


def test_e5c_conclusion_stats():
    """stats 应包含数值列的 avg/max/min"""
    step = {"type": "conclusion"}
    all_outputs = []
    last_sql = {"columns": ["sales"], "rows": [[100], [200], [300]]}
    out = _exec_conclusion(step, None, last_sql, all_outputs)
    assert out["stats"]["sales_avg"] == 200.0
    assert out["stats"]["sales_max"] == 300
    assert out["stats"]["sales_min"] == 100
    print(f"  ✅ stats: avg=200, max=300, min=100")


def test_e6_pipeline_nl2sql_then_strategy():
    """完整 pipeline：模拟 NL2SQL 输出 + Strategy top5"""
    # 模拟 NL2SQL 输出
    nl2sql_out = {
        "type": "nl2sql",
        "status": "success",
        "sql": "SELECT brand, SUM(units) FROM fact GROUP BY brand",
        "result": {
            "columns": ["brand", "total_units"],
            "rows": [["A", 1000], ["B", 5000], ["C", 3000], ["D", 2000], ["E", 4000], ["F", 1500]],
            "row_count": 6,
        },
        "conclusion": "B 品牌销量第一",
    }
    # Strategy top5
    strategy_out = _exec_strategy(
        {"type": "strategy", "strategy": "topn", "n": 5},
        prev_output=nl2sql_out,
        last_sql_result=nl2sql_out["result"],
    )
    assert strategy_out["output_rows"] == 5
    assert strategy_out["result"]["rows"][0][0] == "B"
    assert strategy_out["result"]["rows"][0][1] == 5000
    # Conclusion
    conc_out = _exec_conclusion(
        {"type": "conclusion"},
        prev_output=strategy_out,
        last_sql_result=strategy_out["result"],
        all_outputs=[{"index": 0, "output": nl2sql_out}, {"index": 1, "output": strategy_out}],
    )
    assert conc_out["used_nl2sql_conclusion"] is True
    assert "B 品牌销量第一" in conc_out["text"]
    print(f"  ✅ pipeline 3 步: NL2SQL → top5 → conclusion")


def test_e7_aggregation_count():
    step = {"type": "aggregation", "aggregation": "count"}
    last_sql = {"columns": ["brand", "units"], "rows": [["A", 1], ["B", 2], ["C", 3]]}
    out = _exec_aggregation(step, last_sql, None)
    assert out["result"]["rows"][0][1] == 3
    print(f"  ✅ count: {out['result']['rows'][0][1]}")


def test_e8_strategy_empty_input():
    step = {"type": "strategy", "strategy": "topn", "n": 5}
    out = _exec_strategy(step, None, last_sql_result={"columns": [], "rows": []})
    assert out["output_rows"] == 0
    assert "无 SQL 结果" in out["note"]
    print(f"  ✅ 空输入: 优雅降级")


def test_e9_aggregation_empty_input():
    step = {"type": "aggregation", "aggregation": "sum"}
    out = _exec_aggregation(step, last_sql_result=None, prev_output=None)
    assert out["input_rows"] == 0
    print(f"  ✅ 空输入: 优雅降级")


def main():
    print("=" * 60)
    print("Phase E - 真实 NL2SQL 执行器测试（13 个 case）")
    print("=" * 60)
    tests = [
        ("E.2 变量替换", test_e2_variable_substitution),
        ("E.3a topn", test_e3_strategy_topn),
        ("E.3b threshold_filter", test_e3b_strategy_threshold),
        ("E.3c bottomn", test_e3c_strategy_bottomn),
        ("E.4a sum", test_e4_aggregation_sum),
        ("E.4b avg", test_e4b_aggregation_avg),
        ("E.4c group_by sum", test_e4c_aggregation_groupby),
        ("E.4d max/min", test_e4d_aggregation_max_min),
        ("E.4e count", test_e7_aggregation_count),
        ("E.5a 复用 NL2SQL conclusion", test_e5_conclusion_uses_nl2sql),
        ("E.5b 用 prompt 模板", test_e5b_conclusion_no_nl2sql_uses_prompt),
        ("E.5c stats 计算", test_e5c_conclusion_stats),
        ("E.6 pipeline 3 步串联", test_e6_pipeline_nl2sql_then_strategy),
        ("E.8 strategy 空输入", test_e8_strategy_empty_input),
        ("E.9 aggregation 空输入", test_e9_aggregation_empty_input),
    ]
    passed = 0
    failed = 0
    for name, fn in tests:
        print(f"\n[Test] {name}")
        try:
            fn()
            passed += 1
        except AssertionError as e:
            print(f"  ❌ FAIL: {e}")
            failed += 1
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    print(f"\n{'=' * 60}")
    print(f"Phase E 测试: {passed} passed, {failed} failed, {passed + failed} total")
    print("=" * 60)
    return failed


if __name__ == "__main__":
    sys.exit(main())
