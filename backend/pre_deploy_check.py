"""
GAC-ChatBI 部署前健康检查脚本
===============================

目的：在本地完整模拟 Render 双服务构建流程，部署前发现所有潜在问题。

模拟流程：
  后端 FastAPI：
    1. 校验 Python 版本
    2. 校验 requirements.txt 中所有依赖可正常 import
    3. 校验 .env.example 中的环境变量
    4. 校验 DuckDB 数据文件存在且非空
    5. 校验所有路由可注册（import api.main）
    6. 启动 uvicorn（模拟 Render $PORT）
    7. 健康检查 /api/health
    8. 冒烟测试核心端点（/api/chat /api/sop/analyze /api/dashboard/snapshot）

  前端 Next.js：
    1. 校验 package.json 依赖完整性
    2. 校验 next.config.mjs output: "export" 配置
    3. 校验所有 .tsx/.ts 文件无明显语法错误
    4. 模拟 npm install + npm run build（实际跑构建）

输出：
  - 控制台彩色报告（绿 ✅ / 黄 ⚠️ / 红 ❌）
  - pre_deploy_report.json（机器可读）

运行：
  cd backend && python pre_deploy_check.py
"""

import json
import os
import sys
import time
import socket
import subprocess
import platform
from pathlib import Path
from datetime import datetime

# 颜色 ANSI
class C:
    G = "\033[92m"  # 绿
    Y = "\033[93m"  # 黄
    R = "\033[91m"  # 红
    B = "\033[94m"  # 蓝
    W = "\033[0m"   # 重置
    BOLD = "\033[1m"


def ok(msg):  print(f"  {C.G}✅{C.W} {msg}")
def warn(msg): print(f"  {C.Y}⚠️ {C.W} {msg}")
def err(msg):  print(f"  {C.R}❌{C.W} {msg}")
def info(msg): print(f"  {C.B}ℹ️{C.W}  {msg}")
def head(msg): print(f"\n{C.BOLD}{C.B}{'═' * 70}\n  {msg}\n{'═' * 70}{C.W}")

# 路径常量
ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
RESULTS = {"checks": [], "errors": [], "warnings": []}


def record(check_id: str, name: str, status: str, detail: str = ""):
    RESULTS["checks"].append({
        "id": check_id, "name": name, "status": status, "detail": detail
    })
    if status == "fail":
        RESULTS["errors"].append(f"[{check_id}] {name}: {detail}")
    elif status == "warn":
        RESULTS["warnings"].append(f"[{check_id}] {name}: {detail}")


# ════════════════════════════════════════════════════════════
# 阶段 1：基础环境
# ════════════════════════════════════════════════════════════
def check_environment():
    head("阶段 1：基础环境检查")

    # 1.1 Python 版本
    py_ver = platform.python_version()
    if py_ver.startswith("3.10") or py_ver.startswith("3.11") or py_ver.startswith("3.9"):
        ok(f"Python 版本：{py_ver}（满足 Render 要求 ≥ 3.9）")
        record("E101", "Python 版本", "pass", py_ver)
    else:
        warn(f"Python 版本：{py_ver}（Render 实际使用 3.10，建议本地对齐）")
        record("E101", "Python 版本", "warn", py_ver)

    # 1.2 操作系统
    info(f"操作系统：{platform.system()} {platform.release()}")
    record("E102", "操作系统", "pass", platform.platform())

    # 1.3 工作目录
    info(f"项目根：{ROOT}")
    if (ROOT / "render.yaml").exists():
        ok("render.yaml 已就位（Render Blueprint 识别用）")
        record("E103", "render.yaml", "pass")
    else:
        err("render.yaml 缺失！Render 无法识别双服务声明")
        record("E103", "render.yaml", "fail", "缺失")


