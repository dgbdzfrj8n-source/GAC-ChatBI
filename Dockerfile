# ==================================================
# 广汽云 ChatBI - 后端服务 Dockerfile
# Fly.io / Koyeb / Render 通用部署
# Python 3.11 + DuckDB + FastAPI + Uvicorn
# Build context: project root
# ==================================================

FROM python:3.11-slim

# ─── 系统环境优化 ─────────────────────────────────
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# ─── 创建非 root 用户（安全加固） ─────────────────
RUN groupadd -r app && useradd -r -g app -d /app -s /sbin/nologin app

WORKDIR /app

# ─── 先 copy 依赖文件（利用 Docker 缓存层加速） ────
COPY backend/requirements.txt .

# ─── 安装 Python 依赖 ─────────────────────────────
RUN pip install --no-cache-dir -r requirements.txt

# ─── 拷贝后端源代码到 /app ────────────────────────
COPY backend/ .

# ─── 数据目录权限 ────────────────────────────────
RUN mkdir -p /app/data && chown -R app:app /app

# ─── 切换到非 root 用户 ──────────────────────────
USER app

# ─── 健康检查 ─────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=5).read()" || exit 1

# ─── 暴露端口 ─────────────────────────────────────
EXPOSE 8000

# ─── 启动命令（生产用 uvicorn） ─────────────────
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --log-level info"]
