# 真实AI执行功能设置指南

## 概述

本指南将帮助您启用Intent Test Framework的真实AI驱动测试执行功能，而不是演示版本。

## 架构说明

### 当前架构（客户端执行）
```
Web界面(Vercel) → 本地MidSceneJS服务器 → 本地Chrome浏览器
```

**特点**：
- ✅ 完全控制浏览器环境
- ✅ 无网络延迟
- ❌ 需要本地环境设置
- ❌ 不适合多用户部署

### 推荐架构（云端执行）
```
Web界面(Vercel) → 云端执行服务 → 云端浏览器
```

**特点**：
- ✅ 无需本地设置
- ✅ 支持多用户并发
- ✅ 统一的执行环境
- ✅ 更好的安全性

## 前置要求

### 1. Node.js环境
```bash
# 安装Node.js (版本 >= 16)
# 访问 https://nodejs.org/ 下载安装

# 验证安装
node --version
npm --version
```

### 2. AI模型配置
```bash
# 设置环境变量（推荐使用阿里云通义千问VL）
export OPENAI_API_KEY="your_dashscope_api_key"
export OPENAI_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
export MIDSCENE_MODEL_NAME="qwen-vl-max-latest"
```

### 3. MidSceneJS安装
```bash
# 全局安装MidSceneJS CLI
npm install -g @midscene/cli

# 验证安装
npx midscene --version
```

## 启动步骤

### 方法1: 使用启动脚本（推荐）
```bash
# 运行启动脚本
python start_midscene_server.py
```

### 方法2: 手动启动
```bash
# 1. 创建配置文件 midscene.config.json
{
  "model": {
    "name": "qwen-vl-max-latest",
    "apiKey": "your_api_key",
    "baseURL": "https://dashscope.aliyuncs.com/compatible-mode/v1"
  },
  "server": {
    "port": 3001,
    "host": "127.0.0.1"
  }
}

# 2. 启动MidSceneJS服务器
npx midscene server --port 3001
```

## 验证设置

### 1. 检查服务器状态
```bash
curl http://127.0.0.1:3001/health
```

### 2. 测试AI功能
```python
from midscene_python import MidSceneAI

# 初始化AI
ai = MidSceneAI()

# 测试基本功能
ai.goto("https://www.baidu.com")
ai.ai_input("测试", "搜索框")
ai.ai_tap("搜索按钮")
```

## 功能特性

### 真实执行vs演示执行

| 功能 | 演示版本 | 真实执行 |
|------|----------|----------|
| 浏览器控制 | ❌ 模拟 | ✅ 真实浏览器 |
| AI视觉理解 | ❌ 无 | ✅ 通义千问VL |
| 截图功能 | ❌ 假数据 | ✅ 真实截图 |
| 步骤执行 | ❌ 预设结果 | ✅ 动态执行 |
| 错误处理 | ❌ 无 | ✅ 智能重试 |

### 支持的操作类型

- **navigate**: 页面导航
- **ai_input**: AI智能输入
- **ai_tap**: AI智能点击
- **ai_assert**: AI智能断言
- **ai_wait_for**: AI智能等待
- **ai_query**: AI数据提取
- **ai_scroll**: AI智能滚动

## 故障排除

### 常见问题

1. **服务器启动失败**
   ```bash
   # 检查端口占用
   lsof -i :3001
   
   # 杀死占用进程
   kill -9 <PID>
   ```

2. **AI调用失败**
   ```bash
   # 检查API密钥
   echo $OPENAI_API_KEY
   
   # 测试API连接
   curl -H "Authorization: Bearer $OPENAI_API_KEY" \
        "$OPENAI_BASE_URL/models"
   ```

3. **浏览器启动失败**
   ```bash
   # 安装浏览器依赖（Linux）
   sudo apt-get install -y chromium-browser
   
   # 或使用系统Chrome
   export CHROME_PATH="/usr/bin/google-chrome"
   ```

### 日志调试

```bash
# 启用详细日志
export DEBUG=midscene:*
npx midscene server --port 3001
```

## 性能优化

### 1. 浏览器模式选择
- **headless**: 无头模式，性能更好
- **browser**: 有头模式，便于调试

### 2. 超时设置
```json
{
  "browser": {
    "defaultTimeout": 30000,
    "navigationTimeout": 60000
  }
}
```

### 3. 并发控制
- 建议同时运行的测试用例不超过3个
- 避免在同一页面上并发操作

## 部署到生产环境

### Docker部署
```dockerfile
FROM node:18-alpine

# 安装浏览器依赖
RUN apk add --no-cache chromium

# 设置环境变量
ENV CHROME_PATH=/usr/bin/chromium-browser
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true

# 安装MidSceneJS
RUN npm install -g @midscene/cli

# 启动服务器
CMD ["npx", "midscene", "server", "--port", "3001"]
```

### 云服务器部署
1. 确保服务器有足够内存（推荐4GB+）
2. 安装必要的系统依赖
3. 配置防火墙开放3001端口
4. 使用PM2管理进程

## 监控和维护

### 健康检查
```bash
# 定期检查服务器状态
*/5 * * * * curl -f http://127.0.0.1:3001/health || systemctl restart midscene
```

### 日志管理
```bash
# 日志轮转
logrotate /var/log/midscene.log
```

## 支持和帮助

- 官方文档: https://midscenejs.com
- GitHub仓库: https://github.com/web-infra-dev/midscene
- 问题反馈: 在项目Issues中提交

---

配置完成后，您的Intent Test Framework将具备真实的AI驱动测试执行能力！
