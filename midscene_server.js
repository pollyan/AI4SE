/**
 * MidSceneJS HTTP API服务器
 * 提供AI功能的HTTP接口供Python调用
 */

const express = require('express');
const cors = require('cors');
const { PlaywrightAgent } = require('@midscene/web');
const { chromium } = require('playwright');

const app = express();
const port = 3001;

// 中间件
app.use(cors());
app.use(express.json({ limit: '50mb' }));

// 全局变量存储浏览器和页面实例
let browser = null;
let page = null;
let agent = null;

// 启动浏览器和页面
async function initBrowser() {
    if (!browser) {
        browser = await chromium.launch({
            headless: process.env.HEADLESS === 'true',
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

// API端点

// 导航到URL
app.post('/goto', async (req, res) => {
    try {
        const { url } = req.body;
        const { page } = await initBrowser();
        
        await page.goto(url, { waitUntil: 'networkidle' });
        
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
app.listen(port, () => {
    console.log(`🚀 MidSceneJS服务器启动成功`);
    console.log(`🌐 监听端口: ${port}`);
    console.log(`💡 模型: ${process.env.MIDSCENE_MODEL_NAME || 'gpt-4o'}`);
    console.log(`🔗 API地址: ${process.env.OPENAI_BASE_URL || 'https://api.openai.com/v1'}`);
    console.log(`✨ 服务器就绪，等待AI请求...`);
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