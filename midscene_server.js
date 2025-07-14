/**
 * MidSceneJS HTTP API服务器
 * 提供AI功能的HTTP接口供Python调用
 */

const express = require('express');
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

const port = 3001;

// 中间件
app.use(cors());
app.use(express.json({ limit: '50mb' }));

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

// 启动浏览器和页面
async function initBrowser(headless = true) {
    if (!browser) {
        console.log(`🚀 启动浏览器 - 模式: ${headless ? '无头模式' : '浏览器模式'}`);
        browser = await chromium.launch({
            headless: headless,
            args: ['--no-sandbox', '--disable-setuid-sandbox']
        });
    }
    
    if (!page) {
        const context = await browser.newContext({
            viewport: { width: 1280, height: 720 },
            deviceScaleFactor: 1
        });
        page = await context.newPage();
        
        // 配置MidSceneJS AI
        const config = {
            modelName: process.env.MIDSCENE_MODEL_NAME || 'qwen-vl-max-latest',
            apiKey: process.env.OPENAI_API_KEY,
            baseUrl: process.env.OPENAI_BASE_URL || 'https://dashscope.aliyuncs.com/compatible-mode/v1'
        };
        
        console.log('🤖 初始化MidSceneJS AI配置:', {
            modelName: config.modelName,
            baseUrl: config.baseUrl,
            hasApiKey: !!config.apiKey
        });
        
        agent = new PlaywrightAgent(page, { 
            aiModel: config 
        });
    }
    
    return { page, agent };
}

// WebSocket连接处理
io.on('connection', (socket) => {
    console.log('🔌 WebSocket客户端连接:', socket.id);

    socket.on('disconnect', () => {
        console.log('🔌 WebSocket客户端断开:', socket.id);
    });

    // 发送服务器状态
    socket.emit('server-status', {
        status: 'ready',
        timestamp: new Date().toISOString()
    });
});

