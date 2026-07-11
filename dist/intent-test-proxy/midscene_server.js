/**
 * MidSceneJS HTTP API服务器
 * 提供AI功能的HTTP接口供Python调用
 */

// 加载环境变量
require('dotenv').config();

// 环境变量完整性检查
function validateEnvironmentVariables() {
    const requiredVars = [
        'OPENAI_API_KEY',
        'OPENAI_BASE_URL',
        'MIDSCENE_MODEL_NAME',
        'MAIN_APP_URL'
    ];
    const missing = requiredVars.filter(name =>
        typeof process.env[name] !== 'string' || !process.env[name].trim()
    );
    if (missing.length > 0) {
        throw new Error(`Missing required environment variables: ${missing.join(', ')}`);
    }
    for (const name of ['OPENAI_BASE_URL', 'MAIN_APP_URL']) {
        let parsed;
        try {
            parsed = new URL(process.env[name]);
        } catch (_error) {
            throw new Error(`Invalid required URL environment variable: ${name}`);
        }
        if (!['http:', 'https:'].includes(parsed.protocol)) {
            throw new Error(`Invalid required URL environment variable: ${name}`);
        }
    }
}

const express = require('express');
const { PlaywrightAgent } = require('@midscene/web');
const { chromium } = require('playwright');
const { createServer } = require('http');
const { Server } = require('socket.io');
const axios = require('axios');
const crypto = require('crypto');
const path = require('path');
const fs = require('fs');

function loadRuntimeConfig(env) {
    const topology = env.INTENT_PROXY_TOPOLOGY;
    if (!['local-host', 'managed'].includes(topology)) {
        throw new Error('INTENT_PROXY_TOPOLOGY must be local-host or managed');
    }
    const proxyToken = env.INTENT_PROXY_TOKEN;
    if (typeof proxyToken !== 'string' || Buffer.byteLength(proxyToken, 'utf8') < 32) {
        throw new Error('INTENT_PROXY_TOKEN must contain at least 32 UTF-8 bytes');
    }
    let origin;
    try {
        origin = new URL(env.INTENT_PUBLIC_ORIGIN);
    } catch (_error) {
        throw new Error('INTENT_PUBLIC_ORIGIN must be an absolute HTTP(S) origin');
    }
    if (!['http:', 'https:'].includes(origin.protocol) || origin.origin !== env.INTENT_PUBLIC_ORIGIN || env.INTENT_PUBLIC_ORIGIN === '*') {
        throw new Error('INTENT_PUBLIC_ORIGIN must be an exact HTTP(S) origin');
    }
    const loopbackHosts = new Set(['localhost', '127.0.0.1', '[::1]']);
    if (
        topology === 'local-host' &&
        (origin.protocol !== 'http:' || !loopbackHosts.has(origin.hostname))
    ) {
        throw new Error('local-host INTENT_PUBLIC_ORIGIN must be an exact loopback HTTP origin');
    }
    return {
        topology,
        bindHost: topology === 'local-host' ? '127.0.0.1' : '0.0.0.0',
        browserSocketEnabled: topology === 'local-host',
        publicOrigin: origin.origin,
        proxyToken
    };
}

let runtimeConfig = null;
if (process.env.INTENT_PROXY_TOPOLOGY || process.env.INTENT_PROXY_TOKEN || process.env.INTENT_PUBLIC_ORIGIN) {
    runtimeConfig = loadRuntimeConfig(process.env);
}

function setRuntimeConfigForTest(config) {
    if (process.env.NODE_ENV !== 'test') throw new Error('test-only runtime config override');
    runtimeConfig = config;
}

function timingSafeEqualSecret(supplied, expected) {
    if (typeof supplied !== 'string' || typeof expected !== 'string') return false;
    const left = Buffer.from(supplied, 'utf8');
    const right = Buffer.from(expected, 'utf8');
    return left.length === right.length && crypto.timingSafeEqual(left, right);
}

function parseBearer(value) {
    const match = typeof value === 'string' ? /^Bearer ([^\s]+)$/.exec(value) : null;
    return match ? match[1] : null;
}

function requireBackendToken(req, res, next) {
    if (req.method === 'GET' && req.path === '/health') return next();
    if (req.method === 'GET' && req.path === '/ai-test') return res.status(404).end();
    const supplied = parseBearer(req.get('authorization'));
    if (!runtimeConfig || !timingSafeEqualSecret(supplied, runtimeConfig.proxyToken)) {
        return res.status(401).json({ success: false, code: 'PROXY_AUTH_REQUIRED' });
    }
    return next();
}

function resolveArtifactPath(outputRoot, executionId, serverName) {
    if (typeof executionId !== 'string' || typeof serverName !== 'string') throw new Error('invalid artifact path');
    const root = path.resolve(outputRoot);
    const owningRoot = path.resolve(root, executionId);
    const resolved = path.resolve(root, executionId, serverName);
    if (!owningRoot.startsWith(`${root}${path.sep}`) || !resolved.startsWith(`${owningRoot}${path.sep}`)) {
        throw new Error('artifact path escapes owning output root');
    }
    if (fs.existsSync(root)) {
        const rootStat = fs.lstatSync(root);
        if (!rootStat.isDirectory() || rootStat.isSymbolicLink()) {
            throw new Error('artifact path has an unsafe output root');
        }
        const realRoot = fs.realpathSync(root);
        const relativeParts = path.relative(root, resolved).split(path.sep);
        let cursor = root;
        for (const part of relativeParts) {
            cursor = path.join(cursor, part);
            if (!fs.existsSync(cursor)) break;
            if (fs.lstatSync(cursor).isSymbolicLink()) {
                throw new Error('artifact path contains a symbolic link');
            }
            const realCursor = fs.realpathSync(cursor);
            if (realCursor !== realRoot && !realCursor.startsWith(`${realRoot}${path.sep}`)) {
                throw new Error('artifact path escapes owning output root');
            }
        }
    }
    return resolved;
}

const SAFE_STEP_STATUSES = new Set(['pending', 'running', 'success', 'failed', 'stopped', 'skipped']);

function safeStepProgress(state) {
    if (!Array.isArray(state?.steps)) return [];
    return state.steps.flatMap(step => {
        if (!step || !Number.isInteger(step.index) || typeof step.description !== 'string' ||
            !SAFE_STEP_STATUSES.has(step.status)) {
            return [];
        }
        return [{
            index: step.index,
            description: step.description,
            status: step.status,
            start_time: typeof step.start_time === 'string' ? step.start_time : null,
            end_time: typeof step.end_time === 'string' ? step.end_time : null,
            duration: Number.isFinite(step.duration) ? step.duration : null
        }];
    });
}

function safeExecutionSnapshot(executionId, state) {
    const callbackCodes = Array.isArray(state?.callbackErrors)
        ? state.callbackErrors.map(item => item?.code).filter(code => typeof code === 'string')
        : [];
    const currentStep = Number.isInteger(state?.currentStep) ? state.currentStep : (Array.isArray(state?.steps) ? state.steps.length : 0);
    const totalSteps = Number.isInteger(state?.totalSteps) ? state.totalSteps : currentStep;
    return {
        executionId,
        status: state?.status,
        progress: { currentStep, totalSteps },
        steps: safeStepProgress(state),
        callbackCodes
    };
}

// Lifecycle callback adapter. Tests may replace only this external boundary;
// the Express app and execution runtime remain the production implementation.
let lifecycleHttpClient = axios;

const app = express();
const server = createServer(app);
const io = new Server(server, {
    cors: {
        origin(origin, callback) {
            callback(null, Boolean(runtimeConfig && origin === runtimeConfig.publicOrigin));
        },
        methods: ["GET", "POST"]
    }
});

const port = process.env.PORT || 3001;

// 数据库配置 - 注意：如果需要连接到主Web应用，请确保端口正确
const API_BASE_URL = process.env.MAIN_APP_URL;
const OUTPUT_ROOT = path.resolve(process.cwd(), 'screenshots');
const LIFECYCLE_CALLBACK_MAX_ATTEMPTS = 3;
const LIFECYCLE_CALLBACK_BACKOFF_MS = 25;

// 中间件
app.use(express.json({ limit: '50mb' }));
app.use((req, res, next) => {
    const origin = req.get('origin');
    if (origin && (!runtimeConfig || origin !== runtimeConfig.publicOrigin)) {
        return res.status(403).json({ success: false, code: 'ORIGIN_NOT_ALLOWED' });
    }
    return next();
});
app.use(requireBackendToken);

// 全局变量存储浏览器和页面实例
let browser = null;
let page = null;
let agent = null;

// 执行状态管理
const executionStates = new Map();

// 执行控制标志 - 用于中断执行
const executionControls = new Map();

// 变量上下文管理 - 存储每个执行的变量
const variableContexts = new Map();

// The runtime owns one global browser/page/agent set, so admission is
// deliberately serial. This remains set until the owning async execution has
// completed resource cleanup, even when its public state has been stopped.
let activeExecutionId = null;
let activeExecutionPromise = null;
let runtimeResetting = false;
let resetPromise = null;

function emitExecutionEvent(executionId, event, payload) {
    if (typeof executionId !== 'string' || !executionId) return false;
    io.to(`execution:${executionId}`).emit(event, payload);
    return true;
}

