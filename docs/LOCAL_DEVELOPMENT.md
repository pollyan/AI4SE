# Docker 本地开发环境使用指南

## 重要变更 🎉

**代码热更新已启用!** 现在本地 Docker 环境支持代码实时同步,无需频繁重启或重新构建。

## 启动本地环境

```bash
./scripts/deploy-local.sh
```

这个脚本会:
- 停止现有容器
- 重新构建镜像(确保依赖最新)
- 以开发模式启动服务(启用代码热更新)

## 开发工作流

### 日常代码修改

✅ **直接修改代码即可,无需任何额外操作!**

- **Python 代码**: Flask 会自动检测变化并重载
- **前端文件**: 刷新浏览器即可看到最新内容
- **配置文件**: 大部分会自动生效

### 何时需要重新构建

只有以下情况需要重新运行 `./scripts/deploy-local.sh`:

- ✏️ 修改了 `requirements.txt` (Python 依赖)
- ✏️ 修改了 `package.json` (Node.js 依赖)
- ✏️ 修改了 `Dockerfile` 或 `docker-compose*.yml`
- ✏️ 添加了新的系统级依赖

### 何时需要重启容器

通常不需要重启,但以下情况可能需要:

```bash
./scripts/restart-local.sh
```

- 🔄 修改了环境变量 (`.env` 文件)
- 🔄 服务出现异常需要重启
- 🔄 某些配置需要服务重启才能生效

## 常用命令

```bash
# 查看实时日志
docker logs intent-test-web -f

# 查看所有容器状态
docker-compose ps

# 停止服务
docker-compose down

# 进入容器调试
docker exec -it intent-test-web bash
```

## 工作原理

开发环境使用 **volumes 挂载**机制:

```yaml
# docker-compose.dev.yml
volumes:
  - ./web_gui:/app/web_gui          # 代码实时同步
  - ./api:/app/api                  # API 代码同步
  - ./start.py:/app/start.py        # 启动脚本同步
```

- 你在本地修改的文件会**立即**反映到容器内
- Flask 的 `debug=True` 模式会监控文件变化
- 检测到变化时自动重新加载应用

## 与生产环境的区别

| 特性 | 开发环境 | 生产环境 |
|------|---------|---------|
| 代码方式 | Volumes 挂载 | COPY 到镜像 |
| 自动重载 | ✅ 启用 | ❌ 禁用 |
| Debug 模式 | ✅ 启用 | ❌ 禁用 |
| 热更新 | ✅ 支持 | ❌ 需要重新部署 |

## 故障排查

### 代码修改没生效?

1. **检查文件是否正确挂载**:
   ```bash
   docker exec intent-test-web cat /app/web_gui/services/adk_agents/service.py | head -5
   ```
   
2. **查看 Flask 是否检测到变化**:
   ```bash
   docker logs intent-test-web -f | grep -i "reload"
   ```

3. **确认使用了开发配置**:
   ```bash
   docker inspect intent-test-web | grep -i "volumes" -A 10
   ```

### 容器启动失败?

1. 查看详细日志:
   ```bash
   docker logs intent-test-web --tail=100
   ```

2. 检查端口占用:
   ```bash
   lsof -i :5001
   ```

3. 重新构建(清除缓存):
   ```bash
   docker-compose down -v
   ./scripts/deploy-local.sh
   ```

## AI 助手使用提示

当 AI 助手帮你部署本地环境时,它会:
- 自动使用 `./scripts/deploy-local.sh`
- 确保开发配置已启用
- 代码修改后无需要求你重启或重新构建

如果 AI 建议你"重启 Docker"来加载新代码,那可能是个误导 - **直接告诉它代码已经通过 volumes 自动同步了!**
