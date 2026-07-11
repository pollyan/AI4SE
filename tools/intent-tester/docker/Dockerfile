# syntax=docker/dockerfile:1
FROM mcr.microsoft.com/playwright:v1.57.0-noble AS proxy

WORKDIR /app/tools/intent-tester
COPY tools/intent-tester/package.json tools/intent-tester/package-lock.json ./
RUN npm ci --omit=dev --no-audit --no-fund
COPY tools/intent-tester/browser-automation ./browser-automation
COPY tools/intent-tester/midscene_framework ./midscene_framework
CMD ["node", "browser-automation/midscene_server.js"]

FROM python:3.11-slim AS web

WORKDIR /app

# 复制 requirements.txt 并安装 Python 依赖
COPY tools/intent-tester/requirements.txt .
RUN unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY && \
    pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com -r requirements.txt

# 复制共享模块
COPY tools/shared ./tools/shared

# 复制应用代码
COPY tools/intent-tester ./tools/intent-tester

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

# 启动 production WSGI server
CMD ["gunicorn", "--worker-class", "gthread", "--threads", "100", "--bind", "0.0.0.0:5001", "backend.app:create_app()"]