function verifySocketTicket(ticket, requestedExecutionId, requestOrigin) {
    if (!runtimeConfig?.browserSocketEnabled) {
        const error = new Error('BROWSER_SOCKET_DISABLED');
        error.data = { code: 'BROWSER_SOCKET_DISABLED' };
        throw error;
    }
    if (typeof ticket !== 'string') throw new Error('SOCKET_TICKET_INVALID');
    const parts = ticket.split('.');
    if (parts.length !== 2) throw new Error('SOCKET_TICKET_INVALID');
    const [encoded, signature] = parts;
    let payloadBytes;
    let payload;
    try {
        payloadBytes = Buffer.from(encoded, 'base64url');
        payload = JSON.parse(payloadBytes.toString('utf8'));
    } catch (_error) {
        throw new Error('SOCKET_TICKET_INVALID');
    }
    const expected = crypto.createHmac('sha256', runtimeConfig.proxyToken).update(payloadBytes).digest('base64url');
    if (!timingSafeEqualSecret(signature, expected)) throw new Error('SOCKET_TICKET_INVALID');
    const now = Math.floor(Date.now() / 1000);
    if (!payload || typeof payload.executionId !== 'string' || !payload.executionId ||
        requestedExecutionId !== payload.executionId ||
        payload.origin !== runtimeConfig.publicOrigin || requestOrigin !== runtimeConfig.publicOrigin ||
        payload.aud !== 'intent-proxy-socket' || !Number.isInteger(payload.iat) ||
        !Number.isInteger(payload.exp) || payload.iat > now + 5 || payload.exp <= now ||
        payload.exp !== payload.iat + 60 || typeof payload.nonce !== 'string' || !payload.nonce) {
        throw new Error('SOCKET_TICKET_INVALID');
    }
    return payload;
}

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
    emitExecutionEvent(executionId, 'log-message', logEntry);
    
    // 记录到执行状态
    const executionState = executionStates.get(executionId);
    if (executionState) {
        executionState.logs.push(logEntry);
    }
    
    return logEntry;
}

