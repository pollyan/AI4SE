# Intent Test Framework - 本地代理服务器

## 快速开始

### 1. 启动服务器

**Windows:**
双击 `start.bat` 文件

**Mac/Linux:**
双击 `start.sh` 文件，或在终端中运行：
```bash
./start.sh
```

### 2. 配置AI API密钥

首次运行会自动创建配置文件 `.env`，请编辑此文件添加您的AI API密钥：

```env
# 阿里云DashScope (推荐)
OPENAI_API_KEY=sk-your-dashscope-api-key
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MIDSCENE_MODEL_NAME=qwen-vl-max-latest
```

### 3. 开始使用

配置完成后重新运行启动脚本，看到以下信息表示启动成功：

```
🚀 MidSceneJS本地代理服务器启动成功
🌐 HTTP服务器: http://localhost:3001
🔌 WebSocket服务器: ws://localhost:3001
✨ 服务器就绪，等待测试执行请求...
```

然后返回Web界面，选择"本地代理模式"即可使用！

## 系统要求

- Node.js 16.x 或更高版本
- 至少 2GB 可用内存
- 稳定的网络连接 (用于AI API调用)

## 故障排除

### Node.js未安装
请访问 https://nodejs.org/ 下载并安装Node.js LTS版本

### 端口被占用
如果3001端口被占用，可以在 `.env` 文件中修改：
```env
PORT=3002
```

### 依赖安装失败
尝试清除缓存后重新安装：
```bash
npm cache clean --force
rm -rf node_modules
npm install
```

### AI API调用失败
1. 检查API密钥是否正确
2. 确认账户余额充足
3. 检查网络连接
4. 验证BASE_URL和MODEL_NAME配置

## 技术支持

如遇问题，请检查：
1. 控制台错误信息
2. 网络连接状态
3. API密钥配置
4. 防火墙设置

---

Intent Test Framework - AI驱动的Web自动化测试平台
