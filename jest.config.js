/**
 * Jest测试配置 - 专用于本地代理服务器测试
 */

module.exports = {
  // 测试环境
  testEnvironment: 'node',

  // 测试文件匹配模式
  testMatch: [
    '**/tools/intent-tester/tests/proxy/**/*.test.js',
    '**/tools/intent-tester/tests/proxy/**/*.spec.js'
  ],

  // 忽略的文件和目录
  testPathIgnorePatterns: [
    '/node_modules/',
    '/dist/',
    '/build/'
  ],

  // 覆盖率配置
  collectCoverage: false, // 默认关闭，通过命令行参数控制
  collectCoverageFrom: [
    'tools/intent-tester/browser-automation/midscene_server.js',
    '!**/node_modules/**',
    '!**/dist/**',
    '!**/build/**',
    '!**/tests/**'
  ],

  // 覆盖率报告格式
  coverageReporters: [
    'text',
    'text-summary',
    'html',
    'lcov',
    'json'
  ],

  // 覆盖率输出目录
  coverageDirectory: '<rootDir>/coverage/proxy',

  // 覆盖率阈值 - 暂时禁用直到测试稳定运行
  // coverageThreshold: {
  //   global: {
  //     branches: 50,
  //     functions: 50,
  //     lines: 50,
  //     statements: 50
  //   }
  // },

  setupFilesAfterEnv: [
    '<rootDir>/tools/intent-tester/tests/proxy/setup.js'
  ],

  // 测试超时时间 (30秒)
  testTimeout: 30000,

  // 详细输出
  verbose: true,

  // 清理mock
  clearMocks: true,
  restoreMocks: true,

  // 报告器配置
  reporters: [
    'default',
    ['jest-junit', {
      outputDirectory: './test-results/proxy',
      outputName: 'junit.xml',
      classNameTemplate: '{classname}',
      titleTemplate: '{title}',
      ancestorSeparator: ' › ',
      usePathForSuiteName: true
    }]
  ],

  // 全局变量
  globals: {
    NODE_ENV: 'test'
  },

  // 检测已打开的句柄
  detectOpenHandles: true,

  // 强制退出
  forceExit: true,

  // 最大并发测试数量
  maxConcurrency: 1 // 代理服务器测试需要串行执行避免端口冲突
};