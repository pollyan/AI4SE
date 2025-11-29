# Docker Desktop 安装指南 (macOS)

## 🔍 当前状态

您的Mac还没有安装Docker。让我们来安装它！

## 📥 安装步骤

### 方法一：使用Homebrew（推荐）⭐

```bash
# 1. 如果还没安装Homebrew，先安装它
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. 安装Docker Desktop
brew install --cask docker

# 3. 启动Docker Desktop
open /Applications/Docker.app

# 4. 等待Docker启动（菜单栏会出现Docker图标）
# 验证安装
docker --version
docker-compose --version
```

### 方法二：手动下载安装

1. **访问Docker官网下载**
   - Apple Silicon (M1/M2): https://desktop.docker.com/mac/main/arm64/Docker.dmg
   - Intel芯片: https://desktop.docker.com/mac/main/amd64/Docker.dmg

2. **安装步骤**
   - 双击下载的 `Docker.dmg`
   - 将Docker图标拖到Applications文件夹
   - 打开Applications，双击Docker
   - 首次启动需要授权（输入密码）

3. **验证安装**
   ```bash
   docker --version
   docker-compose --version
   ```

## ⚙️ Docker配置建议

安装完成后，打开Docker Desktop，进行以下配置：

### 1. 资源配置（Settings → Resources）

推荐配置：
- **CPUs**: 2-3个核心
- **Memory**: 4GB
- **Swap**: 1GB
- **Disk Image Size**: 60GB

### 2. 启用文件共享（Settings → Resources → File Sharing）

确保项目目录有权限：
- `/Users/anhui/Documents`

### 3. 其他设置

- ✅ 开机自动启动Docker Desktop
- ✅ 使用gRPC FUSE进行文件共享（性能更好）

## 🚀 安装完成后，启动测试

```bash
# 1. 进入项目目录
cd /Users/anhui/Documents/myProgram/intent-test-framework

# 2. 创建环境变量文件
cp .env.docker.example .env
nano .env  # 编辑填入API密钥

# 3. 启动开发环境
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# 4. 访问应用
open http://localhost:5001
```

## 🎯 第一次使用Docker

构建镜像需要一些时间（5-10分钟），主要是：
- 下载基础镜像（Python、Node.js、PostgreSQL）
- 安装依赖
- 安装Playwright浏览器

后续启动会很快，因为镜像已缓存。

## ❓ 常见问题

### Docker Desktop无法启动

**症状**: 菜单栏没有Docker图标

**解决**:
```bash
# 完全卸载重装
brew uninstall --cask docker
brew install --cask docker
open /Applications/Docker.app
```

### 端口被占用

**症状**: 提示5001或3001端口已被占用

**解决**:
```bash
# 查看哪个进程占用端口
lsof -i :5001
lsof -i :3001

# 停止占用端口的进程
kill -9 <PID>
```

### 构建太慢

**症状**: docker-compose build 非常慢

**解决**:
1. 配置Docker镜像加速器（Settings → Docker Engine）
   ```json
   {
     "registry-mirrors": [
       "https://mirror.ccs.tencentyun.com",
       "https://docker.mirrors.ustc.edu.cn"
     ]
   }
   ```

2. 使用更快的网络环境

## 📚 学习资源

- Docker官方文档: https://docs.docker.com/desktop/mac/
- Docker Compose文档: https://docs.docker.com/compose/

---

**准备好了吗？** 安装完Docker后告诉我，我们继续测试部署！
