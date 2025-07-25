/**
 * Jest测试环境设置文件
 * 为代理服务器测试配置全局设置和清理逻辑
 */

// 设置测试环境变量
process.env.NODE_ENV = 'test';
process.env.PORT = '3002'; // 使用不同的端口避免与开发服务器冲突
process.env.TESTING = 'true';

// 设置测试超时
jest.setTimeout(30000);

// 全局变量
global.testPort = 3002;
global.testBaseUrl = `http://localhost:${global.testPort}`;

// 测试前的全局设置
beforeAll(async () => {
  // 静默控制台输出以避免测试输出混乱
  const originalConsoleLog = console.log;
  const originalConsoleError = console.error;
  const originalConsoleWarn = console.warn;
  
  global.originalConsole = {
    log: originalConsoleLog,
    error: originalConsoleError,
    warn: originalConsoleWarn
  };
  
  // 在测试模式下减少日志输出
  console.log = jest.fn();
  console.warn = jest.fn();
  // 保留错误日志用于调试
  console.error = (...args) => {
    if (process.env.DEBUG_TESTS) {
      originalConsoleError(...args);
    }
  };
});

// 测试后的全局清理
afterAll(async () => {
  // 恢复控制台输出
  if (global.originalConsole) {
    console.log = global.originalConsole.log;
    console.error = global.originalConsole.error;
    console.warn = global.originalConsole.warn;
  }
});

// 每个测试后的清理
afterEach(async () => {
  // 清理所有mock
  jest.clearAllMocks();
  
  // 清理计时器
  jest.clearAllTimers();
  
  // 清理未处理的Promise
  await new Promise(resolve => setImmediate(resolve));
});

// 处理未捕获的Promise拒绝
process.on('unhandledRejection', (reason, promise) => {
  if (process.env.DEBUG_TESTS) {
    console.error('未处理的Promise拒绝:', reason);
  }
});

// 处理未捕获的异常
process.on('uncaughtException', (error) => {
  if (process.env.DEBUG_TESTS) {
    console.error('未捕获的异常:', error);
  }
});