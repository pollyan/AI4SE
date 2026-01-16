# syntax=docker/dockerfile:1
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制 requirements.txt 并安装 Python 依赖
COPY tools/intent-tester/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -i https://mirrors.aliyun.com/pypi/simple/ -r requirements.txt

# 复制共享模块
COPY tools/shared ./tools/shared

# 复制应用代码
COPY tools/intent-tester ./tools/intent-tester

# 设置环境变量
# 设置环境变量
ENV PYTHONPATH=/app/tools/intent-tester:${PYTHONPATH}
ENV FLASK_APP=backend.app

# 暴露端口
EXPOSE 5001

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5001/health')"

# 切换工作目录以便 correctly resolving 'backend' package
WORKDIR /app/tools/intent-tester

# 启动应用
CMD ["python", "-m", "backend.app"]