// 执行单个步骤
async function executeStep(step, page, agent, executionId, stepIndex) {
    const { action, params = {}, description } = step;

    // 发送步骤开始事件
    io.emit('step-start', {
        executionId,
        stepIndex,
        action,
        description: description || action
    });

    try {
        switch (action) {
            case 'navigate':
                if (params.url) {
                    await page.goto(params.url, { waitUntil: 'networkidle', timeout: 60000 });
                    io.emit('log-message', {
                        executionId,
                        level: 'info',
                        message: `🔗 导航到: ${params.url}`
                    });
                }
                break;

            case 'click':
                if (params.locate) {
                    await agent.aiTap(params.locate);
                    io.emit('log-message', {
                        executionId,
                        level: 'info',
                        message: `👆 点击: ${params.locate}`
                    });
                }
                break;

            case 'type':
            case 'ai_input':
                if (params.locate && params.text) {
                    await agent.aiInput(params.text, params.locate);
                    io.emit('log-message', {
                        executionId,
                        level: 'info',
                        message: `⌨️ 输入: "${params.text}" 到 ${params.locate}`
                    });
                }
                break;

            case 'wait':
                const waitTime = params.time || 1000;
                await page.waitForTimeout(waitTime);
                io.emit('log-message', {
                    executionId,
                    level: 'info',
                    message: `⏱️ 等待: ${waitTime}ms`
                });
                break;

            case 'assert':
                if (params.condition) {
                    await agent.aiAssert(params.condition);
                    io.emit('log-message', {
                        executionId,
                        level: 'info',
                        message: `✅ 断言: ${params.condition}`
                    });
                }
                break;

            default:
                // 通用AI操作
                const instruction = description || action;
                await agent.ai(instruction);
                io.emit('log-message', {
                    executionId,
                    level: 'info',
                    message: `🤖 AI操作: ${instruction}`
                });
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

// 异步执行完整测试用例
async function executeTestCaseAsync(testcase, mode, executionId) {
    try {
        // 更新执行状态
        executionStates.set(executionId, {
            status: 'running',
            startTime: new Date(),
            testcase: testcase.name,
            mode
        });

        // 发送执行开始事件
        io.emit('execution-start', {
            executionId,
            testcase: testcase.name,
            mode,
            timestamp: new Date().toISOString()
        });

        io.emit('log-message', {
            executionId,
            level: 'info',
            message: `🚀 开始执行测试用例: ${testcase.name}`
        });

        // 解析测试步骤
        let steps;
        try {
            steps = typeof testcase.steps === 'string'
                ? JSON.parse(testcase.steps)
                : testcase.steps || [];
        } catch (parseError) {
            throw new Error(`步骤解析失败: ${parseError.message}`);
        }

        if (steps.length === 0) {
            throw new Error('测试用例没有步骤');
        }

        io.emit('log-message', {
            executionId,
            level: 'info',
            message: `📋 共 ${steps.length} 个步骤`
        });

        // 初始化浏览器
        const headless = mode === 'headless';
        io.emit('log-message', {
            executionId,
            level: 'info',
            message: `🌐 初始化浏览器 (${headless ? '无头模式' : '可视模式'})`
        });

        const { page, agent } = await initBrowser(headless);

        // 执行每个步骤
        for (let i = 0; i < steps.length; i++) {
            const step = steps[i];

            // 发送步骤进度
            io.emit('step-progress', {
                executionId,
                stepIndex: i,
                totalSteps: steps.length,
                step: step.description || step.action,
                progress: Math.round((i / steps.length) * 100)
            });

            // 执行步骤
            await executeStep(step, page, agent, executionId, i);

            // 截图
            try {
                const screenshot = await page.screenshot({
                    fullPage: false,
                    type: 'png'
                });

                io.emit('screenshot-taken', {
                    executionId,
                    stepIndex: i,
                    screenshot: screenshot.toString('base64'),
                    timestamp: new Date().toISOString()
                });
            } catch (screenshotError) {
                console.warn('截图失败:', screenshotError.message);
            }

            // 发送步骤完成事件
            io.emit('step-complete', {
                executionId,
                stepIndex: i,
                success: true
            });

            // 短暂延迟，让用户看到执行过程
            await page.waitForTimeout(500);
        }

        // 更新执行状态
        const executionState = executionStates.get(executionId);
        executionState.status = 'completed';
        executionState.endTime = new Date();
        executionState.duration = executionState.endTime - executionState.startTime;

        // 发送执行完成事件
        io.emit('execution-complete', {
            executionId,
            success: true,
            message: '🎉 测试执行完成！',
            duration: executionState.duration,
            timestamp: new Date().toISOString()
        });

        io.emit('log-message', {
            executionId,
            level: 'success',
            message: `🎉 测试执行完成！耗时: ${Math.round(executionState.duration / 1000)}秒`
        });

    } catch (error) {
        console.error('测试执行失败:', error);

        // 更新执行状态
        const executionState = executionStates.get(executionId);
        if (executionState) {
            executionState.status = 'failed';
            executionState.endTime = new Date();
            executionState.error = error.message;
        }

        // 发送执行错误事件
        io.emit('execution-error', {
            executionId,
            error: error.message,
            timestamp: new Date().toISOString()
        });

        io.emit('log-message', {
            executionId,
            level: 'error',
            message: `❌ 测试执行失败: ${error.message}`
        });
    }
}

// API端点

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

// 获取执行状态
app.get('/api/execution-status/:executionId', (req, res) => {
    const { executionId } = req.params;
    const executionState = executionStates.get(executionId);

    if (!executionState) {
        return res.status(404).json({
            success: false,
            error: '执行记录不存在'
        });
    }

    res.json({
        success: true,
        executionId,
        ...executionState
    });
});

// 停止执行
app.post('/api/stop-execution/:executionId', async (req, res) => {
    const { executionId } = req.params;
    const executionState = executionStates.get(executionId);

    if (!executionState) {
        return res.status(404).json({
            success: false,
            error: '执行记录不存在'
        });
    }

    if (executionState.status !== 'running') {
        return res.json({
            success: true,
            message: '执行已结束'
        });
    }

    try {
        // 更新状态为已停止
        executionState.status = 'stopped';
        executionState.endTime = new Date();

        // 发送停止事件
        io.emit('execution-stopped', {
            executionId,
            timestamp: new Date().toISOString()
        });

        io.emit('log-message', {
            executionId,
            level: 'warning',
            message: '⏹️ 执行已被用户停止'
        });

        res.json({
            success: true,
            message: '执行已停止'
        });

    } catch (error) {
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// 获取服务器状态
app.get('/api/status', (req, res) => {
    const runningExecutions = Array.from(executionStates.values())
        .filter(state => state.status === 'running');

    res.json({
        success: true,
        status: 'ready',
        browserInitialized: !!browser,
        runningExecutions: runningExecutions.length,
        totalExecutions: executionStates.size,
        uptime: process.uptime(),
        timestamp: new Date().toISOString()
    });
});

// 设置浏览器模式
app.post('/set-browser-mode', async (req, res) => {
    try {
        const { mode } = req.body; // 'browser' 或 'headless'
        const headless = mode === 'headless';

        // 如果浏览器已经启动且模式不同，需要重启浏览器
        if (browser) {
            await browser.close();
            browser = null;
            page = null;
            agent = null;
        }

        // 重新初始化浏览器
        await initBrowser(headless);

        res.json({
            success: true,
            mode: mode,
            message: `浏览器已切换到${headless ? '无头模式' : '浏览器模式'}`
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// 导航到URL
app.post('/goto', async (req, res) => {
    try {
        const { url, mode } = req.body;
        const headless = mode === 'headless' || mode === undefined; // 默认无头模式
        const { page } = await initBrowser(headless);
        
        await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
        
        res.json({ 
            success: true, 
            url: page.url(),
            title: await page.title()
        });
    } catch (error) {
        res.status(500).json({ 
            success: false, 
            error: error.message 
        });
    }
});

// AI输入
app.post('/ai-input', async (req, res) => {
    try {
        const { text, locate } = req.body;
        const { agent } = await initBrowser();
        
        const result = await agent.aiInput(text, locate);
        
        res.json({ 
            success: true, 
            result 
        });
    } catch (error) {
        res.status(500).json({ 
            success: false, 
            error: error.message 
        });
    }
});

// AI点击
app.post('/ai-tap', async (req, res) => {
    try {
        const { prompt } = req.body;
        const { agent } = await initBrowser();
        
        const result = await agent.aiTap(prompt);
        
        res.json({ 
            success: true, 
            result 
        });
    } catch (error) {
        res.status(500).json({ 
            success: false, 
            error: error.message 
        });
    }
});

// AI查询
app.post('/ai-query', async (req, res) => {
    try {
        const { prompt } = req.body;
        const { agent } = await initBrowser();
        
        const result = await agent.aiQuery(prompt);
        
        res.json({ 
            success: true, 
            result 
        });
    } catch (error) {
        res.status(500).json({ 
            success: false, 
            error: error.message 
        });
    }
});

// AI断言
app.post('/ai-assert', async (req, res) => {
    try {
        const { prompt } = req.body;
        const { agent } = await initBrowser();
        
        await agent.aiAssert(prompt);
        
        res.json({ 
            success: true, 
            result: true 
        });
    } catch (error) {
        res.status(500).json({ 
            success: false, 
            error: error.message 
        });
    }
});

// AI动作
app.post('/ai-action', async (req, res) => {
    try {
        const { prompt } = req.body;
        const { agent } = await initBrowser();
        
        const result = await agent.aiAction(prompt);
        
        res.json({ 
            success: true, 
            result 
        });
    } catch (error) {
        res.status(500).json({ 
            success: false, 
            error: error.message 
        });
    }
});

// AI等待
app.post('/ai-wait-for', async (req, res) => {
    try {
        const { prompt, timeout = 30000 } = req.body;
        const { agent } = await initBrowser();
        
        const result = await agent.aiWaitFor(prompt, { timeout });
        
        res.json({ 
            success: true, 
            result 
        });
    } catch (error) {
        res.status(500).json({ 
            success: false, 
            error: error.message 
        });
    }
});

// AI滚动
app.post('/ai-scroll', async (req, res) => {
    try {
        const { options, locate } = req.body;
        const { agent } = await initBrowser();
        
        let result;
        if (locate) {
            result = await agent.aiScroll(options, locate);
        } else {
            result = await agent.aiScroll(options);
        }
        
        res.json({ 
            success: true, 
            result 
        });
    } catch (error) {
        res.status(500).json({ 
            success: false, 
            error: error.message 
        });
    }
});

// 截图
app.post('/screenshot', async (req, res) => {
    try {
        const { path } = req.body;
        const { page } = await initBrowser();
        
        const screenshot = await page.screenshot({ path });
        
        res.json({ 
            success: true, 
            path 
        });
    } catch (error) {
        res.status(500).json({ 
            success: false, 
            error: error.message 
        });
    }
});

// 获取页面信息
app.get('/page-info', async (req, res) => {
    try {
        const { page } = await initBrowser();
        
        const info = {
            url: page.url(),
            title: await page.title(),
            viewport: page.viewportSize()
        };
        
        res.json({ 
            success: true, 
            info 
        });
    } catch (error) {
        res.status(500).json({ 
            success: false, 
            error: error.message 
        });
    }
});

// 健康检查
app.get('/health', (req, res) => {
    res.json({ 
        success: true, 
        message: 'MidSceneJS服务器运行正常',
        timestamp: new Date().toISOString()
    });
});

// 清理资源
app.post('/cleanup', async (req, res) => {
    try {
        if (page) {
            await page.close();
            page = null;
            agent = null;
        }
        if (browser) {
            await browser.close();
            browser = null;
        }
        
        res.json({ 
            success: true, 
            message: '资源已清理' 
        });
    } catch (error) {
        res.status(500).json({ 
            success: false, 
            error: error.message 
        });
    }
});

// 错误处理中间件
app.use((error, req, res, next) => {
    console.error('服务器错误:', error);
    res.status(500).json({ 
        success: false, 
        error: '内部服务器错误' 
    });
});

// 启动服务器
server.listen(port, () => {
    console.log(`🚀 MidSceneJS本地代理服务器启动成功`);
    console.log(`🌐 HTTP服务器: http://localhost:${port}`);
    console.log(`🔌 WebSocket服务器: ws://localhost:${port}`);
    console.log(`💡 AI模型: ${process.env.MIDSCENE_MODEL_NAME || 'qwen-vl-max-latest'}`);
    console.log(`🔗 API地址: ${process.env.OPENAI_BASE_URL || 'https://dashscope.aliyuncs.com/compatible-mode/v1'}`);
    console.log(`✨ 服务器就绪，等待测试执行请求...`);
    console.log(`📋 支持的API端点:`);
    console.log(`   POST /api/execute-testcase - 执行测试用例`);
    console.log(`   GET  /api/status - 获取服务器状态`);
    console.log(`   GET  /health - 健康检查`);
});

// 优雅关闭
process.on('SIGTERM', async () => {
    console.log('收到SIGTERM信号，正在优雅关闭...');
    if (page) await page.close();
    if (browser) await browser.close();
    process.exit(0);
});

process.on('SIGINT', async () => {
    console.log('收到SIGINT信号，正在优雅关闭...');
    if (page) await page.close();
    if (browser) await browser.close();
    process.exit(0);
}); 