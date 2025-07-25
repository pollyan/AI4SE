/**
 * MidScene代理服务器WebSocket通信测试
 */

const { TestDataFactory, WebSocketTestHelper, ServerTestHelper, AssertHelper } = require('./mocks/test-helpers');
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

describe('MidScene代理服务器 - WebSocket通信测试', () => {
  let server;
  let serverInstance;
  let clients = [];
  
  beforeAll(async () => {
    // 设置测试环境变量
    process.env.PORT = global.testPort.toString();
    process.env.NODE_ENV = 'test';
    process.env.OPENAI_API_KEY = 'test-api-key';
    process.env.OPENAI_BASE_URL = 'https://test-api.com/v1';
    process.env.MIDSCENE_MODEL_NAME = 'test-model';
    
    // 启动测试服务器
    const http = require('http');
    const express = require('express');
    const { Server } = require('socket.io');
    
    const app = express();
    app.use(express.json());
    
    server = http.createServer(app);
    const io = new Server(server, {
      cors: {
        origin: "*",
        methods: ["GET", "POST"]
      }
    });
    
    // 模拟服务器WebSocket逻辑
    io.on('connection', (socket) => {
      // 发送服务器状态
      socket.emit('server-status', {
        status: 'ready',
        timestamp: new Date().toISOString()
      });
      
      socket.on('disconnect', () => {
        // 断开连接处理
      });
    });
    
    // 添加测试端点以触发WebSocket事件
    app.post('/test/trigger-websocket-event', (req, res) => {
      const { eventType, data } = req.body;
      io.emit(eventType, data);
      res.json({ success: true });
    });
    
    // 启动服务器
    await new Promise((resolve) => {
      server.listen(global.testPort, resolve);
    });
    
    serverInstance = { server, io };
  });
  
  afterAll(async () => {
    // 断开所有客户端连接
    WebSocketTestHelper.disconnectAll(clients);
    
    // 关闭服务器
    if (server) {
      await new Promise((resolve) => {
        server.close(resolve);
      });
    }
  });
  
  afterEach(() => {
    // 每个测试后断开客户端连接
    WebSocketTestHelper.disconnectAll(clients);
    clients = [];
  });
  
  describe('WebSocket连接管理', () => {
    test('应该成功建立WebSocket连接', async () => {
      const client = WebSocketTestHelper.createClient();
      clients.push(client);
      
      await new Promise((resolve) => {
        client.on('connect', () => {
          expect(client.connected).toBe(true);
          resolve();
        });
      });
    });
    
    test('连接后应该收到服务器状态消息', async () => {
      const client = WebSocketTestHelper.createClient();
      clients.push(client);
      
      const statusData = await WebSocketTestHelper.waitForEvent(client, 'server-status', 5000);
      
      expect(statusData).toBeDefined();
      expect(statusData.status).toBe('ready');
      expect(statusData.timestamp).toBeDefined();
    });
    
    test('应该正确处理连接断开', async () => {
      const client = WebSocketTestHelper.createClient();
      clients.push(client);
      
      // 等待连接建立
      await WebSocketTestHelper.waitForEvent(client, 'connect');
      
      // 断开连接
      client.disconnect();
      
      // 验证连接状态
      await new Promise(resolve => setTimeout(resolve, 100));
      expect(client.connected).toBe(false);
    });
    
    test('应该支持多个客户端连接', async () => {
      const client1 = WebSocketTestHelper.createClient();
      const client2 = WebSocketTestHelper.createClient();
      const client3 = WebSocketTestHelper.createClient();
      
      clients.push(client1, client2, client3);
      
      // 等待所有客户端连接
      await Promise.all([
        WebSocketTestHelper.waitForEvent(client1, 'connect'),
        WebSocketTestHelper.waitForEvent(client2, 'connect'),
        WebSocketTestHelper.waitForEvent(client3, 'connect')
      ]);
      
      expect(client1.connected).toBe(true);
      expect(client2.connected).toBe(true);
      expect(client3.connected).toBe(true);
    });
  });
  
  describe('实时消息推送', () => {
    let client;
    
    beforeEach(async () => {
      client = WebSocketTestHelper.createClient();
      clients.push(client);
      await WebSocketTestHelper.waitForEvent(client, 'connect');
    });
    
    test('应该接收执行开始消息', async () => {
      const executionData = {
        executionId: 'test_exec_123',
        testcase: '测试用例',
        mode: 'headless',
        totalSteps: 4,
        timestamp: new Date().toISOString()
      };
      
      // 触发执行开始事件
      const axios = require('axios');
      await axios.post(`${global.testBaseUrl}/test/trigger-websocket-event`, {
        eventType: 'execution-start',
        data: executionData
      });
      
      // 等待并验证消息
      const receivedData = await WebSocketTestHelper.waitForEvent(client, 'execution-start');
      
      expect(receivedData).toMatchObject(executionData);
      AssertHelper.assertWebSocketMessage(receivedData, 'execution-start');
    });
    
    test('应该接收步骤开始消息', async () => {
      const stepData = {
        executionId: 'test_exec_123',
        stepIndex: 0,
        action: 'navigate',
        description: '导航到测试页面',
        totalSteps: 4
      };
      
      // 触发步骤开始事件
      const axios = require('axios');
      await axios.post(`${global.testBaseUrl}/test/trigger-websocket-event`, {
        eventType: 'step-start',
        data: stepData
      });
      
      // 等待并验证消息
      const receivedData = await WebSocketTestHelper.waitForEvent(client, 'step-start');
      
      expect(receivedData).toMatchObject(stepData);
      expect(receivedData.stepIndex).toBe(0);
      expect(receivedData.action).toBe('navigate');
    });
    
    test('应该接收步骤完成消息', async () => {
      const stepCompletedData = {
        executionId: 'test_exec_123',
        stepIndex: 0,
        totalSteps: 4,
        success: true,
        result: {
          status: 'success',
          duration: 1500
        }
      };
      
      // 触发步骤完成事件
      const axios = require('axios');
      await axios.post(`${global.testBaseUrl}/test/trigger-websocket-event`, {
        eventType: 'step-completed',
        data: stepCompletedData
      });
      
      // 等待并验证消息
      const receivedData = await WebSocketTestHelper.waitForEvent(client, 'step-completed');
      
      expect(receivedData).toMatchObject(stepCompletedData);
      expect(receivedData.success).toBe(true);
      expect(receivedData.result).toBeDefined();
    });
    
    test('应该接收步骤失败消息', async () => {
      const stepFailedData = {
        executionId: 'test_exec_123',
        stepIndex: 1,
        totalSteps: 4,
        success: false,
        error: 'AI模型连接失败'
      };
      
      // 触发步骤失败事件
      const axios = require('axios');
      await axios.post(`${global.testBaseUrl}/test/trigger-websocket-event`, {
        eventType: 'step-completed',
        data: stepFailedData
      });
      
      // 等待并验证消息
      const receivedData = await WebSocketTestHelper.waitForEvent(client, 'step-completed');
      
      expect(receivedData).toMatchObject(stepFailedData);
      expect(receivedData.success).toBe(false);
      expect(receivedData.error).toBeDefined();
    });
    
    test('应该接收步骤跳过消息', async () => {
      const stepSkippedData = {
        executionId: 'test_exec_123',
        stepIndex: 1,
        totalSteps: 4,
        description: '输入测试文本',
        message: '此步骤已被标记为跳过'
      };
      
      // 触发步骤跳过事件
      const axios = require('axios');
      await axios.post(`${global.testBaseUrl}/test/trigger-websocket-event`, {
        eventType: 'step-skipped',
        data: stepSkippedData
      });
      
      // 等待并验证消息
      const receivedData = await WebSocketTestHelper.waitForEvent(client, 'step-skipped');
      
      expect(receivedData).toMatchObject(stepSkippedData);
      expect(receivedData.message).toContain('跳过');
    });
    
    test('应该接收步骤进度消息', async () => {
      const progressData = {
        executionId: 'test_exec_123',
        stepIndex: 2,
        totalSteps: 4,
        step: '点击提交按钮',
        progress: 75
      };
      
      // 触发步骤进度事件
      const axios = require('axios');
      await axios.post(`${global.testBaseUrl}/test/trigger-websocket-event`, {
        eventType: 'step-progress',
        data: progressData
      });
      
      // 等待并验证消息
      const receivedData = await WebSocketTestHelper.waitForEvent(client, 'step-progress');
      
      expect(receivedData).toMatchObject(progressData);
      expect(receivedData.progress).toBe(75);
    });
    
    test('应该接收执行完成消息', async () => {
      const executionCompletedData = {
        executionId: 'test_exec_123',
        status: 'success',
        message: '测试执行完成！所有 4 个步骤全部成功',
        duration: 15000,
        totalSteps: 4,
        successSteps: 4,
        failedSteps: 0,
        skippedSteps: 0,
        executedSteps: 4,
        timestamp: new Date().toISOString()
      };
      
      // 触发执行完成事件
      const axios = require('axios');
      await axios.post(`${global.testBaseUrl}/test/trigger-websocket-event`, {
        eventType: 'execution-completed',
        data: executionCompletedData
      });
      
      // 等待并验证消息
      const receivedData = await WebSocketTestHelper.waitForEvent(client, 'execution-completed');
      
      expect(receivedData).toMatchObject(executionCompletedData);
      AssertHelper.assertExecutionStatus(receivedData.status);
      expect(receivedData.totalSteps).toBe(4);
      expect(receivedData.successSteps).toBe(4);
    });
    
    test('应该接收执行停止消息', async () => {
      const executionStoppedData = {
        executionId: 'test_exec_123',
        timestamp: new Date().toISOString()
      };
      
      // 触发执行停止事件
      const axios = require('axios');
      await axios.post(`${global.testBaseUrl}/test/trigger-websocket-event`, {
        eventType: 'execution-stopped',
        data: executionStoppedData
      });
      
      // 等待并验证消息
      const receivedData = await WebSocketTestHelper.waitForEvent(client, 'execution-stopped');
      
      expect(receivedData).toMatchObject(executionStoppedData);
      expect(receivedData.timestamp).toBeDefined();
    });
    
    test('应该接收日志消息', async () => {
      const logData = {
        executionId: 'test_exec_123',
        level: 'info',
        message: '导航到: https://example.com',
        timestamp: new Date().toISOString()
      };
      
      // 触发日志消息事件
      const axios = require('axios');
      await axios.post(`${global.testBaseUrl}/test/trigger-websocket-event`, {
        eventType: 'log-message',
        data: logData
      });
      
      // 等待并验证消息
      const receivedData = await WebSocketTestHelper.waitForEvent(client, 'log-message');
      
      expect(receivedData).toMatchObject(logData);
      expect(receivedData.level).toBe('info');
      expect(receivedData.message).toContain('导航到');
    });
    
    test('应该接收截图数据', async () => {
      const screenshotData = {
        executionId: 'test_exec_123',
        stepIndex: 1,
        screenshot: 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==', // 1x1 PNG
        timestamp: new Date().toISOString()
      };
      
      // 触发截图事件
      const axios = require('axios');
      await axios.post(`${global.testBaseUrl}/test/trigger-websocket-event`, {
        eventType: 'screenshot-taken',
        data: screenshotData
      });
      
      // 等待并验证消息
      const receivedData = await WebSocketTestHelper.waitForEvent(client, 'screenshot-taken');
      
      expect(receivedData).toMatchObject(screenshotData);
      expect(receivedData.screenshot).toBeDefined();
      expect(typeof receivedData.screenshot).toBe('string');
    });
  });
  
  describe('广播消息', () => {
    test('应该向所有连接的客户端广播消息', async () => {
      // 创建多个客户端
      const client1 = WebSocketTestHelper.createClient();
      const client2 = WebSocketTestHelper.createClient();
      const client3 = WebSocketTestHelper.createClient();
      
      clients.push(client1, client2, client3);
      
      // 等待所有客户端连接
      await Promise.all([
        WebSocketTestHelper.waitForEvent(client1, 'connect'),
        WebSocketTestHelper.waitForEvent(client2, 'connect'),
        WebSocketTestHelper.waitForEvent(client3, 'connect')
      ]);
      
      const broadcastData = {
        executionId: 'test_exec_broadcast',
        message: 'This is a broadcast message',
        timestamp: new Date().toISOString()
      };
      
      // 触发广播事件
      const axios = require('axios');
      await axios.post(`${global.testBaseUrl}/test/trigger-websocket-event`, {
        eventType: 'execution-start',
        data: broadcastData
      });
      
      // 所有客户端都应该收到消息
      const [data1, data2, data3] = await Promise.all([
        WebSocketTestHelper.waitForEvent(client1, 'execution-start'),
        WebSocketTestHelper.waitForEvent(client2, 'execution-start'),
        WebSocketTestHelper.waitForEvent(client3, 'execution-start')
      ]);
      
      expect(data1).toMatchObject(broadcastData);
      expect(data2).toMatchObject(broadcastData);
      expect(data3).toMatchObject(broadcastData);
    });
  });
  
  describe('错误处理', () => {
    test('应该处理连接超时', async () => {
      // 创建一个短超时的客户端
      const client = WebSocketTestHelper.createClient();
      client.timeout = 100; // 100ms超时
      clients.push(client);
      
      await expect(
        WebSocketTestHelper.waitForEvent(client, 'non-existent-event', 200)
      ).rejects.toThrow('等待事件 "non-existent-event" 超时');
    });
    
    test('应该处理无效的WebSocket消息', async () => {
      const client = WebSocketTestHelper.createClient();
      clients.push(client);
      
      await WebSocketTestHelper.waitForEvent(client, 'connect');
      
      // 发送无效消息不应导致连接断开
      client.emit('invalid-event', { invalid: 'data' });
      
      // 等待一段时间确保连接仍然正常
      await new Promise(resolve => setTimeout(resolve, 500));
      expect(client.connected).toBe(true);
    });
    
    test('应该处理网络连接中断', async () => {
      const client = WebSocketTestHelper.createClient();
      clients.push(client);
      
      await WebSocketTestHelper.waitForEvent(client, 'connect');
      
      // 模拟网络中断
      client.disconnect();
      
      await new Promise(resolve => setTimeout(resolve, 100));
      expect(client.connected).toBe(false);
    });
  });
  
  describe('性能测试', () => {
    test('应该能处理大量WebSocket消息', async () => {
      const client = WebSocketTestHelper.createClient();
      clients.push(client);
      
      await WebSocketTestHelper.waitForEvent(client, 'connect');
      
      const messageCount = 100;
      let receivedCount = 0;
      
      // 监听消息
      client.on('log-message', () => {
        receivedCount++;
      });
      
      // 发送大量消息
      const axios = require('axios');
      const promises = [];
      
      for (let i = 0; i < messageCount; i++) {
        promises.push(
          axios.post(`${global.testBaseUrl}/test/trigger-websocket-event`, {
            eventType: 'log-message',
            data: {
              executionId: 'test_exec_performance',
              level: 'info',
              message: `Message ${i}`,
              timestamp: new Date().toISOString()
            }
          })
        );
      }
      
      await Promise.all(promises);
      
      // 等待消息处理完成
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      expect(receivedCount).toBe(messageCount);
    });
    
    test('WebSocket连接响应时间应该合理', async () => {
      const startTime = Date.now();
      
      const client = WebSocketTestHelper.createClient();
      clients.push(client);
      
      await WebSocketTestHelper.waitForEvent(client, 'connect');
      
      const connectionTime = Date.now() - startTime;
      
      // 连接时间应该小于1秒
      expect(connectionTime).toBeLessThan(1000);
    });
  });
});