// 解析变量引用 - 使用 ${variable} 语法
function resolveVariableReferences(text, variableContext) {
    if (!text || typeof text !== 'string' || !variableContext) {
        return text;
    }
    
    // 只匹配 ${variable} 或 ${variable.property} 格式
    const variablePattern = /\$\{([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)\}/g;
    
    return text.replace(variablePattern, (match, variablePath) => {
        // 解析变量路径，支持多级属性访问
        const pathParts = variablePath.split('.');
        const variableName = pathParts[0];
        const properties = pathParts.slice(1);
        
        // 获取基础变量值
        let variableValue = variableContext[variableName];
        
        if (variableValue === undefined) {
            console.warn(`变量未找到: ${variableName}`);
            return match; // 保持原始文本
        }
        
        // 如果有属性路径，逐级访问
        for (let i = 0; i < properties.length; i++) {
            const property = properties[i];
            
            if (typeof variableValue !== 'object' || variableValue === null) {
                console.warn(`${variableName}${properties.slice(0, i).map(p => '.' + p).join('')} 不是对象，无法访问属性 ${property}`);
                return match;
            }
            
            if (variableValue[property] === undefined) {
                console.warn(`属性未找到: ${variableName}.${properties.slice(0, i + 1).join('.')}`);
                return match;
            }
            
            variableValue = variableValue[property];
        }
        
        // 返回最终值
        return typeof variableValue === 'object' ? JSON.stringify(variableValue) : String(variableValue);
    });
}

function waitForLifecycleRetry(attempt) {
    return new Promise(resolve => {
        setTimeout(resolve, LIFECYCLE_CALLBACK_BACKOFF_MS * attempt);
    });
}

function lifecycleFailureCode(response, error) {
    const status = response?.status || error?.response?.status;
    return Number.isInteger(status) ? `http_${status}` : 'transport_error';
}

async function sendLifecycleCallback(executionId, event, data) {
    const url = `${API_BASE_URL}/executions/${encodeURIComponent(executionId)}/lifecycle`;
    let lastFailureCode = 'transport_error';

    for (let attempt = 1; attempt <= LIFECYCLE_CALLBACK_MAX_ATTEMPTS; attempt += 1) {
        let response;
        let transportError;
        try {
            response = await lifecycleHttpClient.post(url, data, {
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${runtimeConfig.proxyToken}`
                },
                timeout: 10000
            });
        } catch (error) {
            transportError = error;
        }

        if (!transportError && response?.status >= 200 && response.status < 300) {
            console.log(`✅ 生命周期回调已同步: ${executionId} (${event})`);
            return true;
        }

        lastFailureCode = lifecycleFailureCode(response, transportError);
        if (attempt < LIFECYCLE_CALLBACK_MAX_ATTEMPTS) {
            console.warn(
                `⚠️ 生命周期回调失败，将重试: ${executionId} (${event}) ` +
                `${attempt}/${LIFECYCLE_CALLBACK_MAX_ATTEMPTS} [${lastFailureCode}]`
            );
            await waitForLifecycleRetry(attempt);
        }
    }

    console.error(
        `❌ 生命周期回调重试耗尽: ${executionId} (${event}) ` +
        `${LIFECYCLE_CALLBACK_MAX_ATTEMPTS}/${LIFECYCLE_CALLBACK_MAX_ATTEMPTS} ` +
        `[${lastFailureCode}]`
    );
    recordCallbackExhausted(executionId, event, LIFECYCLE_CALLBACK_MAX_ATTEMPTS);
    return false;
}

// Web系统API集成函数
async function notifyExecutionStart(executionId, testcase, mode) {
    try {
        const totalSteps = Array.isArray(testcase.steps) ? testcase.steps.length : 
                          (typeof testcase.steps === 'string' ? JSON.parse(testcase.steps).length : 0);

        // 通过WebSocket通知前端执行开始
        emitExecutionEvent(executionId, 'execution-start', {
            executionId: executionId,
            testcase: testcase.name,
            mode: mode,
            totalSteps: totalSteps
        });

        const startData = {
            event: 'started',
            status: 'running'
        };
        await sendLifecycleCallback(executionId, 'started', startData);
        
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
        emitExecutionEvent(executionId, 'execution-completed', {
            executionId: executionId,
            testcase: testcase.name,
            status: status,
            mode: mode,
            startTime: startTime,
            endTime: endTime,
            steps: steps,
            errorMessage: errorMessage
        });

        const resultData = {
            event: 'result',
            status: status,
            start_time: startTime,
            end_time: endTime,
            steps: steps || [],
            error_message: errorMessage
        };
        await sendLifecycleCallback(executionId, 'result', resultData);

        console.log(`通知执行结果: ${executionId} -> ${status}`);
        return { success: true };
    } catch (error) {
        console.error(`通知执行结果失败: ${error.message}`);
        return null;
    }
}

function recordCallbackExhausted(executionId, event, attempts) {
    const executionState = executionStates.get(executionId);
    if (!executionState) {
        return;
    }
    if (!Array.isArray(executionState.callbackErrors)) {
        executionState.callbackErrors = [];
    }
    executionState.callbackErrors.push({
        event,
        code: 'lifecycle_callback_exhausted',
        attempts,
        timestamp: new Date().toISOString()
    });
    emitExecutionEvent(executionId, 'lifecycle-callback-failed', {
        executionId,
        event,
        code: 'lifecycle_callback_exhausted',
        attempts
    });
}

function cleanupErrorCategory(error) {
    if (error instanceof TypeError) return 'TypeError';
    if (error instanceof RangeError) return 'RangeError';
    if (error instanceof ReferenceError) return 'ReferenceError';
    if (error instanceof SyntaxError) return 'SyntaxError';
    return error instanceof Error ? 'Error' : 'NonError';
}

function recordCleanupError(executionId, resource) {
    const executionState = executionStates.get(executionId);
    if (!executionState) {
        return;
    }
    if (!Array.isArray(executionState.cleanupErrors)) {
        executionState.cleanupErrors = [];
    }
    executionState.cleanupErrors.push({
        resource,
        code: 'resource_cleanup_failed',
        timestamp: new Date().toISOString()
    });
}

function reportCleanupError(executionId, resource, error) {
    console.error(
        `⚠️ 资源清理失败 [resource_cleanup_failed] ` +
        `resource=${resource} category=${cleanupErrorCategory(error)}`
    );
    recordCleanupError(executionId, resource);
}

async function cleanupOwnedResources(executionId) {
    const ownedPage = page;
    const ownedBrowser = browser;

    // Detach first so a close rejection can never leave damaged resources
    // available for a later execution.
    page = null;
    agent = null;
    browser = null;

    if (ownedPage) {
        try {
            await ownedPage.close();
        } catch (error) {
            reportCleanupError(executionId, 'page', error);
        }
    }

    if (ownedBrowser) {
        try {
            await ownedBrowser.close();
        } catch (error) {
            reportCleanupError(executionId, 'browser', error);
        }
    }
}

// 启动浏览器和页面
async function initBrowser(headless = true, timeoutConfig = {}, enableCache = true, testcaseName = '') {
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
                '--disable-gpu',
                '--disable-background-timer-throttling', // 防止后台节流
                '--disable-backgrounding-occluded-windows', // 防止后台窗口被挂起
                '--disable-renderer-backgrounding', // 防止渲染器后台化
                '--disable-features=TranslateUI', // 禁用翻译UI避免干扰
                '--disable-features=VizDisplayCompositor' // 提高稳定性
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
        hasApiKey: !!config.apiKey,
        enableCache: enableCache
    });
    
    // 根据 MidScene 文档配置缓存
    const agentConfig = { 
        aiModel: config
    };
    
    // 设置缓存相关的环境变量和 cacheId
    if (enableCache) {
        process.env.MIDSCENE_CACHE = '1';
        // 为每个测试用例生成唯一的 cacheId
        // 支持中文字符，并合并连续的连字符
        const normalizedName = testcaseName ? 
            testcaseName
                .replace(/[\s\-_]+/g, '-')  // 空格、连字符、下划线统一替换为单个连字符
                .replace(/[^\u4e00-\u9fa5a-zA-Z0-9\-]/g, '')  // 保留中文、字母、数字和连字符
                .replace(/\-+/g, '-')  // 合并多个连续的连字符
                .replace(/^\-|\-$/g, '')  // 去除首尾的连字符
                .toLowerCase() : 
            `test-${Date.now()}`;
        const cacheId = `playwright-${normalizedName || Date.now()}`;
        agentConfig.cacheId = cacheId;
        console.log('📦 AI缓存已启用');
        console.log(`📦 Cache ID: ${cacheId}`);
    } else {
        delete process.env.MIDSCENE_CACHE;
        console.log('📦 AI缓存已禁用');
    }
    
    agent = new PlaywrightAgent(page, agentConfig);
    
    return { page, agent };
}

io.use((socket, next) => {
    try {
        const payload = verifySocketTicket(
            socket.handshake.auth?.ticket,
            socket.handshake.auth?.executionId,
            socket.handshake.headers.origin
        );
        socket.data.executionId = payload.executionId;
        next();
    } catch (error) {
        const safeError = new Error(error.message === 'BROWSER_SOCKET_DISABLED' ? error.message : 'SOCKET_TICKET_INVALID');
        safeError.data = { code: safeError.message };
        next(safeError);
    }
});

io.on('connection', (socket) => {
    const executionId = socket.data.executionId;
    socket.join(`execution:${executionId}`);
    const state = executionStates.get(executionId);
    if (state) socket.emit('execution-snapshot', safeExecutionSnapshot(executionId, state));
});

// 标准化步骤类型 - 将新的MidSceneJS格式映射到执行引擎识别的格式
function normalizeStepType(stepType) {
    const typeMapping = {
        // 新格式 -> 执行引擎格式
        'goto': 'navigate',
        'aiTap': 'ai_tap',
        'aiInput': 'ai_input',
        'aiAssert': 'ai_assert',
        'aiQuery': 'ai_query',
        'aiString': 'ai_string',
        'aiNumber': 'ai_number',
        'aiBoolean': 'ai_boolean',
        'aiLocate': 'ai_locate',
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
    // 在步骤开始时检查中断标志
    const control = executionControls.get(executionId);
    if (control && control.shouldStop) {
        console.log(`Step ${stepIndex + 1} execution interrupted by user`);
        return {
            status: 'stopped',
            start_time: new Date().toISOString(),
            end_time: new Date().toISOString(),
            duration: 0,
            error_message: '用户中断执行'
        };
    }

    // 支持新旧格式兼容: 新格式使用type字段，旧格式使用action字段
    const stepType = step.type || step.action;
    const params = step.params || {};
    const description = step.description;

    // 标准化步骤类型名称 - 将新的MidSceneJS格式映射到执行引擎识别的格式
    const normalizedAction = normalizeStepType(stepType);

    // 发送步骤开始事件
    emitExecutionEvent(executionId, 'step-start', {
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
                    console.log(`\n[${new Date().toISOString()}] MidScene Step Execution - aiTap`);
                    console.log(`Target: ${clickTarget}`);
                    console.log(`Execution ID: ${executionId}`);
                    console.log(`Step ${stepIndex + 1}/${totalSteps}`);
                    
                    const tapStartTime = Date.now();
                    
                    // 添加重试机制
                    let retryCount = 0;
                    const maxRetries = 3;
                    let lastError = null;
                    
                    while (retryCount < maxRetries) {
                        try {
                            await agent.aiTap(clickTarget);
                            break; // 成功则退出循环
                        } catch (error) {
                            lastError = error;
                            retryCount++;
                            
                            console.error(`尝试 ${retryCount}/${maxRetries} 失败:`, error.message);
                            
                            // 检查是否是AI模型连接错误
                            if (error.message.includes('Connection error') || error.message.includes('AI model service')) {
                                logMessage(executionId, 'warning', `AI模型连接失败，正在重试... (${retryCount}/${maxRetries})`);
                                await page.waitForTimeout(2000 * retryCount); // 递增等待时间
                            } else if (error.message.includes('Protocol error')) {
                                // 鼠标协议错误，可能需要重新初始化
                                logMessage(executionId, 'warning', `鼠标协议错误，尝试使用替代方法...`);
                                // 尝试使用page.click作为备选方案
                                try {
                                    const element = await page.locator(`:text("${clickTarget}")`).first();
                                    await element.click();
                                    break;
                                } catch (fallbackError) {
                                    console.error('备选点击方法也失败:', fallbackError.message);
                                }
                            } else {
                                // 其他错误直接抛出
                                throw error;
                            }
                        }
                    }
                    
                    if (retryCount >= maxRetries) {
                        throw lastError || new Error(`点击操作失败，已重试${maxRetries}次`);
                    }
                    
                    const tapEndTime = Date.now();
                    
                    console.log(`MidScene aiTap completed in ${tapEndTime - tapStartTime}ms\n`);
                    logMessage(executionId, 'info', `点击: ${clickTarget}`);
                }
                break;

            case 'type':
            case 'ai_input':
                const inputTarget = params.locate || params.selector || params.element;
                let inputText = params.text || params.value;
                
                // 解析变量引用
                const context = variableContexts.get(executionId);
                if (context && inputText) {
                    const originalText = inputText;
                    inputText = resolveVariableReferences(inputText, context);
                    if (originalText !== inputText) {
                        logMessage(executionId, 'info', `变量解析: "${originalText}" → "${inputText}"`);
                    }
                }
                
                if (inputTarget && inputText) {
                    console.log(`\n[${new Date().toISOString()}] MidScene Step Execution - aiInput`);
                    console.log(`Text: ${inputText}`);
                    console.log(`Target: ${inputTarget}`);
                    console.log(`Execution ID: ${executionId}`);
                    console.log(`Step ${stepIndex + 1}/${totalSteps}`);
                    
                    const inputStartTime = Date.now();
                    
                    // 添加重试机制
                    let retryCount = 0;
                    const maxRetries = 3;
                    let lastError = null;
                    
                    while (retryCount < maxRetries) {
                        try {
                            await agent.aiInput(inputText, inputTarget);
                            break; // 成功则退出循环
                        } catch (error) {
                            lastError = error;
                            retryCount++;
                            
                            console.error(`输入尝试 ${retryCount}/${maxRetries} 失败:`, error.message);
                            
                            // 检查是否是AI模型连接错误
                            if (error.message.includes('Connection error') || error.message.includes('AI model service')) {
                                logMessage(executionId, 'warning', `AI模型连接失败，正在重试... (${retryCount}/${maxRetries})`);
                                await page.waitForTimeout(2000 * retryCount); // 递增等待时间
                            } else if (error.message.includes('empty content')) {
                                // AI返回空内容，可能是识别失败
                                logMessage(executionId, 'warning', `AI识别失败，等待页面加载后重试...`);
                                await page.waitForTimeout(3000);
                            } else {
                                // 其他错误直接抛出
                                throw error;
                            }
                        }
                    }
                    
                    if (retryCount >= maxRetries) {
                        throw lastError || new Error(`输入操作失败，已重试${maxRetries}次`);
                    }
                    
                    const inputEndTime = Date.now();
                    
                    console.log(`MidScene aiInput completed in ${inputEndTime - inputStartTime}ms\n`);
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
                    console.log(`\n[${new Date().toISOString()}] MidScene Step Execution - aiAssert`);
                    console.log(`Condition: ${assertCondition}`);
                    console.log(`Execution ID: ${executionId}`);
                    console.log(`Step ${stepIndex + 1}/${totalSteps}`);
                    
                    const assertStartTime = Date.now();
                    await agent.aiAssert(assertCondition);
                    const assertEndTime = Date.now();
                    
                    console.log(`MidScene aiAssert completed in ${assertEndTime - assertStartTime}ms\n`);
                    logMessage(executionId, 'info', `断言: ${assertCondition}`);
                }
                break;

            case 'ai_query':
                const queryText = params.query;
                const dataDemand = params.dataDemand;
                const outputVariable = step.output_variable;
                
                if (queryText && dataDemand) {
                    // 将dataDemand结构描述拼接到query字符串末尾
                    const combinedQuery = `${queryText}${dataDemand}`;
                    
                    console.log(`\n[${new Date().toISOString()}] MidScene Step Execution - aiQuery`);
                    console.log(`Original Query: ${queryText}`);
                    console.log(`DataDemand: ${dataDemand}`);
                    console.log(`Combined Query: ${combinedQuery}`);
                    console.log(`Output Variable: ${outputVariable || 'None'}`);
                    console.log(`Execution ID: ${executionId}`);
                    console.log(`Step ${stepIndex + 1}/${totalSteps}`);
                    
                    const queryStartTime = Date.now();
                    
                    // 添加重试机制
                    let retryCount = 0;
                    const maxRetries = 3;
                    let lastError = null;
                    let queryResult = null;
                    
                    while (retryCount < maxRetries) {
                        try {
                            // 使用MidSceneJS的aiQuery方法，传入拼接后的查询字符串
                            queryResult = await agent.aiQuery(combinedQuery);
                            break; // 成功则退出循环
                        } catch (error) {
                            lastError = error;
                            retryCount++;
                            
                            console.error(`aiQuery尝试 ${retryCount}/${maxRetries} 失败:`, error.message);
                            
                            // 检查是否是AI模型连接错误
                            if (error.message.includes('Connection error') || error.message.includes('AI model service')) {
                                logMessage(executionId, 'warning', `AI模型连接失败，正在重试... (${retryCount}/${maxRetries})`);
                                await page.waitForTimeout(2000 * retryCount); // 递增等待时间
                            } else {
                                // 其他错误直接抛出
                                throw error;
                            }
                        }
                    }
                    
                    if (retryCount >= maxRetries) {
                        throw lastError || new Error(`aiQuery操作失败，已重试${maxRetries}次`);
                    }
                    
                    const queryEndTime = Date.now();
                    
                    console.log(`MidScene aiQuery completed in ${queryEndTime - queryStartTime}ms`);
                    console.log(`Query Result:`, JSON.stringify(queryResult, null, 2));
                    
                    // 在日志中显示提取到的变量值
                    const resultStr = typeof queryResult === 'object' ? JSON.stringify(queryResult, null, 2) : String(queryResult);
                    logMessage(executionId, 'info', `AI数据提取完成，提取结果: ${resultStr}`);
                    
                    // 存储变量（如果指定了output_variable）
                    if (outputVariable) {
                        let context = variableContexts.get(executionId);
                        if (!context) {
                            context = {};
                            variableContexts.set(executionId, context);
                        }
                        
                        // 使用用户指定的变量名存储结果
                        context[outputVariable] = queryResult;
                        logMessage(executionId, 'info', `变量已存储: ${outputVariable} = ${resultStr}`);
                    } else {
                        // 兼容性：如果没有指定output_variable，使用step_X_result格式
                        let context = variableContexts.get(executionId);
                        if (!context) {
                            context = {};
                            variableContexts.set(executionId, context);
                        }
                        
                        const stepVariableName = `step_${stepIndex + 1}_result`;
                        context[stepVariableName] = queryResult;
                        logMessage(executionId, 'info', `变量已存储（兼容模式）: ${stepVariableName} = ${resultStr}`);
                    }
                }
                break;

            case 'ai_string':
                const stringQuery = params.query;
                const stringOutputVariable = step.output_variable;
                
                if (stringQuery) {
                    console.log(`\n[${new Date().toISOString()}] MidScene Step Execution - aiString`);
                    console.log(`Query: ${stringQuery}`);
                    console.log(`Output Variable: ${stringOutputVariable || 'None'}`);
                    console.log(`Execution ID: ${executionId}`);
                    console.log(`Step ${stepIndex + 1}/${totalSteps}`);
                    
                    const stringStartTime = Date.now();
                    
                    // 添加重试机制
                    let retryCount = 0;
                    const maxRetries = 3;
                    let lastError = null;
                    let stringResult = null;
                    
                    while (retryCount < maxRetries) {
                        try {
                            // 使用MidSceneJS的aiString方法
                            stringResult = await agent.aiString(stringQuery);
                            break; // 成功则退出循环
                        } catch (error) {
                            lastError = error;
                            retryCount++;
                            
                            console.error(`aiString尝试 ${retryCount}/${maxRetries} 失败:`, error.message);
                            
                            // 检查是否是AI模型连接错误
                            if (error.message.includes('Connection error') || error.message.includes('AI model service')) {
                                logMessage(executionId, 'warning', `AI模型连接失败，正在重试... (${retryCount}/${maxRetries})`);
                                await page.waitForTimeout(2000 * retryCount); // 递增等待时间
                            } else {
                                // 其他错误直接抛出
                                throw error;
                            }
                        }
                    }
                    
                    if (retryCount >= maxRetries) {
                        throw lastError || new Error(`aiString操作失败，已重试${maxRetries}次`);
                    }
                    
                    const stringEndTime = Date.now();
                    
                    console.log(`MidScene aiString completed in ${stringEndTime - stringStartTime}ms`);
                    console.log(`String Result: "${stringResult}"`);
                    
                    // 在日志中显示提取到的字符串值
                    logMessage(executionId, 'info', `AI字符串提取完成，提取结果: "${stringResult}"`);
                    
                    // 存储变量（如果指定了output_variable）
                    if (stringOutputVariable) {
                        let context = variableContexts.get(executionId);
                        if (!context) {
                            context = {};
                            variableContexts.set(executionId, context);
                        }
                        
                        // 使用用户指定的变量名存储结果
                        context[stringOutputVariable] = stringResult;
                        logMessage(executionId, 'info', `变量已存储: ${stringOutputVariable} = "${stringResult}"`);
                    } else {
                        // 兼容性：如果没有指定output_variable，使用step_X_result格式
                        let context = variableContexts.get(executionId);
                        if (!context) {
                            context = {};
                            variableContexts.set(executionId, context);
                        }
                        
                        const stepVariableName = `step_${stepIndex + 1}_result`;
                        context[stepVariableName] = stringResult;
                        logMessage(executionId, 'info', `变量已存储（兼容模式）: ${stepVariableName} = "${stringResult}"`);
                    }
                }
                break;

            case 'ai_number':
                const numberQuery = params.query;
                const numberOutputVariable = step.output_variable;
                
                if (numberQuery) {
                    console.log(`\n[${new Date().toISOString()}] MidScene Step Execution - aiNumber`);
                    console.log(`Query: ${numberQuery}`);
                    console.log(`Output Variable: ${numberOutputVariable || 'None'}`);
                    console.log(`Execution ID: ${executionId}`);
                    console.log(`Step ${stepIndex + 1}/${totalSteps}`);
                    
                    const numberStartTime = Date.now();
                    
                    // 添加重试机制
                    let retryCount = 0;
                    const maxRetries = 3;
                    let lastError = null;
                    let numberResult = null;
                    
                    while (retryCount < maxRetries) {
                        try {
                            // 使用MidSceneJS的aiNumber方法
                            numberResult = await agent.aiNumber(numberQuery);
                            break; // 成功则退出循环
                        } catch (error) {
                            lastError = error;
                            retryCount++;
                            
                            console.error(`aiNumber尝试 ${retryCount}/${maxRetries} 失败:`, error.message);
                            
                            // 检查是否是AI模型连接错误
                            if (error.message.includes('Connection error') || error.message.includes('AI model service')) {
                                logMessage(executionId, 'warning', `AI模型连接失败，正在重试... (${retryCount}/${maxRetries})`);
                                await page.waitForTimeout(2000 * retryCount); // 递增等待时间
                            } else {
                                // 其他错误直接抛出
                                throw error;
                            }
                        }
                    }
                    
                    if (retryCount >= maxRetries) {
                        throw lastError || new Error(`aiNumber操作失败，已重试${maxRetries}次`);
                    }
                    
                    const numberEndTime = Date.now();
                    
                    console.log(`MidScene aiNumber completed in ${numberEndTime - numberStartTime}ms`);
                    console.log(`Number Result: ${numberResult}`);
                    
                    // 在日志中显示提取到的数字值
                    logMessage(executionId, 'info', `AI数字提取完成，提取结果: ${numberResult}`);
                    
                    // 存储变量（如果指定了output_variable）
                    if (numberOutputVariable) {
                        let context = variableContexts.get(executionId);
                        if (!context) {
                            context = {};
                            variableContexts.set(executionId, context);
                        }
                        
                        // 使用用户指定的变量名存储结果
                        context[numberOutputVariable] = numberResult;
                        logMessage(executionId, 'info', `变量已存储: ${numberOutputVariable} = ${numberResult}`);
                    } else {
                        // 兼容性：如果没有指定output_variable，使用step_X_result格式
                        let context = variableContexts.get(executionId);
                        if (!context) {
                            context = {};
                            variableContexts.set(executionId, context);
                        }
                        
                        const stepVariableName = `step_${stepIndex + 1}_result`;
                        context[stepVariableName] = numberResult;
                        logMessage(executionId, 'info', `变量已存储（兼容模式）: ${stepVariableName} = ${numberResult}`);
                    }
                }
                break;

            case 'ai_boolean':
                const booleanQuery = params.query;
                const booleanOutputVariable = step.output_variable;
                
                if (booleanQuery) {
                    console.log(`\n[${new Date().toISOString()}] MidScene Step Execution - aiBoolean`);
                    console.log(`Query: ${booleanQuery}`);
                    console.log(`Output Variable: ${booleanOutputVariable || 'None'}`);
                    console.log(`Execution ID: ${executionId}`);
                    console.log(`Step ${stepIndex + 1}/${totalSteps}`);
                    
                    const booleanStartTime = Date.now();
                    
                    // 添加重试机制
                    let retryCount = 0;
                    const maxRetries = 3;
                    let lastError = null;
                    let booleanResult = null;
                    
                    while (retryCount < maxRetries) {
                        try {
                            // 使用MidSceneJS的aiBoolean方法
                            booleanResult = await agent.aiBoolean(booleanQuery);
                            break; // 成功则退出循环
                        } catch (error) {
                            lastError = error;
                            retryCount++;
                            
                            console.error(`aiBoolean尝试 ${retryCount}/${maxRetries} 失败:`, error.message);
                            
                            // 检查是否是AI模型连接错误
                            if (error.message.includes('Connection error') || error.message.includes('AI model service')) {
                                logMessage(executionId, 'warning', `AI模型连接失败，正在重试... (${retryCount}/${maxRetries})`);
                                await page.waitForTimeout(2000 * retryCount); // 递增等待时间
                            } else {
                                // 其他错误直接抛出
                                throw error;
                            }
                        }
                    }
                    
                    if (retryCount >= maxRetries) {
                        throw lastError || new Error(`aiBoolean操作失败，已重试${maxRetries}次`);
                    }
                    
                    const booleanEndTime = Date.now();
                    
                    console.log(`MidScene aiBoolean completed in ${booleanEndTime - booleanStartTime}ms`);
                    console.log(`Boolean Result: ${booleanResult}`);
                    
                    // 在日志中显示提取到的布尔值
                    logMessage(executionId, 'info', `AI布尔值提取完成，提取结果: ${booleanResult}`);
                    
                    // 存储变量（如果指定了output_variable）
                    if (booleanOutputVariable) {
                        let context = variableContexts.get(executionId);
                        if (!context) {
                            context = {};
                            variableContexts.set(executionId, context);
                        }
                        
                        // 使用用户指定的变量名存储结果
                        context[booleanOutputVariable] = booleanResult;
                        logMessage(executionId, 'info', `变量已存储: ${booleanOutputVariable} = ${booleanResult}`);
                    } else {
                        // 兼容性：如果没有指定output_variable，使用step_X_result格式
                        let context = variableContexts.get(executionId);
                        if (!context) {
                            context = {};
                            variableContexts.set(executionId, context);
                        }
                        
                        const stepVariableName = `step_${stepIndex + 1}_result`;
                        context[stepVariableName] = booleanResult;
                        logMessage(executionId, 'info', `变量已存储（兼容模式）: ${stepVariableName} = ${booleanResult}`);
                    }
                }
                break;

            case 'ai_locate':
                const locateQuery = params.locate;
                const locateOutputVariable = step.output_variable;
                
                if (locateQuery) {
                    console.log(`\n[${new Date().toISOString()}] MidScene Step Execution - aiLocate`);
                    console.log(`Locate: ${locateQuery}`);
                    console.log(`Output Variable: ${locateOutputVariable || 'None'}`);
                    console.log(`Execution ID: ${executionId}`);
                    console.log(`Step ${stepIndex + 1}/${totalSteps}`);
                    
                    const locateStartTime = Date.now();
                    
                    // 添加重试机制
                    let retryCount = 0;
                    const maxRetries = 3;
                    let lastError = null;
                    let locateResult = null;
                    
                    while (retryCount < maxRetries) {
                        try {
                            // 使用MidSceneJS的aiLocate方法
                            locateResult = await agent.aiLocate(locateQuery);
                            break; // 成功则退出循环
                        } catch (error) {
                            lastError = error;
                            retryCount++;
                            
                            console.error(`aiLocate尝试 ${retryCount}/${maxRetries} 失败:`, error.message);
                            
                            // 检查是否是AI模型连接错误
                            if (error.message.includes('Connection error') || error.message.includes('AI model service')) {
                                logMessage(executionId, 'warning', `AI模型连接失败，正在重试... (${retryCount}/${maxRetries})`);
                                await page.waitForTimeout(2000 * retryCount); // 递增等待时间
                            } else {
                                // 其他错误直接抛出
                                throw error;
                            }
                        }
                    }
                    
                    if (retryCount >= maxRetries) {
                        throw lastError || new Error(`aiLocate操作失败，已重试${maxRetries}次`);
                    }
                    
                    const locateEndTime = Date.now();
                    
                    console.log(`MidScene aiLocate completed in ${locateEndTime - locateStartTime}ms`);
                    console.log(`Locate Result:`, locateResult);
                    
                    // 在日志中显示定位到的坐标
                    const locateDisplay = locateResult ? 
                        `坐标: (${locateResult.x}, ${locateResult.y})` : 
                        '未找到元素';
                    logMessage(executionId, 'info', `AI元素定位完成，${locateDisplay}`);
                    
                    // 存储变量（如果指定了output_variable）
                    if (locateOutputVariable) {
                        let context = variableContexts.get(executionId);
                        if (!context) {
                            context = {};
                            variableContexts.set(executionId, context);
                        }
                        
                        // 使用用户指定的变量名存储结果
                        context[locateOutputVariable] = locateResult;
                        logMessage(executionId, 'info', `变量已存储: ${locateOutputVariable} = ${JSON.stringify(locateResult)}`);
                    } else {
                        // 兼容性：如果没有指定output_variable，使用step_X_result格式
                        let context = variableContexts.get(executionId);
                        if (!context) {
                            context = {};
                            variableContexts.set(executionId, context);
                        }
                        
                        const stepVariableName = `step_${stepIndex + 1}_result`;
                        context[stepVariableName] = locateResult;
                        logMessage(executionId, 'info', `变量已存储（兼容模式）: ${stepVariableName} = ${JSON.stringify(locateResult)}`);
                    }
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
                const screenshotPath = resolveArtifactPath(OUTPUT_ROOT, executionId, `step-${stepIndex}.png`);
                fs.mkdirSync(path.dirname(screenshotPath), { recursive: true });
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
                    console.log(`\n[${new Date().toISOString()}] MidScene Step Execution - aiWaitFor`);
                    console.log(`Target: ${waitTarget}`);
                    console.log(`Timeout: ${waitTimeout}ms`);
                    console.log(`Execution ID: ${executionId}`);
                    console.log(`Step ${stepIndex + 1}/${totalSteps}`);
                    
                    const waitStartTime = Date.now();
                    await agent.aiWaitFor(waitTarget, { timeout: waitTimeout });
                    const waitEndTime = Date.now();
                    
                    console.log(`MidScene aiWaitFor completed in ${waitEndTime - waitStartTime}ms\n`);
                    logMessage(executionId, 'info', `等待元素出现: ${waitTarget}`);
                }
                break;

            case 'ai':
                // AI智能操作 - 使用通用的AI方法
                const aiPrompt = params.prompt || params.instruction || description || stepType;
                console.log(`\n[${new Date().toISOString()}] MidScene Step Execution - ai`);
                console.log(`Prompt: ${aiPrompt}`);
                console.log(`Params:`, JSON.stringify(params, null, 2));
                console.log(`Execution ID: ${executionId}`);
                console.log(`Step ${stepIndex + 1}/${totalSteps}`);
                
                const aiStartTime = Date.now();
                
                // 添加重试机制
                let retryCount = 0;
                const maxRetries = 3;
                let lastError = null;
                
                while (retryCount < maxRetries) {
                    try {
                        await agent.ai(aiPrompt);
                        break; // 成功则退出循环
                    } catch (error) {
                        lastError = error;
                        retryCount++;
                        
                        console.error(`AI操作尝试 ${retryCount}/${maxRetries} 失败:`, error.message);
                        
                        // 检查是否是AI模型连接错误
                        if (error.message.includes('Connection error') || error.message.includes('AI model service')) {
                            logMessage(executionId, 'warning', `AI模型连接失败，正在重试... (${retryCount}/${maxRetries})`);
                            await page.waitForTimeout(2000 * retryCount); // 递增等待时间
                        } else if (error.message.includes('empty content')) {
                            // AI返回空内容，可能是识别失败
                            logMessage(executionId, 'warning', `AI识别失败，等待页面加载后重试...`);
                            await page.waitForTimeout(3000);
                        } else {
                            // 其他错误直接抛出
                            throw error;
                        }
                    }
                }
                
                if (retryCount >= maxRetries) {
                    throw lastError || new Error(`AI操作失败，已重试${maxRetries}次`);
                }
                const aiEndTime = Date.now();
                
                console.log(`MidScene ai completed in ${aiEndTime - aiStartTime}ms\n`);
                logMessage(executionId, 'info', `AI智能操作: ${aiPrompt}`);
                break;

            case 'ai_action':
                const aiActionPrompt = params.prompt || params.instruction || description || stepType;
                console.log(`\n[${new Date().toISOString()}] MidScene Step Execution - ai_action`);
                console.log(`Prompt: ${aiActionPrompt}`);
                console.log(`Execution ID: ${executionId}`);
                console.log(`Step ${stepIndex + 1}/${totalSteps}`);
                
                const aiActionStartTime = Date.now();
                await agent.aiAction(aiActionPrompt);
                const aiActionEndTime = Date.now();
                
                console.log(`MidScene aiAction completed in ${aiActionEndTime - aiActionStartTime}ms\n`);
                logMessage(executionId, 'info', `AI操作规划: ${aiActionPrompt}`);
                break;

            default:
                // 通用AI操作 - 优先使用params中的prompt或instruction
                const instruction = params.prompt || params.instruction || description || stepType;
                console.log(`\n[${new Date().toISOString()}] MidScene Step Execution - Default Action`);
                console.log(`Action Type: ${normalizedAction}`);
                console.log(`Instruction: ${instruction}`);
                console.log(`Params:`, JSON.stringify(params, null, 2));
                console.log(`Description: ${description}`);
                console.log(`Execution ID: ${executionId}`);
                console.log(`Step ${stepIndex + 1}/${totalSteps}`);
                
                const defaultStartTime = Date.now();
                await agent.ai(instruction);
                const defaultEndTime = Date.now();
                
                console.log(`MidScene default action completed in ${defaultEndTime - defaultStartTime}ms\n`);
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
        emitExecutionEvent(executionId, 'step-failed', {
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
async function executeTestCaseAsync(testcase, mode, executionId, timeoutConfig = {}, enableCache = true) {
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
            logs: [],  // 收集日志数据
            callbackErrors: [],
            cleanupErrors: []
        };
        
        // 更新执行状态
        executionStates.set(executionId, currentExecution);
        
        // 设置执行控制标志
        executionControls.set(executionId, { shouldStop: false });

        // 通知Web系统执行开始
        await notifyExecutionStart(executionId, testcase, mode);

        // 发送执行开始事件
        emitExecutionEvent(executionId, 'execution-start', {
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

        console.log(`\n[${new Date().toISOString()}] Test Case Execution Details`);
        console.log(`Test Case: ${testcase.name}`);
        console.log(`Execution ID: ${executionId}`);
        console.log(`Mode: ${mode}`);
        console.log(`Cache Enabled: ${enableCache}`);
        console.log(`Total Steps: ${steps.length}`);
        console.log('\nSteps Overview:');
        steps.forEach((step, index) => {
            const stepType = step.type || step.action;
            const description = step.description || stepType;
            console.log(`  ${index + 1}. [${stepType}] ${description}`);
        });
        console.log('');

        logMessage(executionId, 'info', `共 ${steps.length} 个步骤`);

        // 初始化步骤结果数组
        const stepsResult = [];
        
        // 初始化浏览器
        const headless = mode === 'headless';
        console.log(`\n[${new Date().toISOString()}] Browser Mode Configuration`);
        console.log(`Received mode: "${mode}"`);
        console.log(`Headless value: ${headless}`);
        console.log(`Will launch browser in: ${headless ? 'HEADLESS' : 'VISIBLE'} mode\n`);
        
        logMessage(executionId, 'info', `初始化浏览器 (${headless ? '无头模式' : '可视模式'})`);

        const { page, agent } = await initBrowser(headless, timeoutConfig, enableCache, testcase.name);

        // 执行每个步骤
        for (let i = 0; i < steps.length; i++) {
            // 检查是否应该停止执行
            const control = executionControls.get(executionId);
            console.log(`Checking stop flag for execution ${executionId}, step ${i + 1}:`, control);
            if (control && control.shouldStop) {
                console.log(`Execution ${executionId} interrupted at step ${i + 1}`);
                logMessage(executionId, 'warning', '执行被用户中断');
                throw new Error('执行被用户中断');
            }
            
            const step = steps[i];
            
            // 检查步骤是否被跳过
            if (step.skip) {
                console.log(`Skipping step ${i + 1}: ${step.description || step.action}`);
                logMessage(executionId, 'warning', `步骤 ${i + 1} 被跳过: ${step.description || step.action}`);
                
                // 发送步骤跳过事件
                emitExecutionEvent(executionId, 'step-skipped', {
                    executionId,
                    stepIndex: i,
                    totalSteps: steps.length,
                    description: step.description || step.action,
                    message: '此步骤已被标记为跳过'
                });
                
                // 记录跳过的步骤结果到stepsResult
                const skipTime = new Date().toISOString();
                stepsResult.push({
                    step_index: i,
                    description: step.description || step.action,
                    status: 'skipped',
                    start_time: skipTime,
                    end_time: skipTime,
                    duration: 0,
                    error_message: '步骤被跳过'
                });
                
                // 同样需要记录到executionState.steps中以便统计
                const executionState = executionStates.get(executionId);
                if (executionState) {
                    const stepData = {
                        index: i,
                        description: step.description || step.action || 'Unknown Step',
                        status: 'skipped',
                        start_time: skipTime,
                        end_time: skipTime,
                        duration: 0,
                        stepType: step.type || step.action,
                        params: step.params || {},
                        error_message: '步骤被跳过'
                    };
                    executionState.steps.push(stepData);
                }
                
                continue; // 跳过此步骤，继续下一个
            }

            // 发送步骤进度
            emitExecutionEvent(executionId, 'step-progress', {
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
                emitExecutionEvent(executionId, 'step-completed', {
                    executionId,
                    stepIndex: i,
                    totalSteps: steps.length,
                    success: true,
                    result: stepResult
                });
            } else if (stepResult.status === 'stopped') {
                // 步骤被中断
                logMessage(executionId, 'warning', `步骤 ${i + 1} 被用户中断`);
                
                // 发送步骤中断事件
                emitExecutionEvent(executionId, 'step-completed', {
                    executionId,
                    stepIndex: i,
                    totalSteps: steps.length,
                    success: false,
                    error: '用户中断执行'
                });
                
                // 立即退出执行循环
                break;
            } else {
                // 步骤执行失败
                logMessage(executionId, 'error', `步骤 ${i + 1} 执行失败: ${stepResult.error_message}`);
                
                // 发送步骤失败事件
                emitExecutionEvent(executionId, 'step-completed', {
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

                emitExecutionEvent(executionId, 'screenshot-taken', {
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
        const skippedSteps = executionState.steps.filter(step => step.status === 'skipped').length;
        const executedSteps = totalSteps - skippedSteps; // 实际执行的步骤数
        
        // 优化成功判断逻辑：如果实际执行的步骤都成功，则判断为成功（跳过的步骤不影响结果）
        const control = executionControls.get(executionId);
        const overallStatus = (executionState.status === 'stopped' || control?.shouldStop)
            ? 'stopped'
            : (failedSteps === 0 && executedSteps > 0) ? 'success'
                : 'failed';
        executionState.status = overallStatus;

        // 生成更详细的消息
        let message = '';
        if (overallStatus === 'success') {
            message = skippedSteps > 0 
                ? `测试执行完成！执行步骤 ${successSteps}/${executedSteps} 全部成功，跳过 ${skippedSteps} 个步骤`
                : `测试执行完成！所有 ${successSteps} 个步骤全部成功`;
        } else if (overallStatus === 'stopped') {
            message = '测试执行已停止';
        } else {
            message = `测试执行完成，但有 ${failedSteps} 个步骤失败`;
        }

        // 发送执行完成事件
        emitExecutionEvent(executionId, 'execution-completed', {
            executionId,
            status: overallStatus,
            message: message,
            duration: executionState.duration,
            totalSteps: totalSteps,
            successSteps: successSteps,
            failedSteps: failedSteps,
            skippedSteps: skippedSteps,
            executedSteps: executedSteps,
            timestamp: new Date().toISOString()
        });

        const statusMessage = `${message}，耗时: ${Math.round(executionState.duration / 1000)}秒`;
        
        logMessage(executionId, overallStatus === 'success' ? 'success' : 'warning', statusMessage);
        
        // 检查并通知MidScene生成的报告
        await checkAndNotifyMidsceneReport(executionId, testcase, executionState);

        // 通知Web系统执行完成
        await notifyExecutionResult(executionId, testcase, mode, overallStatus, executionState.steps);

    } catch (error) {
        console.error('测试执行失败:', error);

        // 更新执行状态
        const executionState = executionStates.get(executionId);
        const terminalStatus = executionState?.status === 'stopped' ? 'stopped' : 'failed';
        if (executionState) {
            executionState.status = terminalStatus;
            executionState.endTime = new Date();
            executionState.error = error.message;
        }

        // 发送执行错误事件
        emitExecutionEvent(executionId, 'execution-completed', {
            executionId,
            status: terminalStatus,
            error: error.message,
            timestamp: new Date().toISOString()
        });

        logMessage(executionId, 'error', `测试执行失败: ${error.message}`);

        // 通知Web系统执行失败
        await notifyExecutionResult(executionId, testcase, mode, terminalStatus, executionState?.steps || [], error.message);
    } finally {
        // 清理执行控制标志
        executionControls.delete(executionId);

        // Admission remains owned until this cleanup finishes. Resource globals
        // are detached before close so rejected cleanup cannot be reused.
        await cleanupOwnedResources(executionId);
    }
}

// API端点

// 执行完整测试用例
app.post('/api/execute-testcase', async (req, res) => {
    try {
        const { executionId, testcase, mode = 'headless', timeout_settings = {}, enable_cache = true } = req.body;

        // 详细记录请求信息
        console.log(`\n[${new Date().toISOString()}] MidScene API Request - /api/execute-testcase`);
        console.log('Full Request Body:', JSON.stringify(req.body, null, 2));
        console.log('Extracted mode:', mode);
        console.log('Request Body Summary:', JSON.stringify({
            testcase: {
                id: testcase?.id,
                name: testcase?.name,
                stepsCount: Array.isArray(testcase?.steps) ? testcase.steps.length : 
                            (typeof testcase?.steps === 'string' ? JSON.parse(testcase.steps).length : 0)
            },
            mode,
            timeout_settings
        }, null, 2));

        if (typeof executionId !== 'string' || !executionId.trim()) {
            console.error('Error: Missing or invalid executionId');
            return res.status(400).json({
                success: false,
                error: 'executionId必须是非空字符串'
            });
        }

        if (!testcase) {
            console.error('Error: Missing test case data');
            return res.status(400).json({
                success: false,
                error: '缺少测试用例数据'
            });
        }

        if (runtimeResetting || activeExecutionId !== null) {
            return res.status(409).json({
                success: false,
                error: runtimeResetting
                    ? '执行器正在重置'
                    : activeExecutionId === executionId
                    ? '该executionId正在执行'
                    : `执行器正忙，当前executionId: ${activeExecutionId}`,
                activeExecutionId
            });
        }

        if (executionStates.get(executionId)?.status === 'running') {
            return res.status(409).json({
                success: false,
                error: '该executionId正在执行'
            });
        }

        // 解析超时设置
        const timeoutConfig = {
            page_timeout: timeout_settings.page_timeout || 30000,
            action_timeout: timeout_settings.action_timeout || 30000,
            navigation_timeout: timeout_settings.navigation_timeout || 30000
        };
        
        console.log('📋 接收到的超时设置:', JSON.stringify(timeoutConfig, null, 2));

        // 异步执行，立即返回执行ID
        activeExecutionId = executionId;
        const ownerPromise = executeTestCaseAsync(testcase, mode, executionId, timeoutConfig, enable_cache);
        activeExecutionPromise = ownerPromise;
        ownerPromise
            .catch(error => {
                console.error('异步执行错误:', error);
            })
            .finally(() => {
                if (activeExecutionPromise === ownerPromise) {
                    activeExecutionPromise = null;
                    activeExecutionId = null;
                }
            });

        console.log(`Test case execution started successfully\n`);

        res.json({
            success: true,
            executionId,
            message: '测试用例开始执行',
            timestamp: new Date().toISOString()
        });

    } catch (error) {
        console.error(`[${new Date().toISOString()}] MidScene API Error - /api/execute-testcase`);
        console.error('Error:', error.message);
        console.error('Stack:', error.stack);
        
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

    res.json({ success: true, ...safeExecutionSnapshot(executionId, executionState) });
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

    console.log(`\n[${new Date().toISOString()}] Stop Execution Request`);
    console.log(`Execution ID: ${executionId}`);

    if (!executionState) {
        console.log('Execution not found');
        return res.status(404).json({
            success: false,
            error: '执行记录不存在'
        });
    }

    if (executionState.status !== 'running') {
        console.log(`Execution already ${executionState.status}`);
        return res.status(409).json({
            success: false,
            error: `执行已结束，当前状态: ${executionState.status}`
        });
    }

    if (activeExecutionId !== executionId) {
        return res.status(409).json({
            success: false,
            error: '该executionId不是当前活动执行'
        });
    }

    const control = executionControls.get(executionId);
    if (!control) {
        return res.status(409).json({
            success: false,
            error: '活动执行缺少控制状态'
        });
    }

    try {
        // 设置中断标志
        control.shouldStop = true;
        console.log(`Stop flag set successfully for execution ${executionId}`);
        console.log('Current executionControls:', Array.from(executionControls.entries()));

        // 更新状态为已停止
        executionState.status = 'stopped';
        executionState.endTime = new Date();

        // 发送停止事件
        emitExecutionEvent(executionId, 'execution-stopped', {
            executionId,
            timestamp: new Date().toISOString()
        });

        logMessage(executionId, 'warning', '执行已被用户停止');

        console.log('Execution stopped successfully\n');

        res.json({
            success: true,
            message: '执行已停止'
        });

    } catch (error) {
        console.error('Error stopping execution:', error.message);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// 获取服务器状态
app.get('/api/status', (req, res) => {
    res.json({
        success: true,
        status: !runtimeResetting && activeExecutionId === null ? 'ready' : 'busy',
        ...(activeExecutionId ? { activeExecutionId } : {})
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
        
        // 详细记录请求信息
        console.log(`\n[${new Date().toISOString()}] MidScene API Request - /ai-input`);
        console.log('Request Body:', JSON.stringify(req.body, null, 2));
        console.log('Text:', text);
        console.log('Locate:', locate);
        
        const { agent } = await initBrowser();
        
        console.log(`Sending to MidScene: agent.aiInput("${text}", "${locate}")`);
        
        const startTime = Date.now();
        const result = await agent.aiInput(text, locate);
        const endTime = Date.now();
        
        console.log(`MidScene Response Time: ${endTime - startTime}ms`);
        console.log('MidScene Response:', JSON.stringify(result, null, 2));
        console.log('Request completed successfully\n');
        
        res.json({ 
            success: true, 
            result 
        });
    } catch (error) {
        console.error(`[${new Date().toISOString()}] MidScene API Error - /ai-input`);
        console.error('Error:', error.message);
        console.error('Stack:', error.stack);
        
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
        
        // 详细记录请求信息
        console.log(`\n[${new Date().toISOString()}] MidScene API Request - /ai-tap`);
        console.log('Request Body:', JSON.stringify(req.body, null, 2));
        console.log('Prompt:', prompt);
        
        const { agent } = await initBrowser();
        
        console.log(`Sending to MidScene: agent.aiTap("${prompt}")`);
        
        const startTime = Date.now();
        const result = await agent.aiTap(prompt);
        const endTime = Date.now();
        
        console.log(`MidScene Response Time: ${endTime - startTime}ms`);
        console.log('MidScene Response:', JSON.stringify(result, null, 2));
        console.log('Request completed successfully\n');
        
        res.json({ 
            success: true, 
            result 
        });
    } catch (error) {
        console.error(`[${new Date().toISOString()}] MidScene API Error - /ai-tap`);
        console.error('Error:', error.message);
        console.error('Stack:', error.stack);
        
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
        
        // 详细记录请求信息
        console.log(`\n[${new Date().toISOString()}] MidScene API Request - /ai-assert`);
        console.log('Request Body:', JSON.stringify(req.body, null, 2));
        console.log('Prompt:', prompt);
        
        const { agent } = await initBrowser();
        
        console.log(`Sending to MidScene: agent.aiAssert("${prompt}")`);
        
        const startTime = Date.now();
        await agent.aiAssert(prompt);
        const endTime = Date.now();
        
        console.log(`MidScene Response Time: ${endTime - startTime}ms`);
        console.log('Assertion passed successfully');
        console.log('Request completed successfully\n');
        
        res.json({ 
            success: true, 
            result: true 
        });
    } catch (error) {
        console.error(`[${new Date().toISOString()}] MidScene API Error - /ai-assert`);
        console.error('Error:', error.message);
        console.error('Stack:', error.stack);
        
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
        
        // 详细记录请求信息
        console.log(`\n[${new Date().toISOString()}] MidScene API Request - /ai-action`);
        console.log('Request Body:', JSON.stringify(req.body, null, 2));
        console.log('Prompt:', prompt);
        
        const { agent } = await initBrowser();
        
        console.log(`Sending to MidScene: agent.aiAction("${prompt}")`);
        
        const startTime = Date.now();
        const result = await agent.aiAction(prompt);
        const endTime = Date.now();
        
        console.log(`MidScene Response Time: ${endTime - startTime}ms`);
        console.log('MidScene Response:', JSON.stringify(result, null, 2));
        console.log('Request completed successfully\n');
        
        res.json({ 
            success: true, 
            result 
        });
    } catch (error) {
        console.error(`[${new Date().toISOString()}] MidScene API Error - /ai-action`);
        console.error('Error:', error.message);
        console.error('Stack:', error.stack);
        
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
        
        // 详细记录请求信息
        console.log(`\n[${new Date().toISOString()}] MidScene API Request - /ai-wait-for`);
        console.log('Request Body:', JSON.stringify(req.body, null, 2));
        console.log('Prompt:', prompt);
        console.log('Timeout:', timeout);
        
        const { agent } = await initBrowser();
        
        console.log(`Sending to MidScene: agent.aiWaitFor("${prompt}", { timeout: ${timeout} })`);
        
        const startTime = Date.now();
        const result = await agent.aiWaitFor(prompt, { timeout });
        const endTime = Date.now();
        
        console.log(`MidScene Response Time: ${endTime - startTime}ms`);
        console.log('MidScene Response:', JSON.stringify(result, null, 2));
        console.log('Request completed successfully\n');
        
        res.json({ 
            success: true, 
            result 
        });
    } catch (error) {
        console.error(`[${new Date().toISOString()}] MidScene API Error - /ai-wait-for`);
        console.error('Error:', error.message);
        console.error('Stack:', error.stack);
        
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
        const { executionId, serverName } = req.body;
        const screenshotPath = resolveArtifactPath(OUTPUT_ROOT, executionId, serverName);
        fs.mkdirSync(path.dirname(screenshotPath), { recursive: true });
        const { page } = await initBrowser();
        
        await page.screenshot({ path: screenshotPath });
        
        res.json({ 
            success: true, 
            executionId,
            serverName
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
        status: 'ok'
    });
});

// AI模型响应时间测试
app.post('/ai-test', async (req, res) => {
    try {
        console.log('🤖 开始测试AI模型响应时间...');
        
        // 获取当前配置的模型信息
        const modelName = process.env.MIDSCENE_MODEL_NAME || 'qwen-vl-max-latest';
        const baseUrl = process.env.OPENAI_BASE_URL || 'https://dashscope.aliyuncs.com/compatible-mode/v1';
        
        // 使用一个简单的测试图片进行AI识别测试
        const { agent, page } = await initBrowser(true); // 使用无头模式
        
        try {
            // 导航到一个简单的测试页面
            await page.goto('data:text/html,<html><body><h1>AI Test</h1><button>Test Button</button></body></html>');
            
            // 测试AI识别响应时间
            const startTime = Date.now();
            
            // 使用aiLocate进行简单的元素定位测试
            const result = await agent.aiLocate('Test Button');
            
            const responseTime = Date.now() - startTime;
            
            console.log(`✅ AI模型响应时间: ${responseTime}ms`);
            
            res.json({
                success: true,
                model: modelName,
                baseUrl: baseUrl,
                responseTime: responseTime,
                timestamp: new Date().toISOString()
            });
            
        } finally {
            // 清理资源
            if (page) await page.close();
        }
        
    } catch (error) {
        console.error('❌ AI模型测试失败:', error);
        res.status(500).json({
            success: false,
            error: error.message,
            model: process.env.MIDSCENE_MODEL_NAME || 'qwen-vl-max-latest',
            timestamp: new Date().toISOString()
        });
    }
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

function findLatestExecutionReport(outputRoot, executionId) {
    const reportDir = resolveArtifactPath(outputRoot, executionId, 'report');
    if (!fs.existsSync(reportDir)) return null;
    const candidates = fs.readdirSync(reportDir, { withFileTypes: true })
        .filter(entry => entry.isFile() && /^playwright-.*\.html$/.test(entry.name) && !entry.name.endsWith('_simplified.html'))
        .map(entry => {
            const reportPath = resolveArtifactPath(outputRoot, executionId, `report/${entry.name}`);
            return { path: reportPath, mtimeMs: fs.statSync(reportPath).mtimeMs };
        })
        .sort((left, right) => right.mtimeMs - left.mtimeMs);
    return candidates[0]?.path || null;
}

async function checkAndNotifyMidsceneReport(executionId, testcase, executionState, outputRoot = OUTPUT_ROOT) {
    const reportPath = findLatestExecutionReport(outputRoot, executionId);
    if (!reportPath) {
        logMessage(executionId, 'warning', 'MidScene execution report is unavailable');
        return null;
    }
    const simplifiedReportPath = await generateSimplifiedReport(
        reportPath,
        testcase,
        executionState,
        outputRoot,
        executionId
    );
    logMessage(executionId, 'success', `Execution report generated: ${path.basename(simplifiedReportPath)}`);
    return simplifiedReportPath;
}

async function generateSimplifiedReport(
    originalReportPath,
    testcase,
    executionState,
    outputRoot = OUTPUT_ROOT,
    executionId
) {
    const reportDir = resolveArtifactPath(outputRoot, executionId, 'report');
    const resolvedOriginal = path.resolve(originalReportPath);
    if (!resolvedOriginal.startsWith(`${reportDir}${path.sep}`)) {
        throw new Error('artifact path is outside the execution report root');
    }
    const originalContent = fs.readFileSync(resolvedOriginal, 'utf8');
    const originalName = path.basename(resolvedOriginal, '.html');
    const simplifiedName = `${originalName}_simplified.html`;
    const simplifiedPath = resolveArtifactPath(
        outputRoot,
        executionId,
        `report/${simplifiedName}`
    );
    if (fs.existsSync(simplifiedPath) && fs.lstatSync(simplifiedPath).isSymbolicLink()) {
        throw new Error('artifact path cannot be a symbolic link');
    }
    const simplifiedContent = createSimplifiedReportContent(originalContent, testcase, executionState);
    fs.writeFileSync(simplifiedPath, simplifiedContent, 'utf8');
    return simplifiedPath;
}

function escapeReportText(value) {
    return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
}

// 创建一个纯文本安全报告。原始 MidScene HTML 只作为转义文本展示，
// 不继承其中的脚本、事件属性、javascript: URL 或未知第三方 markup。
function createSimplifiedReportContent(originalContent, testcase, executionState) {
    const steps = executionState.steps || [];
    const duration = executionState.duration || 0;

    return `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'">
  <title>测试执行报告</title>
</head>
<body>
  <h1>测试执行报告</h1>
  <dl>
    <dt>测试用例</dt><dd>${escapeReportText(testcase.name)}</dd>
    <dt>状态</dt><dd>${escapeReportText(executionState.status || 'completed')}</dd>
    <dt>耗时</dt><dd>${Math.round(duration / 1000)}秒</dd>
    <dt>步骤数</dt><dd>${steps.length}</dd>
  </dl>
  <h2>原始报告（安全文本视图）</h2>
  <pre>${escapeReportText(originalContent)}</pre>
</body>
</html>`;
}

function startServer(listenPort = process.env.PORT || port) {
    runtimeConfig = loadRuntimeConfig(process.env);
    validateEnvironmentVariables();
    if (server.listening) {
        return Promise.resolve(server);
    }

    return new Promise((resolve, reject) => {
        const handleError = error => {
            server.off('listening', handleListening);
            reject(error);
        };
        const handleListening = () => {
            server.off('error', handleError);
            console.log(`\n🚀 MidSceneJS本地代理服务器启动成功`);
            console.log(`HTTP服务器已绑定 ${runtimeConfig.bindHost}:${listenPort}`);
            console.log(`AI模型: ${process.env.MIDSCENE_MODEL_NAME || 'qwen-vl-max-latest'}`);
            console.log(`API地址: ${process.env.OPENAI_BASE_URL || 'https://dashscope.aliyuncs.com/compatible-mode/v1'}`);
            console.log('服务器就绪，等待测试执行请求...');
            resolve(server);
        };
        server.once('error', handleError);
        server.once('listening', handleListening);
        server.listen(listenPort, runtimeConfig.bindHost);
    });
}

async function resetState() {
    if (resetPromise) {
        return resetPromise;
    }

    runtimeResetting = true;
    const ownerExecutionId = activeExecutionId;
    const ownerPromise = activeExecutionPromise;

    resetPromise = (async () => {
        const control = ownerExecutionId
            ? executionControls.get(ownerExecutionId)
            : null;
        if (control) {
            control.shouldStop = true;
        }

        // Closing the currently owned resources helps cooperative cancellation,
        // but reset still waits for the exact owner promise to unwind.
        await cleanupOwnedResources(ownerExecutionId);
        if (ownerPromise) {
            try {
                await ownerPromise;
            } catch (error) {
                console.error('活动执行在重置期间失败:', error.message);
            }
        }

        if (activeExecutionPromise === ownerPromise) {
            activeExecutionPromise = null;
            activeExecutionId = null;
        }
        executionStates.clear();
        executionControls.clear();
        variableContexts.clear();
    })();

    try {
        await resetPromise;
    } finally {
        resetPromise = null;
        runtimeResetting = false;
    }
}

function closeServer() {
    return new Promise((resolve, reject) => {
        if (!server.listening) {
            resolve();
            return;
        }
        server.close(error => {
            if (error) {
                reject(error);
                return;
            }
            resolve();
        });
    });
}

function setLifecycleHttpClient(httpClient) {
    if (!httpClient || typeof httpClient.post !== 'function') {
        throw new TypeError('Lifecycle HTTP client must provide post(url, data, config)');
    }
    lifecycleHttpClient = httpClient;
}

async function gracefulShutdown(signal) {
    console.log(`收到${signal}信号，正在优雅关闭...`);
    await resetState();
    await closeServer();
}

module.exports = {
    app,
    server,
    io,
    startServer,
    closeServer,
    resetState,
    setLifecycleHttpClient,
    loadRuntimeConfig,
    setRuntimeConfigForTest,
    resolveArtifactPath,
    findLatestExecutionReport,
    generateSimplifiedReport,
    safeExecutionSnapshot,
    emitExecutionEvent,
    executionStates,
    executionControls
};

if (require.main === module) {
    const shutdown = signal => {
        gracefulShutdown(signal)
            .then(() => process.exit(0))
            .catch(error => {
                console.error('优雅关闭失败:', error);
                process.exit(1);
            });
    };
    process.once('SIGTERM', () => shutdown('SIGTERM'));
    process.once('SIGINT', () => shutdown('SIGINT'));
    startServer().catch(error => {
        console.error('MidSceneJS服务器启动失败:', error.message);
        process.exit(1);
    });
}
