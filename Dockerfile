# Flask Web应用 Dockerfile (优化版)
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 配置 pip 使用国内镜像源（阿里云）加速安装
ENV PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
ENV PIP_TRUSTED_HOST=mirrors.aliyun.com

# 安装系统依赖
# 使用国内镜像源加速 apt-get
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# 复制并安装Python依赖（独立层，利用缓存）
COPY requirements_cloud.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码（经常变化，放在后面）
COPY web_gui ./web_gui
COPY api ./api
COPY migrations ./migrations
COPY scripts ./scripts
COPY start.py .
COPY .env.docker.example .

# 创建必要的目录
RUN mkdir -p web_gui/static/screenshots logs

# 暴露端口
EXPOSE 5001

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5001/health')" || exit 1

# 启动命令
CMD ["python", "start.py"]
