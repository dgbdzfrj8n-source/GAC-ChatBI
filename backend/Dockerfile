# ==================================================
# 广汽云 ChatBI - 后端服务 Dockerfile
# 生产部署使用 Python 3.11 + DuckDB + FastAPI
# ==================================================

FROM python:3.11-slim

# 系统环境优化
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8000

# 创建非 root 用户
RUN groupadd -r app && useradd -r -g app app

WORKDIR /app

# 先 copy 依赖文件，利用 docker 缓存
COPY requirements.txt .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# copy 源代码
COPY . .

# 数据文件权限
RUN mkdir -p /app/data && chown -R app:app /app

# 切换到非 root 用户
USER app

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://127.0.0.1:8000/api/health', timeout=5).raise_for_status()" || exit 1

# 暴露端口
EXPOSE 8000

# 启动 FastAPI（生产用 uvicorn，workers=1 因免费实例内存限制）
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--log-level", "info"]
