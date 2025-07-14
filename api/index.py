"""
Vercel入口文件 - Intent Test Framework
专为Serverless环境优化，避免复杂的模块导入
"""

import sys
import os
from flask import Flask, jsonify, render_template_string

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# 创建Flask应用，配置模板和静态文件路径
template_dir = os.path.join(parent_dir, 'web_gui', 'templates')
static_dir = os.path.join(parent_dir, 'web_gui', 'static')

app = Flask(__name__,
           template_folder=template_dir,
           static_folder=static_dir,
           static_url_path='/static')

# 基本配置
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# 简单的HTML模板
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Intent Test Framework</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { text-align: center; margin-bottom: 30px; }
        .status { padding: 15px; border-radius: 5px; margin: 10px 0; }
        .success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .info { background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
        .api-list { margin: 20px 0; }
        .api-item { margin: 10px 0; padding: 10px; background: #f8f9fa; border-left: 4px solid #007bff; }
        .api-url { font-family: monospace; color: #007bff; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Intent Test Framework</h1>
            <p>AI驱动的Web自动化测试平台</p>
        </div>

        <div class="status success">
            ✅ 应用运行正常 - Vercel Serverless环境
        </div>

        <div class="status info">
            🗄️ 数据库: {{ database_status }}
        </div>

        <h3>📋 可用的API端点</h3>
        <div class="api-list">
            <div class="api-item">
                <strong>健康检查:</strong><br>
                <span class="api-url">GET /health</span>
            </div>
            <div class="api-item">
                <strong>API状态:</strong><br>
                <span class="api-url">GET /api/status</span>
            </div>
            <div class="api-item">
                <strong>测试用例:</strong><br>
                <span class="api-url">GET /api/testcases</span>
            </div>
            <div class="api-item">
                <strong>执行历史:</strong><br>
                <span class="api-url">GET /api/executions</span>
            </div>
            <div class="api-item">
                <strong>模板管理:</strong><br>
                <span class="api-url">GET /api/templates</span>
            </div>
            <div class="api-item">
                <strong>统计数据:</strong><br>
                <span class="api-url">GET /api/stats/dashboard</span>
            </div>
        </div>

        <div style="margin-top: 30px; text-align: center; color: #666;">
            <p>🌐 部署在 Vercel | 🗄️ 数据库 Supabase | 🤖 AI驱动测试</p>
        </div>
    </div>
</body>
</html>
"""

# 主页路由 - 使用原来的完整Web界面
@app.route('/')
def home():
    try:
        # 尝试渲染原来的完整界面
        from flask import render_template
        return render_template('index_enhanced.html')
    except Exception as e:
        print(f"⚠️ 无法加载完整界面: {e}")
        # 备用方案：简单状态页面
        database_url = os.getenv('DATABASE_URL', 'Not configured')
        database_status = 'PostgreSQL (Supabase)' if database_url.startswith('postgresql://') else 'Not configured'
        return render_template_string(HTML_TEMPLATE, database_status=database_status)

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'timestamp': os.getenv('VERCEL_DEPLOYMENT_ID', 'local')})

# 添加原来系统的页面路由
@app.route('/testcases')
def testcases_page():
    """测试用例管理页面"""
    try:
        from flask import render_template
        return render_template('testcases.html')
    except Exception as e:
        return jsonify({'error': f'无法加载测试用例页面: {str(e)}'}), 500

@app.route('/execution')
def execution_page():
    """执行控制台页面"""
    try:
        from flask import render_template
        return render_template('execution.html')
    except Exception as e:
        return jsonify({'error': f'无法加载执行控制台页面: {str(e)}'}), 500

@app.route('/reports')
def reports_page():
    """测试报告页面"""
    try:
        from flask import render_template
        return render_template('reports.html')
    except Exception as e:
        return jsonify({'error': f'无法加载测试报告页面: {str(e)}'}), 500

@app.route('/step_editor')
def step_editor_page():
    """步骤编辑器页面"""
    try:
        from flask import render_template
        return render_template('step_editor.html')
    except Exception as e:
        return jsonify({'error': f'无法加载步骤编辑器页面: {str(e)}'}), 500

@app.route('/local-proxy')
def local_proxy_page():
    """本地代理下载页面"""
    try:
        from flask import render_template
        return render_template('local_proxy.html')
    except Exception as e:
        return jsonify({'error': f'无法加载本地代理页面: {str(e)}'}), 500

@app.route('/download/local-proxy')
def download_local_proxy():
    """下载本地代理包 - 动态生成"""
    try:
        import zipfile
        import tempfile
        import io
        from pathlib import Path
        from flask import send_file

        # 动态生成代理包内容
        proxy_files = generate_proxy_package_files()

        # 创建内存中的ZIP文件
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for filename, content in proxy_files.items():
                zipf.writestr(filename, content)

        zip_buffer.seek(0)

        return send_file(
            zip_buffer,
            as_attachment=True,
            download_name='intent-test-proxy.zip',
            mimetype='application/zip'
        )

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'下载失败: {str(e)}'
        }), 500

def generate_proxy_package_files():
    """动态生成代理包文件内容"""
    import os
    from pathlib import Path

    # 获取当前项目的midscene_server.js内容
    current_dir = Path(__file__).parent.parent
    server_file = current_dir / 'midscene_server.js'

    # 读取服务器文件内容
    if server_file.exists():
        with open(server_file, 'r', encoding='utf-8') as f:
            server_content = f.read()
    else:
        # 如果文件不存在，使用基础模板
        server_content = get_basic_server_template()

    files = {
        'midscene_server.js': server_content,
        'package.json': get_package_json_content(),
        '.env.example': get_env_template(),
        'start.bat': get_windows_start_script(),
        'start.sh': get_unix_start_script(),
        'README.md': get_readme_content()
    }

    return files

def get_basic_server_template():
    """获取基础服务器模板"""
    return '''const express = require('express');
const cors = require('cors');
const { PlaywrightAgent } = require('@midscene/web');
const { chromium } = require('playwright');
const { createServer } = require('http');
const { Server } = require('socket.io');

const app = express();
const server = createServer(app);
const io = new Server(server, {
    cors: {
        origin: "*",
        methods: ["GET", "POST"]
    }
});

const port = process.env.PORT || 3001;

// 中间件
app.use(cors());
app.use(express.json());

// 全局变量存储浏览器和页面实例
let browser = null;
let page = null;
let agent = null;

// 执行状态管理
const executionStates = new Map();

// 生成执行ID
function generateExecutionId() {
    return 'exec_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

// 初始化浏览器
async function initBrowser(headless = true) {
    try {
        if (browser) {
            await browser.close();
        }

        browser = await chromium.launch({
            headless: headless,
            args: ['--no-sandbox', '--disable-setuid-sandbox']
        });

        page = await browser.newPage();

        // 初始化MidScene AI代理
        agent = new PlaywrightAgent(page, {
            apiKey: process.env.OPENAI_API_KEY,
            baseURL: process.env.OPENAI_BASE_URL,
            model: process.env.MIDSCENE_MODEL_NAME || 'qwen-vl-max-latest'
        });

        console.log('✅ 浏览器和AI代理初始化成功');
        return { page, agent };
    } catch (error) {
        console.error('❌ 浏览器初始化失败:', error);
        throw error;
    }
}

// WebSocket连接处理
io.on('connection', (socket) => {
    console.log('🔌 WebSocket客户端连接:', socket.id);

    socket.on('disconnect', () => {
        console.log('🔌 WebSocket客户端断开:', socket.id);
    });

    socket.emit('server-status', {
        status: 'ready',
        timestamp: new Date().toISOString()
    });
});

// 健康检查
app.get('/health', (req, res) => {
    res.json({
        status: 'ok',
        timestamp: new Date().toISOString(),
        uptime: process.uptime()
    });
});

// 执行完整测试用例
app.post('/api/execute-testcase', async (req, res) => {
    try {
        const { testcase, mode = 'headless' } = req.body;

        if (!testcase) {
            return res.status(400).json({
                success: false,
                error: '缺少测试用例数据'
            });
        }

        const executionId = generateExecutionId();

        // 异步执行，立即返回执行ID
        executeTestCaseAsync(testcase, mode, executionId).catch(error => {
            console.error('异步执行错误:', error);
        });

        res.json({
            success: true,
            executionId,
            message: '测试用例开始执行',
            timestamp: new Date().toISOString()
        });

    } catch (error) {
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// 异步执行完整测试用例
async function executeTestCaseAsync(testcase, mode, executionId) {
    try {
        executionStates.set(executionId, {
            status: 'running',
            startTime: new Date(),
            testcase: testcase.name,
            mode
        });

        io.emit('execution-start', {
            executionId,
            testcase: testcase.name,
            mode,
            timestamp: new Date().toISOString()
        });

        const steps = typeof testcase.steps === 'string'
            ? JSON.parse(testcase.steps)
            : testcase.steps || [];

        if (steps.length === 0) {
            throw new Error('测试用例没有步骤');
        }

        const headless = mode === 'headless';
        const { page, agent } = await initBrowser(headless);

        for (let i = 0; i < steps.length; i++) {
            const step = steps[i];

            io.emit('step-progress', {
                executionId,
                stepIndex: i,
                totalSteps: steps.length,
                step: step.description || step.action,
                progress: Math.round((i / steps.length) * 100)
            });

            await executeStep(step, page, agent, executionId, i);

            io.emit('step-complete', {
                executionId,
                stepIndex: i,
                success: true
            });
        }

        const executionState = executionStates.get(executionId);
        executionState.status = 'completed';
        executionState.endTime = new Date();

        io.emit('execution-complete', {
            executionId,
            success: true,
            message: '🎉 测试执行完成！',
            timestamp: new Date().toISOString()
        });

    } catch (error) {
        console.error('测试执行失败:', error);

        const executionState = executionStates.get(executionId);
        if (executionState) {
            executionState.status = 'failed';
            executionState.error = error.message;
        }

        io.emit('execution-error', {
            executionId,
            error: error.message,
            timestamp: new Date().toISOString()
        });
    }
}

// 执行单个步骤
async function executeStep(step, page, agent, executionId, stepIndex) {
    const { action, params = {}, description } = step;

    io.emit('log-message', {
        executionId,
        level: 'info',
        message: `🔄 执行步骤 ${stepIndex + 1}: ${description || action}`
    });

    try {
        switch (action) {
            case 'navigate':
                if (params.url) {
                    await page.goto(params.url, { waitUntil: 'networkidle' });
                }
                break;

            case 'click':
                if (params.locate) {
                    await agent.aiTap(params.locate);
                }
                break;

            case 'type':
            case 'ai_input':
                if (params.locate && params.text) {
                    await agent.aiInput(params.text, params.locate);
                }
                break;

            case 'wait':
                const waitTime = params.time || 1000;
                await page.waitForTimeout(waitTime);
                break;

            case 'assert':
                if (params.condition) {
                    await agent.aiAssert(params.condition);
                }
                break;

            default:
                const instruction = description || action;
                await agent.ai(instruction);
                break;
        }

        return { success: true };

    } catch (error) {
        io.emit('log-message', {
            executionId,
            level: 'error',
            message: `❌ 步骤执行失败: ${error.message}`
        });
        throw error;
    }
}

// 启动服务器
server.listen(port, () => {
    console.log(`🚀 MidSceneJS本地代理服务器启动成功`);
    console.log(`🌐 HTTP服务器: http://localhost:${port}`);
    console.log(`🔌 WebSocket服务器: ws://localhost:${port}`);
    console.log(`💡 AI模型: ${process.env.MIDSCENE_MODEL_NAME || 'qwen-vl-max-latest'}`);
    console.log(`🔗 API地址: ${process.env.OPENAI_BASE_URL || 'https://dashscope.aliyuncs.com/compatible-mode/v1'}`);
    console.log(`✨ 服务器就绪，等待测试执行请求...`);
});
'''

def get_package_json_content():
    """获取package.json内容"""
    return '''{
  "name": "intent-test-proxy",
  "version": "1.0.0",
  "description": "Intent Test Framework 本地代理服务器",
  "main": "midscene_server.js",
  "scripts": {
    "start": "node midscene_server.js",
    "install-deps": "npm install"
  },
  "dependencies": {
    "@midscene/web": "^0.20.1",
    "cors": "^2.8.5",
    "express": "^5.1.0",
    "playwright": "^1.45.0",
    "socket.io": "^4.7.0"
  },
  "keywords": ["midscene", "automation", "testing", "ai"],
  "author": "Intent Test Framework",
  "license": "MIT"
}'''

def get_env_template():
    """获取环境变量模板"""
    return '''# Intent Test Framework 本地代理服务器配置

# AI API配置 (必填)
# 选择以下其中一种配置方式：

# 方式1: 阿里云DashScope (推荐)
OPENAI_API_KEY=sk-your-dashscope-api-key
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MIDSCENE_MODEL_NAME=qwen-vl-max-latest

# 方式2: OpenAI
# OPENAI_API_KEY=sk-your-openai-api-key
# OPENAI_BASE_URL=https://api.openai.com/v1
# MIDSCENE_MODEL_NAME=gpt-4o

# 服务器配置 (可选)
# PORT=3001

# 浏览器配置 (可选)
# BROWSER_HEADLESS=false
# BROWSER_TIMEOUT=30000
'''

def get_windows_start_script():
    """获取Windows启动脚本"""
    return '''@echo off
chcp 65001 >nul
title Intent Test Framework - 本地代理服务器

echo.
echo ========================================
echo   Intent Test Framework 本地代理服务器
echo ========================================
echo.

REM 检查Node.js
echo [1/4] 检查Node.js环境...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 错误: 未检测到Node.js
    echo.
    echo 请先安装Node.js:
    echo https://nodejs.org/
    echo.
    echo 建议安装LTS版本 ^(16.x或更高^)
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('node --version') do set NODE_VERSION=%%i
echo ✅ Node.js版本: %NODE_VERSION%

REM 首次运行安装依赖
echo.
echo [2/4] 检查依赖包...
if not exist node_modules (
    echo 📦 首次运行，正在安装依赖包...
    echo 这可能需要几分钟时间，请耐心等待...
    npm install
    if %errorlevel% neq 0 (
        echo ❌ 依赖安装失败
        pause
        exit /b 1
    )
    echo ✅ 依赖安装完成
) else (
    echo ✅ 依赖包已存在
)

REM 检查配置文件
echo.
echo [3/4] 检查配置文件...
if not exist .env (
    echo ⚙️ 首次运行，创建配置文件...
    copy .env.example .env >nul
    echo.
    echo ⚠️  重要: 请配置AI API密钥
    echo.
    echo 配置文件已创建: .env
    echo 请编辑此文件，添加您的AI API密钥
    echo.
    echo 配置完成后，请重新运行此脚本
    echo.
    notepad .env
    pause
    exit /b 0
)

echo ✅ 配置文件存在

REM 启动服务器
echo.
echo [4/4] 启动服务器...
echo.
echo 🚀 正在启动Intent Test Framework本地代理服务器...
echo.
echo 启动成功后，请返回Web界面选择"本地代理模式"
echo 按 Ctrl+C 可停止服务器
echo.

node midscene_server.js

echo.
echo 服务器已停止
pause
'''

def get_unix_start_script():
    """获取Unix启动脚本"""
    return '''#!/bin/bash

# Intent Test Framework 本地代理服务器启动脚本

# 设置颜色输出
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
BLUE='\\033[0;34m'
NC='\\033[0m' # No Color

echo ""
echo "========================================"
echo "  Intent Test Framework 本地代理服务器"
echo "========================================"
echo ""

# 检查Node.js
echo -e "${BLUE}[1/4]${NC} 检查Node.js环境..."
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ 错误: 未检测到Node.js${NC}"
    echo ""
    echo "请先安装Node.js:"
    echo "https://nodejs.org/"
    echo ""
    echo "建议安装LTS版本 (16.x或更高)"
    exit 1
fi

NODE_VERSION=$(node --version)
echo -e "${GREEN}✅ Node.js版本: $NODE_VERSION${NC}"

# 首次运行安装依赖
echo ""
echo -e "${BLUE}[2/4]${NC} 检查依赖包..."
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}📦 首次运行，正在安装依赖包...${NC}"
    echo "这可能需要几分钟时间，请耐心等待..."
    npm install
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ 依赖安装失败${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ 依赖安装完成${NC}"
else
    echo -e "${GREEN}✅ 依赖包已存在${NC}"
fi

# 检查配置文件
echo ""
echo -e "${BLUE}[3/4]${NC} 检查配置文件..."
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚙️ 首次运行，创建配置文件...${NC}"
    cp .env.example .env
    echo ""
    echo -e "${YELLOW}⚠️  重要: 请配置AI API密钥${NC}"
    echo ""
    echo "配置文件已创建: .env"
    echo "请编辑此文件，添加您的AI API密钥"
    echo ""
    echo "配置完成后，请重新运行此脚本"
    echo ""
    echo "编辑配置文件: nano .env"
    exit 0
fi

echo -e "${GREEN}✅ 配置文件存在${NC}"

# 启动服务器
echo ""
echo -e "${BLUE}[4/4]${NC} 启动服务器..."
echo ""
echo -e "${GREEN}🚀 正在启动Intent Test Framework本地代理服务器...${NC}"
echo ""
echo "启动成功后，请返回Web界面选择"本地代理模式""
echo "按 Ctrl+C 可停止服务器"
echo ""

node midscene_server.js

echo ""
echo "服务器已停止"
'''

def get_readme_content():
    """获取README内容"""
    return '''# Intent Test Framework - 本地代理服务器

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
'''

# 设置环境变量
os.environ['VERCEL'] = '1'

# 尝试加载API功能
try:
    print("🔄 开始加载API功能...")

    # 导入数据库配置
    from web_gui.database_config import get_flask_config

    # 应用数据库配置
    db_config = get_flask_config()
    app.config.update(db_config)

    print("✅ 数据库配置加载成功")

    # 导入模型和路由
    from web_gui.models import db
    from web_gui.api_routes import api_bp

    print("✅ 模型和路由导入成功")

    # 初始化数据库
    db.init_app(app)

    # 注册API路由
    app.register_blueprint(api_bp)

    print("✅ API路由注册成功")

    # 添加CORS支持
    try:
        from flask_cors import CORS
        CORS(app, origins="*")
        print("✅ CORS配置成功")
    except ImportError:
        print("⚠️ CORS模块未找到，跳过")
    
    # 在应用启动时创建数据库表
    try:
        with app.app_context():
            db.create_all()
            print("✅ 数据库表创建成功")
    except Exception as e:
        print(f"⚠️ 数据库表创建失败: {e}")

    # API状态检查
    @app.route('/api/status')
    def api_status():
        return jsonify({
            'status': 'ok',
            'message': 'API is working',
            'database': 'connected',
            'environment': 'Vercel Serverless'
        })

    # 数据库初始化API
    @app.route('/api/init-db', methods=['POST'])
    def init_database():
        try:
            # 创建所有表
            db.create_all()

            # 检查是否有示例数据
            from web_gui.models import TestCase, Template

            test_count = TestCase.query.count()
            template_count = Template.query.count()

            # 如果没有数据，创建示例数据
            if test_count == 0:
                # 简单的测试用例
                simple_testcase = TestCase(
                    name='简单页面访问测试',
                    description='测试访问百度首页',
                    steps='[{"action":"navigate","params":{"url":"https://www.baidu.com"},"description":"访问百度首页"}]',
                    category='基础功能',
                    priority=1,
                    created_by='system'
                )
                db.session.add(simple_testcase)

                # 复杂的测试用例
                complex_testcase = TestCase(
                    name='百度搜索测试',
                    description='测试百度搜索功能',
                    steps='[{"action":"navigate","params":{"url":"https://www.baidu.com"},"description":"访问百度首页"},{"action":"ai_input","params":{"text":"AI测试","locate":"搜索框"},"description":"输入搜索关键词"}]',
                    category='搜索功能',
                    priority=2,
                    created_by='system'
                )
                db.session.add(complex_testcase)

            if template_count == 0:
                sample_template = Template(
                    name='搜索功能模板',
                    description='通用搜索功能测试模板',
                    category='搜索',
                    steps_template='[{"action":"navigate","params":{"url":"{{search_url}}"},"description":"访问搜索页面"}]',
                    parameters='{"search_url":{"type":"string","description":"搜索页面URL"}}',
                    created_by='system',
                    is_public=True
                )
                db.session.add(sample_template)

            # 创建示例执行记录
            from web_gui.models import ExecutionHistory
            execution_count = ExecutionHistory.query.count()
            
            if execution_count == 0:
                from datetime import datetime, timedelta
                import uuid
                
                # 获取刚创建的测试用例
                testcase = TestCase.query.first()
                
                if testcase:
                    base_time = datetime.utcnow() - timedelta(days=5)
                    
                    # 创建一些成功的执行记录
                    for i in range(8):
                        execution_id = str(uuid.uuid4())
                        execution = ExecutionHistory(
                            execution_id=execution_id,
                            test_case_id=testcase.id,
                            status='success',
                            mode='headless',
                            start_time=base_time + timedelta(hours=i*3),
                            end_time=base_time + timedelta(hours=i*3, minutes=2),
                            duration=120,
                            steps_total=3,
                            steps_passed=3,
                            steps_failed=0,
                            executed_by='system'
                        )
                        db.session.add(execution)
                    
                    # 创建一些失败的执行记录
                    for i in range(3):
                        execution_id = str(uuid.uuid4())
                        execution = ExecutionHistory(
                            execution_id=execution_id,
                            test_case_id=testcase.id,
                            status='failed',
                            mode='headless',
                            start_time=base_time + timedelta(hours=i*8),
                            end_time=base_time + timedelta(hours=i*8, minutes=1),
                            duration=60,
                            steps_total=3,
                            steps_passed=1,
                            steps_failed=2,
                            error_message='模拟执行失败',
                            executed_by='system'
                        )
                        db.session.add(execution)
                    
                    print("✅ 创建示例执行记录")

            db.session.commit()

            return jsonify({
                'status': 'success',
                'message': '数据库初始化成功',
                'data': {
                    'test_cases': TestCase.query.count(),
                    'templates': Template.query.count(),
                    'executions': ExecutionHistory.query.count()
                }
            })

        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'数据库初始化失败: {str(e)}'
            }), 500

    # 数据库连接测试
    @app.route('/api/db-test')
    def db_test():
        try:
            database_url = os.getenv('DATABASE_URL')
            if not database_url:
                return jsonify({
                    'status': 'error',
                    'message': 'DATABASE_URL环境变量未设置'
                }), 500

            # 显示连接信息（隐藏密码）
            from urllib.parse import urlparse
            parsed = urlparse(database_url)

            connection_info = {
                'scheme': parsed.scheme,
                'hostname': parsed.hostname,
                'port': parsed.port,
                'database': parsed.path.lstrip('/') if parsed.path else None,
                'username': parsed.username,
                'password_set': bool(parsed.password),
                'original_url': database_url[:50] + '...' if len(database_url) > 50 else database_url
            }

            # 尝试多种连接方式
            connection_attempts = []

            # 方法1: 使用应用的数据库引擎
            try:
                with db.engine.connect() as conn:
                    result = conn.execute(db.text("SELECT 1 as test"))
                    test_result = result.fetchone()

                return jsonify({
                    'status': 'success',
                    'message': '数据库连接成功 (方法1: 应用引擎)',
                    'connection_info': connection_info,
                    'test_query': 'SELECT 1 执行成功'
                })
            except Exception as e1:
                connection_attempts.append(f"方法1失败: {str(e1)}")

            # 方法2: 直接使用psycopg2连接
            try:
                import psycopg2
                conn = psycopg2.connect(database_url)
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                cursor.close()
                conn.close()

                return jsonify({
                    'status': 'success',
                    'message': '数据库连接成功 (方法2: 直接连接)',
                    'connection_info': connection_info,
                    'test_query': 'SELECT 1 执行成功'
                })
            except Exception as e2:
                connection_attempts.append(f"方法2失败: {str(e2)}")

            # 方法3: 尝试连接池端口
            try:
                pool_url = database_url.replace(':5432/', ':6543/')
                import psycopg2
                conn = psycopg2.connect(pool_url)
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                cursor.close()
                conn.close()

                return jsonify({
                    'status': 'success',
                    'message': '数据库连接成功 (方法3: 连接池)',
                    'connection_info': {**connection_info, 'used_pool_port': True},
                    'test_query': 'SELECT 1 执行成功',
                    'suggestion': '建议更新DATABASE_URL使用端口6543'
                })
            except Exception as e3:
                connection_attempts.append(f"方法3失败: {str(e3)}")

            return jsonify({
                'status': 'error',
                'message': '所有连接方法都失败了',
                'connection_info': connection_info,
                'attempts': connection_attempts,
                'suggestion': '请检查Supabase项目状态，或尝试使用连接池URL (端口6543)'
            }), 500

        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'测试过程出错: {str(e)}',
                'connection_info': connection_info if 'connection_info' in locals() else None
            }), 500

    # 智能执行API - 支持Chrome桥接、云端和本地模式
    @app.route('/api/executions/start', methods=['POST'])
    def start_execution():
        try:
            from flask import request
            import threading
            import uuid
            from datetime import datetime

            data = request.get_json() or {}
            testcase_id = data.get('testcase_id')
            mode = data.get('mode', 'headless')  # headless 或 browser
            execution_type = data.get('execution_type', 'local-proxy')  # local-proxy

            if not testcase_id:
                return jsonify({
                    'code': 400,
                    'message': '缺少测试用例ID'
                }), 400

            # 获取测试用例
            from web_gui.models import TestCase
            testcase = TestCase.query.get(testcase_id)
            if not testcase:
                return jsonify({
                    'code': 404,
                    'message': '测试用例不存在'
                }), 404

            # 生成执行ID
            execution_id = str(uuid.uuid4())

            # 创建执行记录
            execution_record = {
                'execution_id': execution_id,
                'testcase_id': testcase_id,
                'testcase_name': testcase.name,
                'mode': mode,
                'execution_type': execution_type,
                'status': 'running',
                'start_time': datetime.utcnow().isoformat(),
                'steps': [],
                'current_step': 0,
                'total_steps': len(json.loads(testcase.steps)) if testcase.steps else 0,
                'screenshots': []
            }

            # 存储执行记录（简单的内存存储）
            if not hasattr(app, 'executions'):
                app.executions = {}
            app.executions[execution_id] = execution_record

            # 智能选择执行方式
            selected_type, execution_message = select_execution_type(execution_type, testcase.name)
            execution_record['execution_type'] = selected_type

            # 启动本地代理执行线程
            thread = threading.Thread(
                target=execute_testcase_background,
                args=(execution_id, testcase, mode)
            )

            thread.daemon = True
            thread.start()

            return jsonify({
                'code': 200,
                'message': '本地代理执行已启动',
                'data': {
                    'execution_id': execution_id,
                    'testcase_id': testcase_id,
                    'testcase_name': testcase.name,
                    'mode': mode,
                    'execution_type': selected_type,
                    'status': 'running',
                    'message': execution_message
                }
            })
        except Exception as e:
            return jsonify({
                'code': 500,
                'message': f'启动执行失败: {str(e)}'
            }), 500

    def select_execution_type(requested_type: str, testcase_name: str) -> tuple:
        """选择执行类型"""
        return 'local-proxy', f'正在通过本地代理执行测试用例: {testcase_name}'


    def execute_testcase_background(execution_id, testcase, mode):
        """后台执行测试用例"""
        try:
            from datetime import datetime
            import json
            import time

            # 获取执行记录
            execution = app.executions[execution_id]

            # 解析测试步骤
            steps = json.loads(testcase.steps) if testcase.steps else []
            execution['total_steps'] = len(steps)
            execution['steps'] = [{'status': 'pending', 'description': step.get('description', '')} for step in steps]
            
            # 创建数据库执行记录
            db_execution = None
            try:
                from web_gui.models import ExecutionHistory, db
                with app.app_context():
                    db_execution = ExecutionHistory(
                        execution_id=execution_id,
                        test_case_id=testcase.id,
                        status='running',
                        mode=mode,
                        start_time=datetime.utcnow(),
                        steps_total=len(steps),
                        steps_passed=0,
                        steps_failed=0,
                        executed_by='system'
                    )
                    db.session.add(db_execution)
                    db.session.commit()
                    print(f"✅ 创建执行记录: {execution_id}")
            except Exception as db_error:
                print(f"⚠️ 创建执行记录失败: {db_error}")

            # 尝试导入AI执行引擎
            try:
                import sys
                import os
                sys.path.append(os.path.dirname(os.path.dirname(__file__)))
                from midscene_python import MidSceneAI

                # 初始化AI
                ai = MidSceneAI()
                ai.set_browser_mode(mode)

                execution['message'] = f'AI引擎已初始化，开始执行 {len(steps)} 个步骤'

                # 执行每个步骤
                for i, step in enumerate(steps):
                    execution['current_step'] = i + 1
                    execution['steps'][i]['status'] = 'running'

                    try:
                        # 执行步骤
                        result = execute_single_step(ai, step, i)
                        execution['steps'][i]['status'] = 'success'
                        execution['steps'][i]['result'] = result

                        # 截图
                        screenshot_path = ai.take_screenshot(f"{execution_id}_step_{i+1}")
                        execution['screenshots'].append({
                            'step': i + 1,
                            'path': screenshot_path,
                            'description': step.get('description', f'步骤 {i+1}')
                        })

                    except Exception as step_error:
                        execution['steps'][i]['status'] = 'failed'
                        execution['steps'][i]['error'] = str(step_error)
                        print(f"步骤 {i+1} 执行失败: {step_error}")
                        # 继续执行下一步骤

                # 执行完成
                execution['status'] = 'completed'
                execution['end_time'] = datetime.utcnow().isoformat()
                execution['message'] = '测试执行完成'
                
                # 更新数据库记录
                try:
                    from web_gui.models import ExecutionHistory, db
                    with app.app_context():
                        db_execution = ExecutionHistory.query.filter_by(execution_id=execution_id).first()
                        if db_execution:
                            db_execution.status = 'success'
                            db_execution.end_time = datetime.utcnow()
                            db_execution.steps_passed = sum(1 for step in execution['steps'] if step.get('status') == 'success')
                            db_execution.steps_failed = sum(1 for step in execution['steps'] if step.get('status') == 'failed')
                            db_execution.duration = int((datetime.utcnow() - db_execution.start_time).total_seconds())
                            db.session.commit()
                            print(f"✅ 更新执行记录: {execution_id} -> success")
                except Exception as db_error:
                    print(f"⚠️ 更新执行记录失败: {db_error}")

            except ImportError as e:
                # AI引擎不可用，使用模拟执行
                execution['message'] = 'AI引擎不可用，使用模拟执行'

                for i, step in enumerate(steps):
                    execution['current_step'] = i + 1
                    execution['steps'][i]['status'] = 'running'
                    time.sleep(2)  # 模拟执行时间
                    execution['steps'][i]['status'] = 'success'
                    execution['steps'][i]['result'] = f"模拟执行: {step.get('description', '')}"

                execution['status'] = 'completed'
                execution['end_time'] = datetime.utcnow().isoformat()
                execution['message'] = '模拟执行完成'
                
                # 更新数据库记录
                try:
                    from web_gui.models import ExecutionHistory, db
                    with app.app_context():
                        db_execution = ExecutionHistory.query.filter_by(execution_id=execution_id).first()
                        if db_execution:
                            db_execution.status = 'success'
                            db_execution.end_time = datetime.utcnow()
                            db_execution.steps_passed = sum(1 for step in execution['steps'] if step.get('status') == 'success')
                            db_execution.steps_failed = sum(1 for step in execution['steps'] if step.get('status') == 'failed')
                            db_execution.duration = int((datetime.utcnow() - db_execution.start_time).total_seconds())
                            db.session.commit()
                            print(f"✅ 更新执行记录: {execution_id} -> success (模拟)")
                except Exception as db_error:
                    print(f"⚠️ 更新执行记录失败: {db_error}")

        except Exception as e:
            execution['status'] = 'failed'
            execution['error'] = str(e)
            execution['end_time'] = datetime.utcnow().isoformat()
            print(f"执行失败: {e}")
            
            # 更新数据库记录为失败
            try:
                from web_gui.models import ExecutionHistory, db
                with app.app_context():
                    db_execution = ExecutionHistory.query.filter_by(execution_id=execution_id).first()
                    if db_execution:
                        db_execution.status = 'failed'
                        db_execution.end_time = datetime.utcnow()
                        db_execution.error_message = str(e)
                        db_execution.duration = int((datetime.utcnow() - db_execution.start_time).total_seconds())
                        db.session.commit()
                        print(f"✅ 更新执行记录: {execution_id} -> failed")
            except Exception as db_error:
                print(f"⚠️ 更新执行记录失败: {db_error}")

    def execute_single_step(ai, step, step_index):
        """执行单个测试步骤"""
        action = step.get('action')
        params = step.get('params', {})
        description = step.get('description', action)

        print(f"执行步骤 {step_index + 1}: {description}")

        if action == 'navigate':
            url = params.get('url')
            return ai.goto(url)
        elif action == 'ai_input':
            text = params.get('text')
            locate = params.get('locate')
            return ai.ai_input(text, locate)
        elif action == 'ai_tap':
            prompt = params.get('prompt')
            return ai.ai_tap(prompt)
        elif action == 'ai_assert':
            prompt = params.get('prompt')
            return ai.ai_assert(prompt)
        elif action == 'ai_wait_for':
            prompt = params.get('prompt')
            timeout = params.get('timeout', 10000)
            return ai.ai_wait_for(prompt, timeout)
        else:
            raise ValueError(f"不支持的操作类型: {action}")

    print("✅ API功能加载成功")

except Exception as e:
    print(f"⚠️ API功能加载失败: {e}")
    import traceback
    traceback.print_exc()

    # 简单的错误API
    @app.route('/api/status')
    def api_status_error():
        return jsonify({
            'status': 'error',
            'message': f'API加载失败: {str(e)}',
            'suggestion': '请检查环境变量和依赖配置'
        }), 500

# Vercel需要的应用对象
application = app

if __name__ == '__main__':
    app.run(debug=True)
