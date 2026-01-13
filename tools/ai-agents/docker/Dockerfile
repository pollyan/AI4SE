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
COPY tools/ai-agents/requirements.txt .
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ -r requirements.txt

# 复制共享模块
# 复制共享模块
COPY tools/shared ./tools/shared

# 复制应用代码
COPY tools/ai-agents ./tools/ai-agents
COPY tools/frontend ./tools/frontend

# 设置环境变量
ENV PYTHONPATH=/app/tools/ai-agents:/app:${PYTHONPATH}
ENV FLASK_APP=backend/app.py

# 设置工作目录
WORKDIR /app/tools/ai-agents

# 暴露端口
EXPOSE 5002

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5002/health')"

# 启动应用
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0", "--port=5002"]
