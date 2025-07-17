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
const axios = require('axios');

const app = express();
const server = createServer(app);
const io = new Server(server, {
    cors: {
        origin: "*",
        methods: ["GET", "POST"]
    }
});

const port = 3001;

// 数据库配置
const API_BASE_URL = 'http://localhost:5001/api';

// 中间件
app.use(cors());
app.use(express.json({ limit: '50mb' }));

// 全局变量存储浏览器和页面实例
let browser = null;
let page = null;
let agent = null;

// 执行状态管理
const executionStates = new Map();

// 清理旧的执行状态 - 保留最近的50个执行记录
function cleanupOldExecutions() {
    const executions = Array.from(executionStates.entries());
    if (executions.length > 50) {
        // 按时间排序，保留最新的50个
        executions
            .sort((a, b) => (b[1].startTime || 0) - (a[1].startTime || 0))
            .slice(50)
            .forEach(([id]) => {
                executionStates.delete(id);
            });
    }
}

// 统一的日志记录函数
function logMessage(executionId, level, message) {
    const logEntry = {
        executionId,
        level,
        message,
        timestamp: new Date().toISOString()
    };
    
    // 发送WebSocket消息
    io.emit('log-message', logEntry);
    
    // 记录到执行状态
    const executionState = executionStates.get(executionId);
    if (executionState) {
        executionState.logs.push(logEntry);
    }
    
    return logEntry;
}

