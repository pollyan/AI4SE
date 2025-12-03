# 本地测试指南

## 🎯 环境说明

我们有两套环境：

1. **本地开发环境** - 用于日常开发和测试
2. **远程生产环境** - 腾讯云服务器（自动部署）

## 📋 测试流程

### 1. 验证生产配置（推荐）

在修改 `docker-compose.prod.yml` 后，**先在本地验证**再推送：

```bash
# 运行配置验证脚本
bash scripts/test-prod-compose.sh
```

这个脚本会：
- ✅ 验证 YAML 语法
- ✅ 检查 Docker Compose 配置
- ✅ 列出将要创建的服务

### 2. 本地完整测试（可选）

如果想在本地完整测试生产配置：

```bash
# 注意：这会启动与生产环境相同的配置
docker-compose -f docker-compose.prod.yml up --build

# 测试完后清理
docker-compose -f docker-compose.prod.yml down
```

### 3. 本地开发环境

日常开发使用：

```bash
# 开发环境（包含完整的 PostgreSQL）
docker-compose up

# 或者使用开发配置
docker-compose -f docker-compose.dev.yml up
```

## 🔄 推荐工作流程

### 修改生产配置时

```bash
# 1. 修改 docker-compose.prod.yml
vim docker-compose.prod.yml

# 2. 本地验证
bash scripts/test-prod-compose.sh

# 3. 验证通过后提交
git add docker-compose.prod.yml
git commit -m "fix: update production config"

# 4. 推送到远程（触发自动部署）
git push origin master
```

### 修改应用代码时

```bash
# 1. 在本地开发环境测试
docker-compose up --build

# 2. 测试通过后提交
git add .
git commit -m "feat: your feature"

# 3. 推送（自动部署到腾讯云）
git push origin master
```

## 🚨 注意事项

- **生产配置使用现有数据库** - `docker-compose.prod.yml` 连接到宿主机上已有的 PostgreSQL，不会创建新的
- **本地配置包含数据库** - `docker-compose.yml` 会创建本地 PostgreSQL 容器
- **先测试后推送** - 使用 `test-prod-compose.sh` 可以避免生产环境部署失败

## 🐛 故障排查

### 本地测试失败

```bash
# 查看详细错误
docker-compose -f docker-compose.prod.yml config

# 验证 YAML 语法（需要安装 yamllint）
pip install yamllint
yamllint docker-compose.prod.yml
```

### 生产部署失败

1. 查看 GitHub Actions 日志
2. SSH 登录服务器检查
3. 回滚到上一版本（服务器会自动回滚）

---

**建议**：每次修改生产配置后都运行 `test-prod-compose.sh` 验证！
