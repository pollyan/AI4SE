# 本地开发环境搭建指南

## 架构说明

本地开发环境**模拟真实用户场景**：

```
┌─────────────────────────────┐
│  Docker容器（轻量级）        │
├─────────────────────────────┤
│  Flask Web应用（端口5001）   │
│  PostgreSQL数据库（端口5432）│
└─────────────────────────────┘
              ↕
┌─────────────────────────────┐
│  本地手动启动（模拟用户）    │
├─────────────────────────────┤
│  MidScene Server（端口3001） │
│  - node midscene_server.js  │
└─────────────────────────────┘
```

**为什么这样设计？**
1. 开发环境 = 用户真实使用场景
2. 开发者能体验完整的部署流程
3. Docker只负责Web应用，轻量快速

---

## 🚀 快速开始

### 步骤1: 安装Docker Desktop

参考 [QUICK_START_DOCKER.md](./QUICK_START_DOCKER.md) 安装Docker。

### 步骤2: 配置环境变量

创建 `.env` 文件：

```bash
cp .env.docker.example .env
nano .env
```

填入配置（重要）：

```env
# 数据库配置
DB_USER=intent_user
DB_PASSWORD=dev_password

# AI配置（必填）
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MIDSCENE_MODEL_NAME=qwen-vl-max-latest

# Flask配置
SECRET_KEY=local-dev-secret
FLASK_ENV=development
```

### 步骤3: 启动Docker服务

```bash
# 启动Web应用和数据库
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# 或后台运行
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

### 步骤4: 手动启动MidScene Server

**新开一个终端窗口**，在项目根目录执行：

```bash
# 安装Node.js依赖（首次）
npm install

# 启动MidScene服务器
node midscene_server.js
```

成功启动后会看到：

```
🚀 MidScene Server Started Successfully
🌐 HTTP服务器: http://localhost:3001
💡 AI模型: qwen-vl-max-latest
```

### 步骤5: 验证服务

访问以下地址确认服务正常：

- **Web应用**: http://localhost:5001
- **MidScene健康检查**: http://localhost:3001/health

---

## 🔧 开发工作流

### 日常开发流程

```bash
# 终端1：启动Docker服务（Web应用+数据库）
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# 终端2：启动MidScene Server
node midscene_server.js

# 浏览器：访问 http://localhost:5001
```

### 代码修改

**Python代码修改**（自动热重载）：
- 修改 `web_gui/` 下的文件
- Flask会自动检测并重启
- 刷新浏览器即可看到效果

**Node.js代码修改**（需手动重启）：
- 修改 `midscene_server.js`
- 在终端按 `Ctrl+C` 停止
- 重新运行 `node midscene_server.js`

### 数据库管理

```bash
# 使用数据库GUI工具连接
Host: localhost
Port: 5432
Database: intent_test
User: intent_user
Password: dev_password

# 或使用命令行
docker-compose exec postgres psql -U intent_user -d intent_test
```

---

## 📊 常用命令

### Docker服务管理

```bash
# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f web-app

# 重启Web应用
docker-compose restart web-app

# 停止所有服务
docker-compose down

# 清空数据库（重新开始）
docker-compose down -v
docker-compose up -d
```

### MidScene Server管理

```bash
# 查看MidScene进程
ps aux | grep midscene_server

# 停止MidScene
# 在运行的终端按 Ctrl+C
# 或者
pkill -f midscene_server.js

# 后台运行MidScene（可选）
nohup node midscene_server.js > midscene.log 2>&1 &

# 查看后台日志
tail -f midscene.log
```

---

## 🐛 常见问题

### Q1: MidScene无法连接到Web应用

**症状**: MidScene报错无法访问localhost:5001

**解决**: 
- 确认Web应用已启动：`docker-compose ps`
- 在Docker容器中，使用 `host.docker.internal:5001` 访问宿主机服务

### Q2: Web应用无法连接MidScene

**症状**: Web界面提示"MidScene服务不可用"

**解决**:
- 确认MidScene已启动：访问 http://localhost:3001/health
- 检查 `.env` 中MIDSCENE_SERVER_URL配置
- 在Docker配置中使用 `host.docker.internal:3001`

### Q3: 端口被占用

**症状**: 启动失败，提示端口5001/3001已被占用

**解决**:
```bash
# 查看端口占用
lsof -i :5001
lsof -i :3001

# 停止占用的进程
kill -9 <PID>
```

### Q4: 数据库无法连接

**症状**: Web应用报错数据库连接失败

**解决**:
```bash
# 检查数据库状态
docker-compose exec postgres pg_isready

# 查看数据库日志
docker-compose logs postgres

# 重启数据库
docker-compose restart postgres
```

---

## 🧪 运行测试

### Python测试

```bash
# 在容器中运行测试
docker-compose exec web-app pytest tests/

# 或本地运行（需要安装依赖）
python -m pytest tests/
```

### Node.js测试

```bash
# MidScene Server测试
npm run test:proxy
```

---

## 📝 开发建议

### 推荐开发工具

- **IDE**: VS Code / PyCharm
- **数据库工具**: TablePlus / DBeaver
- **API测试**: Postman / Insomnia
- **容器管理**: Docker Desktop

### VS Code扩展推荐

- Python
- Pylance
- Docker
- PostgreSQL
- ESLint

### Git提交前检查

```bash
# 代码格式检查
python scripts/quality_check.py

# 运行测试
docker-compose exec web-app pytest tests/

# 确保.env没有被提交
git status | grep .env
```

---

## 🎯 下一步

开发环境搭建完成后：

1. 阅读 [README.md](./README.md) 了解项目功能
2. 查看 [ARCHITECTURE_DEPLOYMENT.md](./ARCHITECTURE_DEPLOYMENT.md) 了解架构
3. 运行测试用例验证功能
4. 开始开发新功能！

---

**问题反馈**: 如遇到问题，请检查日志或提issue
