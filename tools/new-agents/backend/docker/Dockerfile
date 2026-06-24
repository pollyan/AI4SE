FROM python:3.11-slim

WORKDIR /app

COPY tools/new-agents/backend/requirements.txt .
RUN unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY && \
    pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com -r requirements.txt

COPY tools/new-agents/workflow_manifest.json /workflow_manifest.json
COPY tools/new-agents/professional_methods.json /professional_methods.json
COPY tools/new-agents/prompt_regression_samples.json /prompt_regression_samples.json
COPY tools/new-agents/backend/ .

EXPOSE 5002

CMD ["gunicorn", "-c", "docker/gunicorn.conf.py", "app:create_app()"]
