/**
 * Jest测试配置 - 专用于本地代理服务器测试
 */

module.exports = {
  // 测试环境
  testEnvironment: 'node',
  
  // 测试文件匹配模式
  testMatch: [
    '**/tests/proxy/**/*.test.js',
    '**/tests/proxy/**/*.spec.js'
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
    'midscene_server.js',
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
  
  // 覆盖率阈值
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80
    }
  },
  
  // 测试设置文件
  setupFilesAfterEnv: [
    '<rootDir>/tests/proxy/setup.js'
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
  
  // 模块路径映射
  moduleNameMapping: {
    '^@/(.*)$': '<rootDir>/$1',
    '^@tests/(.*)$': '<rootDir>/tests/$1'
  },
  
  // 检测已打开的句柄
  detectOpenHandles: true,
  
  // 强制退出
  forceExit: true,
  
  // 最大并发测试数量
  maxConcurrency: 1, // 代理服务器测试需要串行执行避免端口冲突
  
  // 测试运行模式
  runInBand: true // 串行运行所有测试
};