// 生成执行ID
function generateExecutionId() {
    return 'exec_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

// Web系统API集成函数
async function notifyExecutionStart(executionId, testcase, mode) {
    try {
        const totalSteps = Array.isArray(testcase.steps) ? testcase.steps.length : 
                          (typeof testcase.steps === 'string' ? JSON.parse(testcase.steps).length : 0);

        // 通过WebSocket通知前端执行开始
        io.emit('execution-start', {
            executionId: executionId,
            testcase: testcase.name,
            mode: mode,
            totalSteps: totalSteps
        });

        // 发送执行开始通知到Web系统API
        try {
            const startData = {
                execution_id: executionId,
                testcase_id: testcase.id,
                mode: mode,
                browser: 'chrome',
                steps_total: totalSteps,
                executed_by: 'midscene-server'
            };

            console.log(`📡 发送执行开始通知到Web系统 API: ${executionId}`);
            
            const response = await axios.post(`${API_BASE_URL}/midscene/execution-start`, startData, {
                headers: {
                    'Content-Type': 'application/json'
                },
                timeout: 10000
            });

            if (response.status === 200) {
                console.log(`✅ 执行开始通知已同步到Web系统: ${executionId}`);
            } else {
                console.warn(`⚠️ Web系统API响应异常: ${response.status} - ${response.statusText}`);
            }
        } catch (apiError) {
            console.error(`❌ 发送执行开始通知到Web系统失败: ${apiError.message}`);
            // 不中断流程，继续执行
        }
        
        console.log(`通知执行开始: ${executionId}`);
        return { success: true };
    } catch (error) {
        console.error(`通知执行开始失败: ${error.message}`);
        return null;
    }
}

async function notifyExecutionResult(executionId, testcase, mode, status, steps, errorMessage = null) {
    try {
        const executionState = executionStates.get(executionId);
        if (!executionState) {
            console.log(`未找到执行状态: ${executionId}`);
            return;
        }

        const endTime = new Date().toISOString();
        const startTime = executionState.startTime.toISOString();

        // 通过WebSocket通知前端执行结果
        io.emit('execution-completed', {
            executionId: executionId,
            testcase: testcase.name,
            status: status,
            mode: mode,
            startTime: startTime,
            endTime: endTime,
            steps: steps,
            errorMessage: errorMessage
        });

        // 发送执行结果到Web系统API
        try {
            const resultData = {
                execution_id: executionId,
                testcase_id: testcase.id,
                status: status,
                mode: mode,
                start_time: startTime,
                end_time: endTime,
                steps: steps || [],
                error_message: errorMessage
            };

            console.log(`📡 发送执行结果到Web系统 API: ${executionId}`);
            
            const response = await axios.post(`${API_BASE_URL}/midscene/execution-result`, resultData, {
                headers: {
                    'Content-Type': 'application/json'
                },
                timeout: 10000
            });

            if (response.status === 200) {
                console.log(`✅ 执行结果已同步到Web系统: ${executionId}`);
            } else {
                console.warn(`⚠️ Web系统API响应异常: ${response.status} - ${response.statusText}`);
            }
        } catch (apiError) {
            console.error(`❌ 发送执行结果到Web系统失败: ${apiError.message}`);
            // 不中断流程，继续WebSocket通知
        }

        console.log(`通知执行结果: ${executionId} -> ${status}`);
        return { success: true };
    } catch (error) {
        console.error(`通知执行结果失败: ${error.message}`);
        return null;
    }
}

// 启动浏览器和页面
async function initBrowser(headless = true, timeoutConfig = {}) {
    if (!browser) {
        console.log(`启动浏览器 - 模式: ${headless ? '无头模式' : '浏览器模式'}`);
        browser = await chromium.launch({
            headless: headless,
            args: [
                '--no-sandbox', 
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--disable-gpu'
            ]
        });
    }
    
    // 解析超时配置
    const pageTimeout = timeoutConfig.page_timeout || 30000;
    const actionTimeout = timeoutConfig.action_timeout || 30000;
    const navigationTimeout = timeoutConfig.navigation_timeout || 30000;
    
    if (!page) {
        const context = await browser.newContext({
            viewport: { width: 1280, height: 720 },
            deviceScaleFactor: 1,
            // 使用动态超时设置
            timeout: actionTimeout
        });
        page = await context.newPage();
    }
    
    // 每次都重新设置页面超时（因为浏览器可能被重用）
    page.setDefaultTimeout(actionTimeout);
    page.setDefaultNavigationTimeout(navigationTimeout);
    
    console.log(`⏱️ 超时设置: 页面加载=${pageTimeout}ms, 操作=${actionTimeout}ms, 导航=${navigationTimeout}ms`);
    
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

// 标准化步骤类型 - 将新的MidSceneJS格式映射到执行引擎识别的格式
function normalizeStepType(stepType) {
    const typeMapping = {
        // 新格式 -> 执行引擎格式
        'goto': 'navigate',
        'aiTap': 'ai_tap',
        'aiInput': 'ai_input',
        'aiAssert': 'ai_assert',
        'aiHover': 'ai_hover',
        'aiScroll': 'ai_scroll',
        'aiWaitFor': 'ai_wait_for',
        'evaluateJavaScript': 'evaluate_javascript',
        'logScreenshot': 'screenshot',
        
        // 保持旧格式兼容
        'navigate': 'navigate',
        'ai_tap': 'ai_tap',
        'ai_input': 'ai_input',
        'ai_assert': 'ai_assert',
        'ai_hover': 'ai_hover',
        'ai_scroll': 'ai_scroll',
        'ai_wait_for': 'ai_wait_for',
        'click': 'click',
        'type': 'type',
        'wait': 'wait',
        'sleep': 'sleep',
        'assert': 'assert',
        'refresh': 'refresh',
        'back': 'back',
        'screenshot': 'screenshot',
        'evaluate_javascript': 'evaluate_javascript'
    };
    
    return typeMapping[stepType] || stepType;
}

// 执行单个步骤
async function executeStep(step, page, agent, executionId, stepIndex, totalSteps, timeoutConfig = {}) {
    // 支持新旧格式兼容: 新格式使用type字段，旧格式使用action字段
    const stepType = step.type || step.action;
    const params = step.params || {};
    const description = step.description;

    // 标准化步骤类型名称 - 将新的MidSceneJS格式映射到执行引擎识别的格式
    const normalizedAction = normalizeStepType(stepType);

    // 发送步骤开始事件
    io.emit('step-start', {
        executionId,
        stepIndex,
        action: normalizedAction,
        description: description || normalizedAction,
        totalSteps: totalSteps
    });

    const stepStartTime = Date.now();

    try {
        switch (normalizedAction) {
            case 'navigate':
                if (params.url) {
                    const pageTimeout = timeoutConfig.page_timeout || 30000;
                    const navigationTimeout = timeoutConfig.navigation_timeout || 30000;
                    
                    try {
                        // 首先尝试使用 domcontentloaded，更快的加载策略
                        await page.goto(params.url, { waitUntil: 'domcontentloaded', timeout: navigationTimeout });
                        logMessage(executionId, 'info', `导航到: ${params.url}`);
                        
                        // 等待页面稳定
                        await page.waitForTimeout(2000);
                    } catch (error) {
                        // 如果超时，尝试使用更宽松的策略
                        logMessage(executionId, 'warning', `导航超时，尝试使用基础加载策略: ${error.message}`);
                        const fallbackTimeout = Math.min(navigationTimeout / 2, 15000);
                        await page.goto(params.url, { waitUntil: 'commit', timeout: fallbackTimeout });
                        await page.waitForTimeout(3000);
                        logMessage(executionId, 'info', `导航到: ${params.url} (使用基础策略，超时=${fallbackTimeout}ms)`);
                    }
                }
                break;

            case 'click':
            case 'ai_tap':
                const clickTarget = params.locate || params.selector || params.element;
                if (clickTarget) {
                    await agent.aiTap(clickTarget);
                    logMessage(executionId, 'info', `点击: ${clickTarget}`);
                }
                break;

            case 'type':
            case 'ai_input':
                const inputTarget = params.locate || params.selector || params.element;
                const inputText = params.text || params.value;
                if (inputTarget && inputText) {
                    await agent.aiInput(inputText, inputTarget);
                    logMessage(executionId, 'info', `输入: "${inputText}" 到 ${inputTarget}`);
                }
                break;

            case 'wait':
            case 'sleep':
                const waitTime = params.time || params.duration || 1000;
                await page.waitForTimeout(waitTime);
                logMessage(executionId, 'info', `等待: ${waitTime}ms`);
                break;

            case 'assert':
            case 'ai_assert':
                const assertCondition = params.condition || params.assertion || params.expected;
                if (assertCondition) {
                    await agent.aiAssert(assertCondition);
                    logMessage(executionId, 'info', `断言: ${assertCondition}`);
                }
                break;

            case 'refresh':
                const refreshTimeout = timeoutConfig.navigation_timeout || 30000;
                await page.reload({ waitUntil: 'domcontentloaded', timeout: refreshTimeout });
                logMessage(executionId, 'info', `刷新页面 (超时=${refreshTimeout}ms)`);
                break;

            case 'back':
                const backTimeout = timeoutConfig.navigation_timeout || 30000;
                await page.goBack({ waitUntil: 'domcontentloaded', timeout: backTimeout });
                logMessage(executionId, 'info', `返回上一页 (超时=${backTimeout}ms)`);
                break;

            case 'screenshot':
                const screenshotPath = `./screenshots/${executionId}_step_${stepIndex}.png`;
                await page.screenshot({ path: screenshotPath, fullPage: true });
                logMessage(executionId, 'info', `截图保存到: ${screenshotPath}`);
                break;

            case 'ai_hover':
                const hoverTarget = params.locate || params.selector || params.element;
                if (hoverTarget) {
                    await agent.aiHover(hoverTarget);
                    logMessage(executionId, 'info', `悬停: ${hoverTarget}`);
                }
                break;

            case 'ai_scroll':
                const scrollDirection = params.direction || 'down';
                const scrollDistance = params.distance || 500;
                if (scrollDirection === 'down') {
                    await page.evaluate((dist) => window.scrollBy(0, dist), scrollDistance);
                } else if (scrollDirection === 'up') {
                    await page.evaluate((dist) => window.scrollBy(0, -dist), scrollDistance);
                }
                logMessage(executionId, 'info', `滚动: ${scrollDirection} ${scrollDistance}px`);
                break;

            case 'evaluate_javascript':
                const jsCode = params.code || params.script;
                if (jsCode) {
                    const result = await page.evaluate(jsCode);
                    logMessage(executionId, 'info', `执行JavaScript: ${jsCode}, 结果: ${result}`);
                }
                break;

            case 'ai_wait_for':
                const waitTarget = params.locate || params.selector || params.element;
                const waitTimeout = params.timeout || 10000;
                if (waitTarget) {
                    await agent.aiWaitFor(waitTarget, { timeout: waitTimeout });
                    logMessage(executionId, 'info', `等待元素出现: ${waitTarget}`);
                }
                break;

            default:
                // 通用AI操作
                const instruction = description || stepType;
                await agent.ai(instruction);
                logMessage(executionId, 'info', `AI操作: ${instruction}`);
                break;
        }

        const stepEndTime = Date.now();
        const duration = stepEndTime - stepStartTime;
        
        return {
            status: 'success',
            start_time: new Date(stepStartTime).toISOString(),
            end_time: new Date(stepEndTime).toISOString(),
            duration: duration
        };

    } catch (error) {
        const stepEndTime = Date.now();
        const duration = stepEndTime - stepStartTime;
        
        // 发送步骤失败事件
        io.emit('step-failed', {
            executionId,
            stepIndex,
            totalSteps: totalSteps,
            error: error.message
        });
        
        logMessage(executionId, 'error', `步骤执行失败: ${error.message}`);
        
        // 返回失败结果而不是抛出异常，让上层处理
        return {
            status: 'failed',
            start_time: new Date(stepStartTime).toISOString(),
            end_time: new Date(stepEndTime).toISOString(),
            duration: duration,
            error_message: error.message
        };
    }
}

// 异步执行完整测试用例
async function executeTestCaseAsync(testcase, mode, executionId, timeoutConfig = {}) {
    try {
        // 清理旧的执行状态，确保不会累积太多数据
        cleanupOldExecutions();
        
        // 为每次执行创建独立的状态记录
        const currentExecution = {
            id: executionId,
            status: 'running',
            startTime: new Date(),
            testcase: testcase.name,
            mode,
            steps: [],  // 收集步骤执行数据
            screenshots: [],  // 收集截图数据
            logs: []  // 收集日志数据
        };
        
        // 更新执行状态
        executionStates.set(executionId, currentExecution);

        // 通知Web系统执行开始
        await notifyExecutionStart(executionId, testcase, mode);

        // 发送执行开始事件
        io.emit('execution-start', {
            executionId,
            testcase: testcase.name,
            mode,
            timestamp: new Date().toISOString()
        });

        logMessage(executionId, 'info', `开始执行测试用例: ${testcase.name}`);

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

        logMessage(executionId, 'info', `共 ${steps.length} 个步骤`);

        // 初始化浏览器
        const headless = mode === 'headless';
        logMessage(executionId, 'info', `初始化浏览器 (${headless ? '无头模式' : '可视模式'})`);

        const { page, agent } = await initBrowser(headless, timeoutConfig);

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

            // 执行步骤并获取详细结果
            const stepStartTime = new Date();
            let stepResult = null;
            
            // executeStep现在返回结果而不是抛出异常
            stepResult = await executeStep(step, page, agent, executionId, i, steps.length, timeoutConfig);
            
            // 根据步骤结果发送相应事件
            if (stepResult.status === 'success') {
                // 发送步骤完成事件
                io.emit('step-completed', {
                    executionId,
                    stepIndex: i,
                    totalSteps: steps.length,
                    success: true,
                    result: stepResult
                });
            } else {
                // 步骤执行失败
                logMessage(executionId, 'error', `步骤 ${i + 1} 执行失败: ${stepResult.error_message}`);
                
                // 发送步骤失败事件
                io.emit('step-completed', {
                    executionId,
                    stepIndex: i,
                    totalSteps: steps.length,
                    success: false,
                    error: stepResult.error_message
                });
                
                // 继续执行后续步骤（可以根据配置决定是否在首次失败时停止）
            }

            // 截图
            let screenshot = null;
            try {
                screenshot = await page.screenshot({
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

            // 记录步骤执行数据到当前执行记录
            const executionState = executionStates.get(executionId);
            if (executionState) {
                const stepEndTime = new Date();
                const stepData = {
                    index: i,
                    description: step.description || step.action || 'Unknown Step',
                    status: stepResult?.status || 'success',
                    start_time: stepResult?.start_time || stepStartTime.toISOString(),
                    end_time: stepResult?.end_time || stepEndTime.toISOString(),
                    duration: stepResult?.duration || (stepEndTime - stepStartTime),
                    stepType: step.type || step.action,
                    params: step.params || {},
                    error_message: stepResult?.error_message || null
                };
                
                executionState.steps.push(stepData);
                
                // 记录截图数据
                if (screenshot) {
                    executionState.screenshots.push({
                        stepIndex: i,
                        timestamp: new Date().toISOString(),
                        screenshot: screenshot.toString('base64')
                    });
                }
            }

            // 短暂延迟，让用户看到执行过程
            await page.waitForTimeout(500);
        }

        // 更新执行状态并计算统计信息
        const executionState = executionStates.get(executionId);
        executionState.endTime = new Date();
        executionState.duration = executionState.endTime - executionState.startTime;
        
        // 计算步骤统计
        const totalSteps = executionState.steps.length;
        const successSteps = executionState.steps.filter(step => step.status === 'success').length;
        const failedSteps = executionState.steps.filter(step => step.status === 'failed').length;
        
        // 根据步骤结果确定整体状态
        const overallStatus = failedSteps > 0 ? 'failed' : 'success';
        executionState.status = overallStatus;

        // 发送执行完成事件
        io.emit('execution-completed', {
            executionId,
            status: overallStatus,
            message: overallStatus === 'success' ? '测试执行完成！' : `测试执行完成，但有 ${failedSteps} 个步骤失败`,
            duration: executionState.duration,
            totalSteps: totalSteps,
            successSteps: successSteps,
            failedSteps: failedSteps,
            timestamp: new Date().toISOString()
        });

        const statusMessage = overallStatus === 'success' 
            ? `测试执行完成！耗时: ${Math.round(executionState.duration / 1000)}秒，成功步骤: ${successSteps}/${totalSteps}`
            : `测试执行完成，但有失败！耗时: ${Math.round(executionState.duration / 1000)}秒，成功步骤: ${successSteps}/${totalSteps}，失败步骤: ${failedSteps}`;
        
        logMessage(executionId, overallStatus === 'success' ? 'success' : 'warning', statusMessage);
        
        // 检查并通知MidScene生成的报告
        await checkAndNotifyMidsceneReport(executionId, testcase, executionState);

        // 通知Web系统执行完成
        await notifyExecutionResult(executionId, testcase, mode, overallStatus, executionState.steps);

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
        io.emit('execution-completed', {
            executionId,
            status: 'failed',
            error: error.message,
            timestamp: new Date().toISOString()
        });

        logMessage(executionId, 'error', `测试执行失败: ${error.message}`);

        // 通知Web系统执行失败
        await notifyExecutionResult(executionId, testcase, mode, 'failed', executionState?.steps || [], error.message);
    } finally {
        // 确保每次执行完成后都关闭浏览器，避免资源泄漏和状态污染
        try {
            if (browser) {
                console.log('🔄 关闭浏览器进程，清理资源...');
                await browser.close();
                browser = null;
                page = null;
                agent = null;
                console.log('✅ 浏览器进程已关闭');
            }
        } catch (closeError) {
            console.error('⚠️ 关闭浏览器失败:', closeError.message);
        }
    }
}

// API端点

// 执行完整测试用例
app.post('/api/execute-testcase', async (req, res) => {
    try {
        const { testcase, mode = 'headless', timeout_settings = {} } = req.body;

        if (!testcase) {
            return res.status(400).json({
                success: false,
                error: '缺少测试用例数据'
            });
        }

        const executionId = generateExecutionId();

        // 解析超时设置
        const timeoutConfig = {
            page_timeout: timeout_settings.page_timeout || 30000,
            action_timeout: timeout_settings.action_timeout || 30000,
            navigation_timeout: timeout_settings.navigation_timeout || 30000
        };
        
        console.log('📋 接收到的超时设置:', JSON.stringify(timeoutConfig, null, 2));

        // 异步执行，立即返回执行ID
        executeTestCaseAsync(testcase, mode, executionId, timeoutConfig).catch(error => {
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

// 获取独立的执行报告
app.get('/api/execution-report/:executionId', (req, res) => {
    const { executionId } = req.params;
    const executionState = executionStates.get(executionId);

    if (!executionState) {
        return res.status(404).json({
            success: false,
            error: '执行记录不存在'
        });
    }

    // 生成独立的执行报告
    const report = {
        executionId: executionId,
        testcase: executionState.testcase,
        status: executionState.status,
        mode: executionState.mode,
        startTime: executionState.startTime,
        endTime: executionState.endTime,
        duration: executionState.duration,
        summary: {
            totalSteps: executionState.steps.length,
            successfulSteps: executionState.steps.filter(s => s.status === 'success').length,
            failedSteps: executionState.steps.filter(s => s.status === 'failed').length,
            totalLogs: executionState.logs.length,
            totalScreenshots: executionState.screenshots.length
        },
        steps: executionState.steps,
        logs: executionState.logs,
        screenshots: executionState.screenshots,
        generatedAt: new Date().toISOString()
    };

    res.json({
        success: true,
        report
    });
});

// 获取所有执行记录列表
app.get('/api/executions', (req, res) => {
    const executions = Array.from(executionStates.entries()).map(([id, state]) => ({
        executionId: id,
        testcase: state.testcase,
        status: state.status,
        mode: state.mode,
        startTime: state.startTime,
        endTime: state.endTime,
        duration: state.duration,
        stepsCount: state.steps.length
    }));

    // 按开始时间倒序排列
    executions.sort((a, b) => new Date(b.startTime) - new Date(a.startTime));

    res.json({
        success: true,
        executions,
        total: executions.length
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

        logMessage(executionId, 'warning', '执行已被用户停止');

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
        const { url, mode, timeout_settings = {} } = req.body;
        const headless = mode === 'headless' || mode === undefined; // 默认无头模式
        const timeoutConfig = {
            page_timeout: timeout_settings.page_timeout || 30000,
            action_timeout: timeout_settings.action_timeout || 30000,
            navigation_timeout: timeout_settings.navigation_timeout || 30000
        };
        const { page } = await initBrowser(headless, timeoutConfig);
        
        const navigationTimeout = timeoutConfig.navigation_timeout;
        try {
            await page.goto(url, { waitUntil: 'domcontentloaded', timeout: navigationTimeout });
        } catch (error) {
            // 如果超时，尝试使用更宽松的策略
            const fallbackTimeout = Math.min(navigationTimeout / 2, 15000);
            await page.goto(url, { waitUntil: 'commit', timeout: fallbackTimeout });
        }
        
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

// 检查并通知MidScene生成的报告
async function checkAndNotifyMidsceneReport(executionId, testcase, executionState) {
    try {
        const fs = require('fs');
        const path = require('path');
        
        console.log(`📋 开始检查MidScene报告，执行ID: ${executionId}`);
        console.log(`📋 当前工作目录: ${process.cwd()}`);
        
        // 检查midscene_run目录是否存在
        const midsceneRunDir = path.join(process.cwd(), 'midscene_run');
        console.log(`📋 检查目录: ${midsceneRunDir}`);
        
        if (!fs.existsSync(midsceneRunDir)) {
            console.log('📋 midscene_run目录不存在，跳过报告检查');
            logMessage(executionId, 'warning', 'MidScene报告目录不存在，请检查测试执行环境');
            return;
        }
        
        // 检查报告目录
        const reportDir = path.join(midsceneRunDir, 'report');
        console.log(`📋 检查报告目录: ${reportDir}`);
        
        if (!fs.existsSync(reportDir)) {
            console.log('📋 报告目录不存在，跳过报告检查');
            logMessage(executionId, 'warning', 'MidScene报告子目录不存在，可能测试未生成报告');
            return;
        }
        
        // 获取报告目录中的所有HTML文件
        const files = fs.readdirSync(reportDir);
        console.log(`📋 报告目录中的文件: ${files.join(', ')}`);
        
        const htmlFiles = files.filter(file => file.endsWith('.html') && file.includes('playwright-'));
        console.log(`📋 找到的HTML报告文件: ${htmlFiles.join(', ')}`);
        
        if (htmlFiles.length === 0) {
            console.log('📋 未找到MidScene报告文件');
            logMessage(executionId, 'warning', 'MidScene未生成报告文件，可能测试执行过程中出现问题');
            return;
        }
        
        // 按文件修改时间排序，获取最新的报告文件
        const fileStats = htmlFiles.map(file => {
            const filePath = path.join(reportDir, file);
            const stats = fs.statSync(filePath);
            return {
                name: file,
                path: filePath,
                mtime: stats.mtime
            };
        });
        
        // 获取最新的报告文件
        const latestReport = fileStats.sort((a, b) => b.mtime - a.mtime)[0];
        
        if (latestReport) {
            const reportPath = latestReport.path;
            console.log(`📊 找到MidScene报告文件: ${reportPath}`);
            console.log(`📊 报告文件修改时间: ${latestReport.mtime}`);
            
            // 生成简化的报告
            const simplifiedReportPath = await generateSimplifiedReport(reportPath, testcase, executionState);
            
            // 通过日志消息通知前端使用简化的报告
            logMessage(executionId, 'info', `Midscene - report file updated: ${simplifiedReportPath || reportPath}`);
            
            // 额外发送一条明确的成功消息
            logMessage(executionId, 'success', `报告已生成: ${latestReport.name}`);
        }
        
    } catch (error) {
        console.error('检查MidScene报告失败:', error);
        logMessage(executionId, 'error', `检查MidScene报告失败: ${error.message}`);
    }
}

// 生成简化的报告
async function generateSimplifiedReport(originalReportPath, testcase, executionState) {
    try {
        const fs = require('fs');
        const path = require('path');
        
        // 读取原始报告
        const originalContent = fs.readFileSync(originalReportPath, 'utf8');
        
        // 生成简化的报告文件名
        const reportDir = path.dirname(originalReportPath);
        const originalName = path.basename(originalReportPath, '.html');
        const simplifiedName = `${originalName}_simplified.html`;
        const simplifiedPath = path.join(reportDir, simplifiedName);
        
        // 创建简化的报告内容
        const simplifiedContent = createSimplifiedReportContent(originalContent, testcase, executionState);
        
        // 写入简化报告
        fs.writeFileSync(simplifiedPath, simplifiedContent, 'utf8');
        
        console.log(`📊 生成简化报告: ${simplifiedPath}`);
        return simplifiedPath;
        
    } catch (error) {
        console.error('生成简化报告失败:', error);
        return null;
    }
}

// 创建简化的报告内容
function createSimplifiedReportContent(originalContent, testcase, executionState) {
    const steps = executionState.steps || [];
    const duration = executionState.duration || 0;
    
    // 从原始报告中提取主要内容，去掉统计指标
    let simplifiedContent = originalContent;
    
    // 移除统计指标相关的HTML
    simplifiedContent = simplifiedContent.replace(/<div[^>]*class="[^"]*summary[^"]*"[^>]*>[\s\S]*?<\/div>/gi, '');
    simplifiedContent = simplifiedContent.replace(/<div[^>]*class="[^"]*stats[^"]*"[^>]*>[\s\S]*?<\/div>/gi, '');
    simplifiedContent = simplifiedContent.replace(/<div[^>]*class="[^"]*metrics[^"]*"[^>]*>[\s\S]*?<\/div>/gi, '');
    
    // 添加简化的标题信息
    const titleInfo = `
        <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
            <h1 style="margin: 0; color: #333;">测试执行报告</h1>
            <div style="margin-top: 10px; color: #666;">
                <strong>测试用例:</strong> ${testcase.name} &nbsp;&nbsp;
                <strong>状态:</strong> ${executionState.status || 'completed'} &nbsp;&nbsp;
                <strong>耗时:</strong> ${Math.round(duration / 1000)}秒 &nbsp;&nbsp;
                <strong>步骤数:</strong> ${steps.length}
            </div>
        </div>
    `;
    
    // 将标题信息插入到body开头
    simplifiedContent = simplifiedContent.replace(/<body[^>]*>/i, `$&${titleInfo}`);
    
    return simplifiedContent;
}

// 启动服务器
server.listen(port, () => {
    console.log(`MidSceneJS本地代理服务器启动成功`);
    console.log(`HTTP服务器: http://localhost:${port}`);
    console.log(`WebSocket服务器: ws://localhost:${port}`);
    console.log(`AI模型: ${process.env.MIDSCENE_MODEL_NAME || 'qwen-vl-max-latest'}`);
    console.log(`API地址: ${process.env.OPENAI_BASE_URL || 'https://dashscope.aliyuncs.com/compatible-mode/v1'}`);
    console.log(`服务器就绪，等待测试执行请求...`);
    console.log(`支持的API端点:`);
    console.log(`   POST /api/execute-testcase - 执行测试用例`);
    console.log(`   GET  /api/execution-status/:id - 获取执行状态`);
    console.log(`   GET  /api/execution-report/:id - 获取独立执行报告`);
    console.log(`   GET  /api/executions - 获取所有执行记录`);
    console.log(`   POST /api/stop-execution/:id - 停止执行`);
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