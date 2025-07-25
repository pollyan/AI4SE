/**
 * MidScene代理服务器HTTP API端点测试
 */

const request = require('supertest');
const { TestDataFactory, ServerTestHelper, AssertHelper } = require('./mocks/test-helpers');
const { createMockAgent, createMockPage, createMockBrowser } = require('./mocks/ai-mock');

// Mock MidSceneJS和Playwright
jest.mock('@midscene/web', () => {
  return {
    PlaywrightAgent: jest.fn().mockImplementation(() => createMockAgent('success'))
  };
});

jest.mock('playwright', () => {
  return {
    chromium: {
      launch: jest.fn().mockResolvedValue(createMockBrowser('success'))
    }
  };
});

// Mock Socket.IO for server
jest.mock('socket.io', () => {
  return {
    Server: jest.fn().mockImplementation(() => ({
      emit: jest.fn(),
      on: jest.fn()
    }))
  };
});

// Mock HTTP server
jest.mock('http', () => {
  const originalHttp = jest.requireActual('http');
  return {
    ...originalHttp,
    createServer: jest.fn().mockImplementation((app) => {
      const server = originalHttp.createServer(app);
      // 使用测试端口
      const originalListen = server.listen;
      server.listen = jest.fn().mockImplementation((port, callback) => {
        return originalListen.call(server, global.testPort, callback);
      });
      return server;
    })
  };
});