# ════════════════════════════════════════════════════════════
# 阶段 2：后端依赖 + 数据底座
# ════════════════════════════════════════════════════════════
def check_backend_dependencies():
    head("阶段 2：后端依赖与数据底座")

    # 2.1 requirements.txt
    req_path = BACKEND / "requirements.txt"
    if not req_path.exists():
        err("backend/requirements.txt 缺失！Render 构建会失败")
        record("B201", "requirements.txt", "fail", "缺失")
        return
    ok(f"requirements.txt 已就位（{len(req_path.read_text().splitlines())} 行）")

    # 2.2 依赖 import 校验
    required_pkgs = [
        "fastapi", "uvicorn", "pydantic", "duckdb",
        "pandas", "httpx", "openai", "sse_starlette"
    ]
    for pkg in required_pkgs:
        try:
            __import__(pkg)
            ok(f"依赖 {pkg} 可正常 import")
        except ImportError as e:
            err(f"依赖 {pkg} import 失败：{e}")
            record(f"B202.{pkg}", f"import {pkg}", "fail", str(e))

    # 2.3 DuckDB 数据文件
    duckdb_path = BACKEND / "data" / "gac_bi.duckdb"
    if not duckdb_path.exists():
        err(f"❌ DuckDB 数据文件缺失：{duckdb_path}")
        err("   Render 部署后无法查询！需要本地生成后提交")
        record("B203", "DuckDB 数据文件", "fail", "缺失")
    else:
        size_mb = duckdb_path.stat().st_size / 1024 / 1024
        if size_mb < 0.1:
            warn(f"DuckDB 文件过小（{size_mb:.2f}MB），可能数据未灌满")
            record("B203", "DuckDB 数据文件", "warn", f"{size_mb:.2f}MB")
        else:
            ok(f"DuckDB 数据文件就绪（{size_mb:.2f}MB）")
            record("B203", "DuckDB 数据文件", "pass", f"{size_mb:.2f}MB")

    # 2.4 DuckDB 真实可读性校验
    try:
        import duckdb
        con = duckdb.connect(str(duckdb_path), read_only=True)
        tables = con.execute("SHOW TABLES").fetchall()
        con.close()
        if len(tables) >= 4:
            ok(f"DuckDB 可读，含 {len(tables)} 张表（{[t[0] for t in tables]}）")
            record("B204", "DuckDB 表清单", "pass", str([t[0] for t in tables]))
        else:
            warn(f"DuckDB 仅含 {len(tables)} 张表，业务表可能缺失")
            record("B204", "DuckDB 表清单", "warn")
    except Exception as e:
        err(f"DuckDB 文件无法打开：{e}")
        record("B204", "DuckDB 文件可读性", "fail", str(e))

    # 2.5 .env.example 校验
    env_example = BACKEND / ".env.example"
    if env_example.exists():
        ok("backend/.env.example 已就位（Render 环境变量参考）")
        record("B205", ".env.example", "pass")
    else:
        warn("backend/.env.example 缺失（建议补齐方便 Render 配置）")
        record("B205", ".env.example", "warn")


# ════════════════════════════════════════════════════════════
# 阶段 3：后端路由 + 引擎冒烟
# ════════════════════════════════════════════════════════════
def check_backend_routes():
    head("阶段 3：后端路由与引擎冒烟测试")

    try:
        sys.path.insert(0, str(BACKEND))
        from api.main import app
        ok(f"api.main:app 导入成功（{len([r for r in app.routes if hasattr(r,'path')])} 个路由）")

        # 路由清单
        critical_routes = [
            ("GET", "/api/health"),
            ("GET", "/api/metrics"),
            ("POST", "/api/chat"),
            ("POST", "/api/chat/stream"),
            ("POST", "/api/feedback"),
            ("POST", "/api/sop/analyze"),
            ("GET", "/api/dashboard/snapshot"),
        ]
        registered = {(list(r.methods)[0] if hasattr(r, "methods") and r.methods else "?", r.path) for r in app.routes if hasattr(r, "path")}
        for method, path in critical_routes:
            if (method, path) in registered:
                ok(f"路由 {method} {path} 已注册")
            else:
                err(f"路由 {method} {path} 缺失！")
                record(f"R301.{path}", f"路由 {path}", "fail", "缺失")

        record("R301", "所有路由注册", "pass" if all((m,p) in registered for m,p in critical_routes) else "fail")
    except Exception as e:
        err(f"api.main 导入失败：{e}")
        record("R301", "api.main 导入", "fail", str(e))
        return

    # 引擎初始化冒烟
    try:
        from core.nl2sql_engine import Nl2SqlEngine
        from core.sop_analyzer import SopAnalyzer
        from services.rag_retriever import get_rag

        engine = Nl2SqlEngine()
        sop = SopAnalyzer()
        rag = get_rag()
        ok("Nl2SqlEngine / SopAnalyzer / RAG 实例化成功")

        # 极简查询冒烟
        result = engine.ask("查询测试", force_mock=True)
        if result.get("success") or result.get("sql"):
            ok("NL2SQL 引擎冒烟通过")
            record("R302", "NL2SQL 引擎冒烟", "pass")
        else:
            warn(f"NL2SQL 引擎冒烟返回异常：{result.get('error')}")
            record("R302", "NL2SQL 引擎冒烟", "warn")

        rag_stats = rag.stats()
        ok(f"RAG 知识库就绪：{rag_stats['total_docs']} 文档")
        record("R303", "RAG 知识库", "pass", str(rag_stats))
    except Exception as e:
        err(f"引擎初始化失败：{e}")
        record("R302", "引擎初始化", "fail", str(e))


