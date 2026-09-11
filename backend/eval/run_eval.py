"""
Sprint 5.4: 工业级 ChatBI 自动化评测跑分脚本
===============================================

目标：将 `eval_dataset.json` 中的问题批量跑通，自动统计：
  1. SQL Syntax Pass Rate（语法成功率）
  2. Data Result Pass Rate（数据返回成功率）
  3. Average Latency（平均响应延迟）
  4. P95 Latency（P95 响应延迟）
  5. Token Cost per Query（平均 Token 消耗）
  6. 分难度通过率（easy / medium / hard）
  7. 分业务域通过率（整车销售 / 财务 / 营销 / 渠道）

运行：
    cd backend && python -m eval.run_eval
    cd backend && python -m eval.run_eval --limit 10
    cd backend && python -m eval.run_eval --domain 整车销售
"""

import json
import time
import argparse
import statistics
from pathlib import Path
from datetime import datetime

# 让脚本能直接 import backend 模块（兼容 IDE 与命令行两种入口）
import os
import sys
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from core.nl2sql_engine import Nl2SqlEngine


DATASET_PATH = Path(__file__).parent / "eval_dataset.json"
REPORT_PATH = Path(__file__).parent / "eval_report.json"
BAD_CASES_PATH = Path(__file__).parent / "bad_cases.json"


def load_dataset() -> list:
    """加载评测数据集"""
    if not DATASET_PATH.exists():
        print(f"❌ 数据集文件不存在: {DATASET_PATH}")
        return []
    raw = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    # 兼容两种结构：纯列表 / {"cases": [...]}
    if isinstance(raw, list):
        return raw
    return raw.get("cases", [])


def evaluate_one(engine: Nl2SqlEngine, case: dict) -> dict:
    """执行单条评测用例"""
    query = case.get("query", "").strip()
    if not query:
        return {
            "id": case.get("id"),
            "query": query,
            "sql_pass": False,
            "data_pass": False,
            "execution_time_ms": 0,
            "error": "空问题",
            "difficulty": case.get("difficulty"),
            "domain": case.get("domain")
        }

    start = time.time()
    try:
        out = engine.ask(query, force_mock=False)
        elapsed_ms = (time.time() - start) * 1000

        # SQL 语法是否成功（执行不报错即算）
        sql_pass = bool(out.get("sql")) and out.get("success", False)

        # 数据返回是否成功（有数据行即算）
        data_pass = sql_pass and out.get("row_count", 0) > 0

        return {
            "id": case.get("id"),
            "query": query,
            "expected_intent": case.get("expected_intent"),
            "difficulty": case.get("difficulty"),
            "domain": case.get("domain"),
            "metric_id": case.get("metric_id"),
            "sql_pass": sql_pass,
            "data_pass": data_pass,
            "execution_time_ms": round(elapsed_ms, 1),
            "healed": out.get("healed", False),
            "engine": out.get("engine", "DuckDB"),
            "error": out.get("error"),
            "row_count": out.get("row_count", 0)
        }
    except Exception as e:
        elapsed_ms = (time.time() - start) * 1000
        return {
            "id": case.get("id"),
            "query": query,
            "sql_pass": False,
            "data_pass": False,
            "execution_time_ms": round(elapsed_ms, 1),
            "error": str(e),
            "difficulty": case.get("difficulty"),
            "domain": case.get("domain")
        }


def summarize(results: list) -> dict:
    """聚合评测结果"""
    total = len(results)
    if total == 0:
        return {"error": "无可评测数据"}

    sql_pass_count = sum(1 for r in results if r.get("sql_pass"))
    data_pass_count = sum(1 for r in results if r.get("data_pass"))
    healed_count = sum(1 for r in results if r.get("healed"))

    latencies = [r["execution_time_ms"] for r in results if r.get("execution_time_ms")]

    avg_latency = round(statistics.mean(latencies), 1) if latencies else 0
    p95_latency = 0
    if len(latencies) >= 5:
        try:
            p95_latency = round(statistics.quantiles(latencies, n=20)[18], 1)
        except Exception:
            p95_latency = round(sorted(latencies)[int(len(latencies) * 0.95)], 1)
    elif latencies:
        p95_latency = max(latencies)

    # 分难度统计
    by_difficulty = {}
    for diff in ["easy", "medium", "hard", "unknown"]:
        sub = [r for r in results if r.get("difficulty") == diff]
        if sub:
            by_difficulty[diff] = {
                "count": len(sub),
                "sql_pass_rate": round(sum(1 for r in sub if r.get("sql_pass")) / len(sub) * 100, 2),
                "data_pass_rate": round(sum(1 for r in sub if r.get("data_pass")) / len(sub) * 100, 2)
            }

    # 分域统计
    by_domain = {}
    domain_groups = set(r.get("domain") for r in results if r.get("domain"))
    for domain in domain_groups:
        sub = [r for r in results if r.get("domain") == domain]
        if sub:
            by_domain[domain] = {
                "count": len(sub),
                "sql_pass_rate": round(sum(1 for r in sub if r.get("sql_pass")) / len(sub) * 100, 2),
                "data_pass_rate": round(sum(1 for r in sub if r.get("data_pass")) / len(sub) * 100, 2)
            }

    # 失败用例清单（方便人工 review 与 Bad Case 入库）
    failed_cases = [
        {"id": r.get("id"), "query": r.get("query"), "error": r.get("error")}
        for r in results if not r.get("sql_pass")
    ]

    return {
        "summary": {
            "total": total,
            "sql_pass_count": sql_pass_count,
            "data_pass_count": data_pass_count,
            "sql_pass_rate_pct": round(sql_pass_count / total * 100, 2),
            "data_pass_rate_pct": round(data_pass_count / total * 100, 2),
            "self_heal_count": healed_count,
            "avg_latency_ms": avg_latency,
            "p95_latency_ms": p95_latency,
            "generated_at": datetime.now().isoformat()
        },
        "by_difficulty": by_difficulty,
        "by_domain": by_domain,
        "failed_cases": failed_cases[:20]  # 仅保留前 20 条失败用例，避免报告过大
    }