describe('MidScene代理服务器 - HTTP API测试', () => {
  let app;
  let server;
  
  beforeAll(async () => {
    // 设置测试环境变量
    process.env.PORT = global.testPort.toString();
    process.env.NODE_ENV = 'test';
    process.env.OPENAI_API_KEY = 'test-api-key';
    process.env.OPENAI_BASE_URL = 'https://test-api.com/v1';
    process.env.MIDSCENE_MODEL_NAME = 'test-model';
    
    // 动态导入服务器模块以应用mock
    const serverModule = require('../../midscene_server');
    app = serverModule.app || serverModule;
  });
  
  afterAll(async () => {
    // 清理
    if (server) {
      server.close();
    }
    jest.clearAllMocks();
  });
  
  describe('健康检查端点', () => {
    test('GET /health - 应该返回服务器健康状态', async () => {
      const response = await request(app)
        .get('/health');
      
      AssertHelper.assertApiResponse(response, 200);
      expect(response.body.message).toBe('MidSceneJS服务器运行正常');
      expect(response.body.model).toBeDefined();
      expect(response.body.timestamp).toBeDefined();
    });
  });
  
  describe('服务器状态端点', () => {
    test('GET /api/status - 应该返回服务器状态信息', async () => {
      const response = await request(app)
        .get('/api/status');
      
      AssertHelper.assertApiResponse(response, 200);
      expect(response.body.status).toBe('ready');
      expect(response.body.browserInitialized).toBeDefined();
      expect(response.body.runningExecutions).toBeDefined();
      expect(response.body.totalExecutions).toBeDefined();
      expect(response.body.uptime).toBeDefined();
      expect(response.body.timestamp).toBeDefined();
    });
  });
  
  describe('测试用例执行端点', () => {
    test('POST /api/execute-testcase - 成功启动测试用例执行', async () => {
      const testcase = TestDataFactory.createTestCase();
      
      const response = await request(app)
        .post('/api/execute-testcase')
        .send({
          testcase,
          mode: 'headless',
          timeout_settings: {
            page_timeout: 30000,
            action_timeout: 30000,
            navigation_timeout: 30000
          }
        });
      
      AssertHelper.assertApiResponse(response, 200);
      expect(response.body.message).toBe('测试用例开始执行');
      AssertHelper.assertExecutionId(response.body.executionId);
      expect(response.body.timestamp).toBeDefined();
    });
    
    test('POST /api/execute-testcase - 缺少测试用例数据应该返回400', async () => {
      const response = await request(app)
        .post('/api/execute-testcase')
        .send({
          mode: 'headless'
        });
      
      expect(response.status).toBe(400);
      expect(response.body.success).toBe(false);
      expect(response.body.error).toBe('缺少测试用例数据');
    });
    
    test('POST /api/execute-testcase - 支持不同的执行模式', async () => {
      const testcase = TestDataFactory.createTestCase();
      
      // 测试无头模式
      const headlessResponse = await request(app)
        .post('/api/execute-testcase')
        .send({
          testcase,
          mode: 'headless'
        });
      
      AssertHelper.assertApiResponse(headlessResponse, 200);
      
      // 测试浏览器模式
      const browserResponse = await request(app)
        .post('/api/execute-testcase')
        .send({
          testcase,
          mode: 'browser'
        });
      
      AssertHelper.assertApiResponse(browserResponse, 200);
    });
    
    test('POST /api/execute-testcase - 支持自定义超时设置', async () => {
      const testcase = TestDataFactory.createTestCase();
      
      const response = await request(app)
        .post('/api/execute-testcase')
        .send({
          testcase,
          mode: 'headless',
          timeout_settings: {
            page_timeout: 60000,
            action_timeout: 45000,
            navigation_timeout: 50000
          }
        });
      
      AssertHelper.assertApiResponse(response, 200);
    });
  });
  
  describe('执行状态查询端点', () => {
    test('GET /api/execution-status/:executionId - 查询存在的执行状态', async () => {
      // 首先启动一个执行
      const testcase = TestDataFactory.createTestCase();
      const startResponse = await request(app)
        .post('/api/execute-testcase')
        .send({ testcase, mode: 'headless' });
      
      const executionId = startResponse.body.executionId;
      
      // 查询执行状态
      const statusResponse = await request(app)
        .get(`/api/execution-status/${executionId}`);
      
      AssertHelper.assertApiResponse(statusResponse, 200);
      expect(statusResponse.body.executionId).toBe(executionId);
      AssertHelper.assertExecutionStatus(statusResponse.body.status);
    });
    
    test('GET /api/execution-status/:executionId - 查询不存在的执行ID应该返回404', async () => {
      const nonExistentId = 'exec_999999999_nonexistent';
      
      const response = await request(app)
        .get(`/api/execution-status/${nonExistentId}`);
      
      expect(response.status).toBe(404);
      expect(response.body.success).toBe(false);
      expect(response.body.error).toBe('执行记录不存在');
    });
  });
  
  describe('执行报告端点', () => {
    test('GET /api/execution-report/:executionId - 获取执行报告', async () => {
      // 首先启动一个执行
      const testcase = TestDataFactory.createTestCase();
      const startResponse = await request(app)
        .post('/api/execute-testcase')
        .send({ testcase, mode: 'headless' });
      
      const executionId = startResponse.body.executionId;
      
      // 等待一段时间让执行有一些状态
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // 查询执行报告
      const reportResponse = await request(app)
        .get(`/api/execution-report/${executionId}`);
      
      AssertHelper.assertApiResponse(reportResponse, 200);
      expect(reportResponse.body.report).toBeDefined();
      expect(reportResponse.body.report.executionId).toBe(executionId);
      expect(reportResponse.body.report.testcase).toBeDefined();
      expect(reportResponse.body.report.summary).toBeDefined();
      expect(reportResponse.body.report.generatedAt).toBeDefined();
    });
    
    test('GET /api/execution-report/:executionId - 查询不存在的执行ID应该返回404', async () => {
      const nonExistentId = 'exec_999999999_nonexistent';
      
      const response = await request(app)
        .get(`/api/execution-report/${nonExistentId}`);
      
      expect(response.status).toBe(404);
      expect(response.body.success).toBe(false);
      expect(response.body.error).toBe('执行记录不存在');
    });
  });
  
  describe('执行列表端点', () => {
    test('GET /api/executions - 获取所有执行记录列表', async () => {
      const response = await request(app)
        .get('/api/executions');
      
      AssertHelper.assertApiResponse(response, 200);
      expect(response.body.executions).toBeDefined();
      expect(Array.isArray(response.body.executions)).toBe(true);
      expect(response.body.total).toBeDefined();
      expect(typeof response.body.total).toBe('number');
    });
    
    test('GET /api/executions - 执行列表应该按时间倒序排列', async () => {
      // 启动几个执行
      const testcase1 = TestDataFactory.createTestCase({ name: '测试用例1' });
      const testcase2 = TestDataFactory.createTestCase({ name: '测试用例2' });
      
      await request(app)
        .post('/api/execute-testcase')
        .send({ testcase: testcase1, mode: 'headless' });
      
      await new Promise(resolve => setTimeout(resolve, 100));
      
      await request(app)
        .post('/api/execute-testcase')
        .send({ testcase: testcase2, mode: 'headless' });
      
      // 获取执行列表
      const response = await request(app)
        .get('/api/executions');
      
      AssertHelper.assertApiResponse(response, 200);
      const executions = response.body.executions;
      
      if (executions.length >= 2) {
        const firstExecution = new Date(executions[0].startTime).getTime();
        const secondExecution = new Date(executions[1].startTime).getTime();
        expect(firstExecution).toBeGreaterThanOrEqual(secondExecution);
      }
    });
  });
  
  describe('停止执行端点', () => {
    test('POST /api/stop-execution/:executionId - 停止正在运行的执行', async () => {
      // 启动一个长时间运行的执行
      const testcase = TestDataFactory.createComplexTestCase(20);
      const startResponse = await request(app)
        .post('/api/execute-testcase')
        .send({ testcase, mode: 'headless' });
      
      const executionId = startResponse.body.executionId;
      
      // 立即停止执行
      const stopResponse = await request(app)
        .post(`/api/stop-execution/${executionId}`);
      
      AssertHelper.assertApiResponse(stopResponse, 200);
      expect(stopResponse.body.message).toBe('执行已停止');
    });
    
    test('POST /api/stop-execution/:executionId - 停止不存在的执行应该返回404', async () => {
      const nonExistentId = 'exec_999999999_nonexistent';
      
      const response = await request(app)
        .post(`/api/stop-execution/${nonExistentId}`);
      
      expect(response.status).toBe(404);
      expect(response.body.success).toBe(false);
      expect(response.body.error).toBe('执行记录不存在');
    });
  });
  
  describe('AI功能端点', () => {
    test('GET /ai-test - 测试AI模型响应时间', async () => {
      const response = await request(app)
        .get('/ai-test');
      
      AssertHelper.assertApiResponse(response, 200);
      expect(response.body.model).toBeDefined();
      expect(response.body.baseUrl).toBeDefined();
      expect(response.body.responseTime).toBeDefined();
      expect(typeof response.body.responseTime).toBe('number');
      expect(response.body.timestamp).toBeDefined();
    });
    
    test('POST /ai-input - AI输入功能', async () => {
      const response = await request(app)
        .post('/ai-input')
        .send({
          text: 'test input',
          locate: 'input field'
        });
      
      AssertHelper.assertApiResponse(response, 200);
      expect(response.body.result).toBeDefined();
    });
    
    test('POST /ai-tap - AI点击功能', async () => {
      const response = await request(app)
        .post('/ai-tap')
        .send({
          prompt: 'submit button'
        });
      
      AssertHelper.assertApiResponse(response, 200);
      expect(response.body.result).toBeDefined();
    });
    
    test('POST /ai-assert - AI断言功能', async () => {
      const response = await request(app)
        .post('/ai-assert')
        .send({
          prompt: 'success message is displayed'
        });
      
      AssertHelper.assertApiResponse(response, 200);
      expect(response.body.result).toBe(true);
    });
    
    test('POST /ai-wait-for - AI等待功能', async () => {
      const response = await request(app)
        .post('/ai-wait-for')
        .send({
          prompt: 'loading spinner',
          timeout: 10000
        });
      
      AssertHelper.assertApiResponse(response, 200);
      expect(response.body.result).toBeDefined();
    });
    
    test('POST /ai-action - AI动作规划功能', async () => {
      const response = await request(app)
        .post('/ai-action')
        .send({
          prompt: 'fill out the registration form'
        });
      
      AssertHelper.assertApiResponse(response, 200);
      expect(response.body.result).toBeDefined();
    });
  });
  
  describe('页面操作端点', () => {
    test('POST /goto - 导航到指定URL', async () => {
      const response = await request(app)
        .post('/goto')
        .send({
          url: 'https://example.com',
          mode: 'headless'
        });
      
      AssertHelper.assertApiResponse(response, 200);
      expect(response.body.url).toBeDefined();
      expect(response.body.title).toBeDefined();
    });
    
    test('POST /screenshot - 截图功能', async () => {
      const response = await request(app)
        .post('/screenshot')
        .send({
          path: './test-screenshot.png'
        });
      
      AssertHelper.assertApiResponse(response, 200);
      expect(response.body.path).toBe('./test-screenshot.png');
    });
    
    test('GET /page-info - 获取页面信息', async () => {
      const response = await request(app)
        .get('/page-info');
      
      AssertHelper.assertApiResponse(response, 200);
      expect(response.body.info).toBeDefined();
      expect(response.body.info.url).toBeDefined();
      expect(response.body.info.title).toBeDefined();
      expect(response.body.info.viewport).toBeDefined();
    });
  });
  
  describe('资源管理端点', () => {
    test('POST /cleanup - 清理资源', async () => {
      const response = await request(app)
        .post('/cleanup');
      
      AssertHelper.assertApiResponse(response, 200);
      expect(response.body.message).toBe('资源已清理');
    });
  });
  
  describe('错误处理', () => {
    test('访问不存在的端点应该返回404', async () => {
      const response = await request(app)
        .get('/non-existent-endpoint');
      
      expect(response.status).toBe(404);
    });
    
    test('POST请求缺少必要参数时应该返回适当错误', async () => {
      const response = await request(app)
        .post('/ai-input')
        .send({
          // 缺少text和locate参数
        });
      
      expect(response.status).toBe(500);
      expect(response.body.success).toBe(false);
      expect(response.body.error).toBeDefined();
    });
  });
});