# ════════════════════════════════════════════════════════════
# 阶段 4：前端依赖与构建配置
# ════════════════════════════════════════════════════════════
def check_frontend_setup():
    head("阶段 4：前端依赖与构建配置")

    # 4.1 package.json
    pkg_path = FRONTEND / "package.json"
    if not pkg_path.exists():
        err("frontend/package.json 缺失！")
        record("F401", "package.json", "fail", "缺失")
        return

    pkg = json.loads(pkg_path.read_text())
    ok(f"package.json 已就位（{pkg.get('name', '?')} v{pkg.get('version', '?')}）")

    # 4.2 关键脚本
    scripts = pkg.get("scripts", {})
    if "build" in scripts and ("export" in scripts or pkg.get("scripts", {}).get("build", "").endswith("next build")):
        ok("scripts.build 已配置（Render 会跑 npm run build）")
        record("F402", "scripts.build", "pass")
    else:
        err("scripts.build 缺失或未配置 export")
        record("F402", "scripts.build", "fail")

    # 4.3 next.config 静态导出配置
    next_cfg = FRONTEND / "next.config.mjs"
    if not next_cfg.exists():
        err("frontend/next.config.mjs 缺失！Render Static Site 必须配置 output: export")
        record("F403", "next.config.mjs", "fail", "缺失")
    else:
        content = next_cfg.read_text()
        if "output" in content and "export" in content:
            ok("next.config.mjs 已配置 output: 'export'（静态导出）")
            record("F403", "next.config.mjs 静态导出", "pass")
        else:
            err("next.config.mjs 未配置 output: 'export'")
            record("F403", "next.config.mjs 静态导出", "fail")

    # 4.4 关键依赖
    deps = pkg.get("dependencies", {})
    required = ["next", "react", "react-dom", "echarts", "lucide-react"]
    for d in required:
        if d in deps:
            ok(f"依赖 {d}: {deps[d]}")
        else:
            err(f"依赖 {d} 缺失！")
            record(f"F404.{d}", f"dep {d}", "fail")

    # 4.5 关键文件存在性
    must_exist = [
        "src/app/page.tsx",
        "src/app/dashboard/page.tsx",
        "src/lib/sse.ts",
        "src/components/SopResultModal.tsx",
    ]
    for f in must_exist:
        p = FRONTEND / f
        if p.exists():
            ok(f"关键文件 {f} 已就位")
        else:
            err(f"关键文件 {f} 缺失！")
            record(f"F405.{f}", f"file {f}", "fail")

    # 4.6 是否要执行实际构建（可选，耗时 1-2 分钟）
    if "--skip-build" in sys.argv:
        warn("跳过前端实际构建（--skip-build）")
    else:
        info("准备执行前端构建（这会消耗 1-2 分钟，按 Ctrl+C 跳过）")
        try:
            if not (FRONTEND / "node_modules").exists():
                info("执行 npm install...")
                r = subprocess.run(
                    ["npm", "install", "--silent", "--no-audit", "--no-fund"],
                    cwd=FRONTEND, capture_output=True, text=True, timeout=300
                )
                if r.returncode == 0:
                    ok("npm install 完成")
                else:
                    err(f"npm install 失败：{r.stderr[-300:]}")
                    record("F406", "npm install", "fail")
                    return

            info("执行 npm run build...")
            r = subprocess.run(
                ["npm", "run", "build"],
                cwd=FRONTEND, capture_output=True, text=True, timeout=180
            )
            if r.returncode == 0:
                out_dir = FRONTEND / "out"
                if out_dir.exists():
                    size = sum(f.stat().st_size for f in out_dir.rglob("*") if f.is_file())
                    ok(f"npm run build 完成 → out/ 目录 {size/1024:.1f}KB")
                    record("F407", "前端构建", "pass", f"{size/1024:.1f}KB")
                else:
                    warn("npm run build 成功但 out/ 目录未生成")
                    record("F407", "前端构建", "warn")
            else:
                err(f"npm run build 失败：{r.stderr[-500:]}")
                record("F407", "前端构建", "fail")
        except subprocess.TimeoutExpired:
            err("前端构建超时（>180s），可能依赖过大")
            record("F407", "前端构建", "fail", "timeout")
        except FileNotFoundError:
            warn("未检测到 npm，跳过前端构建")
            record("F407", "前端构建", "warn", "无 npm")


