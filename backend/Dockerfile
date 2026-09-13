# ==================================================
# 广汽云 ChatBI - 后端服务 Dockerfile
# Render 专用：fix HEALTHCHECK 端口 + 简化构建
# ==================================================
# 触发 Render 强制 rebuild 的标记 (commit acdb6c5 + 强制 rebuild)

FROM python:3.11-slim

# ─── 系统环境优化 ─────────────────────────────
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app

# ─── 安装编译 duckdb 需要的依赖（slim 镜像默认没有 gcc）───
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        libstdc++6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ─── 先 copy 依赖文件（利用 Docker 缓存层加速） ────
COPY requirements.txt .

# ─── 安装 Python 依赖 ─────────────────────────────
RUN pip install --no-cache-dir -r requirements.txt

# ─── 拷贝源代码 ──────────────────────────────────
COPY . .

# ─── 数据目录权限（root 启动，简化部署） ──────────
RUN mkdir -p /app/data && chmod -R 777 /app/data

# ─── 健康检查：用 ${PORT:-8000} 与应用端口对齐 ────
# Render 会注入 PORT 环境变量（通常是 10000）
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD sh -c "python -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:${PORT:-8000}/api/health', timeout=5).read()\" || exit 1"

# ─── 暴露端口 ─────────────────────────────────────
EXPOSE 8000

# ─── 启动命令（生产用 uvicorn） ─────────────────
# Render 注入 PORT，未注入时 fallback 到 8000
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --log-level info"]
