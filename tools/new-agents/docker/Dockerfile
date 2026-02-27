# syntax=docker/dockerfile:1

# === 阶段一：构建 ===
FROM node:20-alpine AS builder
WORKDIR /app

# 复制依赖清单并安装
COPY tools/new-agents/package.json tools/new-agents/package-lock.json ./
RUN npm ci

# 复制源码并构建
COPY tools/new-agents/ ./
RUN npm run build

# === 阶段二：运行 ===
FROM nginx:alpine
# 复制 Nginx 配置
COPY tools/new-agents/docker/nginx.conf /etc/nginx/conf.d/default.conf
# 复制构建产物到 new-agents 子目录
COPY --from=builder /app/dist /usr/share/nginx/html/new-agents
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
