# Docker本地测试 - 快速启动指南

> [!IMPORTANT]
> **关于MidScene Server部署位置**
> 
> MidScene服务器需要启动浏览器执行测试，应该运行在**客户端本地**，而不是云服务器！
> 
> - **本地开发测试**: 可以用Docker运行所有服务（包括MidScene）
> - **云服务器部署**: 只部署Flask应用和数据库，MidScene在本地运行
> 
> 详见: [ARCHITECTURE_DEPLOYMENT.md](file:///Users/anhui/Documents/myProgram/intent-test-framework/ARCHITECTURE_DEPLOYMENT.md)

## 📋 测试前准备清单

### 1. 安装Docker Desktop（必需）

您使用的是 **Apple Silicon Mac (ARM64)**，请按以下步骤安装：

#### 快速安装（推荐）
```bash
# 使用Homebrew安装
brew install --cask docker

# 启动Docker Desktop
open /Applications/Docker.app
```

或者**手动下载**：
- 访问: https://desktop.docker.com/mac/main/arm64/Docker.dmg
- 下载后双击安装，拖到Applications文件夹
- 打开Docker.app并等待启动完成（菜单栏会出现🐳图标）

#### 验证安装
```bash
docker --version
docker-compose --version
```

### 2. 配置环境变量

我已为您创建了 `.env.docker.example` 模板文件。

**请手动创建 `.env` 文件**（因为.gitignore限制）：

```bash
# 在项目根目录执行
cp .env.docker.example .env
```

然后编辑 `.env`，**必须填入您的AI API密钥**：

```bash
# 使用nano编辑器
nano .env

# 或使用VS Code
code .env
```

将 `OPENAI_API_KEY=YOUR_API_KEY_HERE` 替换为实际的API密钥。

### 3. 快速配置示例

如果您有**阿里云DashScope密钥**，`.env` 内容如下：

```env
# 数据库（本地测试用）
DB_USER=intent_user
DB_PASSWORD=test123

# AI配置（替换为您的真实密钥）
OPENAI_API_KEY=sk-your-dashscope-key-here
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MIDSCENE_MODEL_NAME=qwen-vl-max-latest

# Flask配置
SECRET_KEY=local-dev-secret-key
FLASK_ENV=development
```

---

## 🚀 启动测试

### 方式1：开发模式（推荐本地测试）

支持代码热重载，修改代码立即生效：

```bash
# 启动所有服务
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# 或后台运行
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

### 方式2：生产模式

模拟线上环境：

```bash
docker-compose up
```

---

## 🌐 访问服务

启动成功后，访问：

- **Web界面**: http://localhost:5001
- **MidScene API**: http://localhost:3001/health
- **数据库**: localhost:5432 (用户名: intent_user)

---

## 📊 监控服务状态

```bash
# 查看所有服务状态
docker-compose ps

# 查看实时日志
docker-compose logs -f

# 只看Web应用日志
docker-compose logs -f web-app

# 只看MidScene服务日志
docker-compose logs -f midscene-server
```

---

## 🛠️ 常用命令

```bash
# 停止所有服务
docker-compose down

# 停止并删除数据卷（清空数据库）
docker-compose down -v

# 重启某个服务
docker-compose restart web-app

# 重新构建镜像
docker-compose build

# 进入容器调试
docker-compose exec web-app bash
docker-compose exec midscene-server sh
```

---

## ⚠️ 首次启动注意事项

1. **构建需要时间**
   - 首次启动需要下载基础镜像（Python、Node.js、PostgreSQL）
   - 安装所有依赖
   - 预计需要 5-10 分钟

2. **等待所有服务健康**
   ```bash
   # 查看健康状态
   docker-compose ps
   # 所有服务都应该显示 "healthy"
   ```

3. **初始化数据库**（自动完成）
   - Flask应用首次启动会自动创建数据表

---

## 🐛 常见问题

### 问题1: 端口被占用

```bash
# 查看端口占用
lsof -i :5001
lsof -i :3001

# 停止占用端口的进程
kill -9 <PID>
```

### 问题2: 服务无法启动

```bash
# 查看详细错误日志
docker-compose logs web-app
docker-compose logs midscene-server

# 重新构建
docker-compose build --no-cache
docker-compose up
```

### 问题3: 数据库连接失败

```bash
# 检查数据库是否就绪
docker-compose exec postgres pg_isready

# 查看数据库日志
docker-compose logs postgres
```

### 问题4: API密钥未配置

如果看到AI相关错误，检查 `.env` 文件：
```bash
cat .env | grep OPENAI_API_KEY
```

确保密钥已正确填入。

---

## ✅ 测试验证步骤

1. **访问首页**
   ```bash
   open http://localhost:5001
   ```

2. **创建测试用例**
   - 点击"测试用例"
   - 点击"创建新用例"
   - 添加测试步骤

3. **执行测试**
   - 在执行控制台选择用例
   - 点击"执行"
   - 查看实时日志

4. **查看报告**
   - 访问测试报告页面
   - 查看执行历史

---

## 📝 完成后反馈

测试完成后，请告诉我：

- ✅ 所有服务是否正常启动？
- ✅ Web界面能否正常访问？
- ✅ 测试用例能否成功执行？
- ❌ 遇到了什么问题？

我会根据测试结果帮您优化配置！

---

**下一步**: 
1. 安装Docker Desktop
2. 创建 `.env` 并配置API密钥
3. 运行 `docker-compose up`
4. 访问 http://localhost:5001

准备好了就告诉我！🚀