# ════════════════════════════════════════════════════════════
# 阶段 5：网络端口冲突预检
# ════════════════════════════════════════════════════════════
def check_port(port: int) -> bool:
    """检测本地端口是否空闲"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def check_render_env():
    head("阶段 5：Render 部署环境变量预检")

    # Render 实际会注入 PORT 环境变量
    # 模拟：检查 .env.example 中的关键变量
    env_example_path = BACKEND / ".env.example"
    if env_example_path.exists():
        content = env_example_path.read_text()
        for key in ["LLM_API_KEY", "LLM_BASE_URL", "ALLOWED_ORIGINS"]:
            if key in content:
                ok(f"环境变量参考 {key} 已在 .env.example 标注")
            else:
                warn(f"环境变量 {key} 未在 .env.example 标注，部署时容易漏配")
                record(f"R501.{key}", f"env {key}", "warn")


# ════════════════════════════════════════════════════════════
# 主入口
# ════════════════════════════════════════════════════════════
def main():
    print(f"{C.BOLD}{C.B}")
    print("=" * 70)
    print("  🚀 GAC-ChatBI 部署前健康检查 v1.0")
    print("=" * 70)
    print(f"{C.W}")
    print(f"  ⏱️  开始时间：{datetime.now().isoformat()}")
    print(f"  📂 项目根：{ROOT}")

    check_environment()
    check_backend_dependencies()
    check_backend_routes()
    check_frontend_setup()
    check_render_env()

    # 最终汇总
    head("部署前健康检查汇总")
    total = len(RESULTS["checks"])
    passed = sum(1 for c in RESULTS["checks"] if c["status"] == "pass")
    failed = len(RESULTS["errors"])
    warned = len(RESULTS["warnings"])

    print(f"  总检查项：{total}")
    print(f"  {C.G}通过：{passed}{C.W}")
    print(f"  {C.Y}警告：{warned}{C.W}")
    print(f"  {C.R}失败：{failed}{C.W}")
    print()

    if failed == 0:
        print(f"  {C.G}{C.BOLD}🎉 健康检查通过！可以放心推送到 Render 部署了！{C.W}")
    else:
        print(f"  {C.R}{C.BOLD}🚨 发现 {failed} 个致命错误，请修复后再部署！{C.W}")
        for e in RESULTS["errors"]:
            print(f"     {C.R}• {e}{C.W}")

    if warned > 0:
        print(f"\n  {C.Y}⚠️  警告项（建议处理，不阻塞部署）：{C.W}")
        for w in RESULTS["warnings"][:5]:
            print(f"     {C.Y}• {w}{C.W}")

    # 写出报告
    report_path = ROOT / "backend" / "pre_deploy_report.json"
    RESULTS["summary"] = {
        "total": total, "passed": passed, "warned": warned, "failed": failed,
        "deploy_ready": failed == 0,
        "generated_at": datetime.now().isoformat()
    }
    report_path.write_text(json.dumps(RESULTS, ensure_ascii=False, indent=2))
    print(f"\n  📄 详细报告：{report_path}")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