def run_eval(limit: int = None, domain: str = None, difficulty: str = None) -> dict:
    """执行评测主函数"""
    print("=" * 70)
    print("  GAC-ChatBI 自动化评测跑分")
    print("=" * 70)

    dataset = load_dataset()
    if not dataset:
        return {"error": "数据集为空"}

    # 过滤
    if domain:
        dataset = [c for c in dataset if c.get("domain") == domain]
    if difficulty:
        dataset = [c for c in dataset if c.get("difficulty") == difficulty]
    if limit:
        dataset = dataset[:limit]

    print(f"\n📊 待评测用例数: {len(dataset)}")
    if domain: print(f"   - 业务域过滤: {domain}")
    if difficulty: print(f"   - 难度过滤: {difficulty}")
    if limit: print(f"   - 限制条数: {limit}")
    print()

    engine = Nl2SqlEngine()
    results = []

    for i, case in enumerate(dataset, 1):
        case_id = case.get("id", f"#{i}")
        query = case.get("query", "")[:50]

        # 实时进度输出
        result = evaluate_one(engine, case)
        results.append(result)

        status = "✅" if result.get("data_pass") else ("⚠️" if result.get("sql_pass") else "❌")
        latency = result.get("execution_time_ms", 0)
        print(f"  {status} [{i:3d}/{len(dataset)}] {case_id} | {latency:>6.1f}ms | {query}...")

    report = summarize(results)

    # 输出汇总
    print("\n" + "=" * 70)
    print("  📈 评测结果汇总")
    print("=" * 70)
    s = report["summary"]
    print(f"  评测总数:       {s['total']}")
    print(f"  SQL 通过率:     {s['sql_pass_rate_pct']}%  (目标 ≥ 95%)")
    print(f"  数据通过率:     {s['data_pass_rate_pct']}%  (目标 ≥ 88%)")
    print(f"  Self-Heal 触发: {s['self_heal_count']} 次")
    print(f"  平均延迟:       {s['avg_latency_ms']} ms  (目标 ≤ 2500ms)")
    print(f"  P95 延迟:       {s['p95_latency_ms']} ms")
    print()

    if report["by_difficulty"]:
        print("  【分难度通过率】")
        for diff, stats in report["by_difficulty"].items():
            print(f"    {diff:>8s}: SQL {stats['sql_pass_rate']}% / 数据 {stats['data_pass_rate']}% ({stats['count']} 题)")
        print()

    if report["by_domain"]:
        print("  【分业务域通过率】")
        for dom, stats in report["by_domain"].items():
            print(f"    {dom:>12s}: SQL {stats['sql_pass_rate']}% / 数据 {stats['data_pass_rate']}% ({stats['count']} 题)")
        print()

    if report["failed_cases"]:
        print(f"  【失败用例 Top {len(report['failed_cases'])}】")
        for fc in report["failed_cases"][:5]:
            print(f"    ❌ {fc['id']}: {fc['query'][:60]}")
            print(f"       {fc.get('error', '')[:80]}")
        print()

    # 写入报告
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"📄 完整报告已保存: {REPORT_PATH}")
    print("=" * 70)

    return report


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description="GAC-ChatBI 自动化评测")
    parser.add_argument("--limit", type=int, default=None, help="限制评测条数")
    parser.add_argument("--domain", type=str, default=None, help="按业务域过滤")
    parser.add_argument("--difficulty", type=str, default=None, help="按难度过滤 (easy/medium/hard)")
    args = parser.parse_args()

    run_eval(limit=args.limit, domain=args.domain, difficulty=args.difficulty)


if __name__ == "__main__":
    main()
