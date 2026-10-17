#!/usr/bin/env python3
"""
GAC-ChatBI v2.0 部署前检查脚本
在推送代码前验证所有配置是否正确
"""

import os
import sys

# 颜色定义
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def check(name: str, condition: bool, detail: str = ""):
    status = f"{GREEN}✅{RESET}" if condition else f"{RED}❌{RESET}"
    print(f"  {status} {name}")
    if detail:
        print(f"     {detail}")
    return condition

def section(name: str):
    print(f"\n{BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
    print(f"{BLUE}  {name}{RESET}")
    print(f"{BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")

def main():
    print(f"\n{GREEN}╔══════════════════════════════════════════════╗{RESET}")
    print(f"{GREEN}║   GAC-ChatBI v2.0 部署前检查                 ║{RESET}")
    print(f"{GREEN}╚══════════════════════════════════════════════╝{RESET}")
    
    all_passed = True
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 1. Git 检查
    section("1. Git 仓库检查")
    
    git_exists = os.path.exists(os.path.join(root, ".git"))
    all_passed &= check("Git 仓库存在", git_exists)
    
    # 2. 前端配置检查
    section("2. 前端配置检查")
    
    # vercel.json
    vercel_json = os.path.join(root, "vercel.json")
    all_passed &= check("vercel.json 存在", os.path.exists(vercel_json))
    
    # frontend/next.config.js 或 .mjs
    next_config = os.path.exists(os.path.join(root, "frontend", "next.config.mjs"))
    next_config |= os.path.exists(os.path.join(root, "frontend", "next.config.js"))
    all_passed &= check("Next.js 配置存在", next_config)
    
    # package.json
    package_json = os.path.join(root, "frontend", "package.json")
    all_passed &= check("package.json 存在", os.path.exists(package_json))
    
    # 3. 后端配置检查
    section("3. 后端配置检查")
    
    # Dockerfile
    dockerfile = os.path.join(root, "backend", "Dockerfile")
    all_passed &= check("Dockerfile 存在", os.path.exists(dockerfile))
    
    # requirements.txt
    requirements = os.path.join(root, "backend", "requirements.txt")
    all_passed &= check("requirements.txt 存在", os.path.exists(requirements))
    
    # 验证 requirements 包含关键依赖
    if os.path.exists(requirements):
        with open(requirements) as f:
            reqs = f.read()
            checks = [
                ("fastapi", "FastAPI"),
                ("uvicorn", "Uvicorn"),
                ("duckdb", "DuckDB"),
                ("pydantic", "Pydantic"),
            ]
            for pkg, name in checks:
                all_passed &= check(f"  - {name}", pkg in reqs)
    
    # 4. 数据库检查
    section("4. 数据库检查")
    
    duckdb_path = os.path.join(root, "backend", "data", "gac_bi.duckdb")
    duckdb_exists = os.path.exists(duckdb_path)
    all_passed &= check("gac_bi.duckdb 存在", duckdb_exists)
    
    if duckdb_exists:
        size_mb = os.path.getsize(duckdb_path) / 1024 / 1024
        all_passed &= check(f"DuckDB 文件大小", size_mb > 10, f"{size_mb:.1f} MB")
    
    # v2.0 新增表
    traffic_csv = os.path.join(root, "backend", "data", "fact_dealer_traffic.csv")
    inventory_csv = os.path.join(root, "backend", "data", "fact_inventory.csv")
    all_passed &= check("fact_dealer_traffic.csv", os.path.exists(traffic_csv))
    all_passed &= check("fact_inventory.csv", os.path.exists(inventory_csv))
    
    # 5. API 路由检查
    section("5. API 路由检查")
    
    api_dir = os.path.join(root, "backend", "api")
    main_api = os.path.join(api_dir, "main.py")
    all_passed &= check("api/main.py 存在", os.path.exists(main_api))
    
    # 6. v2.0 关键文件检查
    section("6. v2.0 关键文件检查")
    
    v2_files = [
        ("backend/workflow/context.py", "工作流上下文"),
        ("backend/workflow/orchestrator.py", "工作流编排器"),
        ("backend/config.py", "v2.0 配置"),
        ("backend/data/semantic_v2.json", "v2.0 语义层"),
    ]
    for path, name in v2_files:
        full_path = os.path.join(root, path)
        all_passed &= check(f"{name}", os.path.exists(full_path), path)
    
    # 7. 前端关键组件检查
    section("7. 前端关键组件检查")
    
    fe_files = [
        ("frontend/src/components/ChatMessage.tsx", "聊天消息组件"),
        ("frontend/src/components/SuggestionPills.tsx", "快捷提问组件"),
        ("frontend/src/components/Sidebar.tsx", "侧边栏组件"),
        ("frontend/src/app/settings/page.tsx", "设置页面"),
    ]
    for path, name in fe_files:
        full_path = os.path.join(root, path)
        all_passed &= check(f"{name}", os.path.exists(full_path), path)
    
    # 8. 环境变量模板检查
    section("8. 环境变量模板检查")
    
    env_example = os.path.join(root, "backend", ".env.example")
    all_passed &= check(".env.example 存在", os.path.exists(env_example))
    
    # 9. 部署平台配置检查
    section("9. 部署平台配置检查")
    
    platforms = [
        ("vercel.json", "Vercel 配置"),
        ("render.yaml", "Render 配置"),
        ("fly.toml", "Fly.io 配置"),
    ]
    for file, name in platforms:
        all_passed &= check(f"{name}", os.path.exists(os.path.join(root, file)))
    
    # 总结
    section("部署检查总结")
    
    if all_passed:
        print(f"\n{GREEN}🎉 所有检查通过！可以开始部署。{RESET}")
        print(f"\n{GREEN}部署步骤：{RESET}")
        print(f"  1. git add . && git commit -m \"v2.0 部署准备\"")
        print(f"  2. git push origin main")
        print(f"  3. 按照 KOYEB_DEPLOY_GUIDE.md 部署后端到 Koyeb")
        print(f"  4. 按照 KOYEB_DEPLOY_GUIDE.md 部署前端到 Vercel")
        return 0
    else:
        print(f"\n{RED}⚠️  有检查项未通过，请修复后再部署。{RESET}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
