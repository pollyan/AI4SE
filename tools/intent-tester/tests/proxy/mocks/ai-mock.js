/**
 * AI服务Mock - 模拟MidSceneJS AI功能
 */

const aiMock = {
  // 模拟AI响应延迟
  responseDelay: 100,
  
  // 模拟成功响应
  mockSuccessResponse: (operation, params = {}) => {
    return new Promise((resolve) => {
      setTimeout(() => {
        const responses = {
          aiTap: { success: true, element: 'mocked-element', action: 'clicked' },
          aiInput: { success: true, element: 'mocked-input', text: params.text },
          aiAssert: { success: true, condition: params.condition, result: true },
          aiWaitFor: { success: true, element: 'mocked-element', found: true },
          aiQuery: { 
            success: true, 
            result: { 
              text: 'mocked query result',
              elements: ['element1', 'element2']
            }
          },
          aiAction: { success: true, actions: ['action1', 'action2'] },
          aiScroll: { success: true, scrolled: true },
          aiHover: { success: true, element: 'mocked-element', hovered: true }
        };
        
        resolve(responses[operation] || { success: true });
      }, aiMock.responseDelay);
    });
  },
  
  // 模拟失败响应
  mockErrorResponse: (operation, errorMessage = 'AI operation failed') => {
    return new Promise((resolve, reject) => {
      setTimeout(() => {
        reject(new Error(errorMessage));
      }, aiMock.responseDelay);
    });
  },
  
  // 模拟超时响应
  mockTimeoutResponse: (operation, timeout = 5000) => {
    return new Promise((resolve, reject) => {
      setTimeout(() => {
        reject(new Error(`${operation} timeout after ${timeout}ms`));
      }, timeout);
    });
  },
  
  // 模拟连接错误
  mockConnectionError: (operation) => {
    return Promise.reject(new Error('Connection error: AI model service unavailable'));
  },
  
  // 模拟空内容响应
  mockEmptyContentError: (operation) => {
    return Promise.reject(new Error('AI returned empty content'));
  },
  
  // 重置Mock状态
  reset: () => {
    aiMock.responseDelay = 100;
  },
  
  // 设置响应延迟
  setResponseDelay: (delay) => {
    aiMock.responseDelay = delay;
  }
};

// 创建MidSceneJS Agent Mock
const createMockAgent = (mockBehavior = 'success') => {
  const agent = {};
  
  const operations = [
    'aiTap', 'aiInput', 'aiAssert', 'aiWaitFor', 
    'aiQuery', 'aiAction', 'aiScroll', 'aiHover', 'ai'
  ];
  
  operations.forEach(operation => {
    agent[operation] = jest.fn().mockImplementation((...args) => {
      switch (mockBehavior) {
        case 'success':
          return aiMock.mockSuccessResponse(operation, args[0]);
        case 'error':
          return aiMock.mockErrorResponse(operation);
        case 'timeout':
          return aiMock.mockTimeoutResponse(operation);
        case 'connection_error':
          return aiMock.mockConnectionError(operation);
        case 'empty_content':
          return aiMock.mockEmptyContentError(operation);
        default:
          return aiMock.mockSuccessResponse(operation, args[0]);
      }
    });
  });
  
  return agent;
};

// 创建浏览器Page Mock
const createMockPage = (mockBehavior = 'success') => {
  const page = {
    goto: jest.fn(),
    screenshot: jest.fn(),
    waitForTimeout: jest.fn(),
    title: jest.fn(),
    url: jest.fn(),
    reload: jest.fn(),
    goBack: jest.fn(),
    evaluate: jest.fn(),
    setDefaultTimeout: jest.fn(),
    setDefaultNavigationTimeout: jest.fn(),
    close: jest.fn(),
    viewportSize: jest.fn()
  };
  
  // 配置默认行为
  switch (mockBehavior) {
    case 'success':
      page.goto.mockResolvedValue(undefined);
      page.screenshot.mockResolvedValue(Buffer.from('fake-screenshot'));
      page.waitForTimeout.mockResolvedValue(undefined);
      page.title.mockResolvedValue('Test Page Title');
      page.url.mockReturnValue('https://example.com');
      page.reload.mockResolvedValue(undefined);
      page.goBack.mockResolvedValue(undefined);
      page.evaluate.mockResolvedValue('evaluation result');
      page.viewportSize.mockReturnValue({ width: 1280, height: 720 });
      page.close.mockResolvedValue(undefined);
      break;
    case 'error':
      page.goto.mockRejectedValue(new Error('Navigation failed'));
      page.screenshot.mockRejectedValue(new Error('Screenshot failed'));
      break;
    case 'timeout':
      page.goto.mockRejectedValue(new Error('Navigation timeout'));
      break;
  }
  
  return page;
};

// 创建浏览器Browser Mock
const createMockBrowser = (mockBehavior = 'success') => {
  const browser = {
    close: jest.fn(),
    newContext: jest.fn(),
    isConnected: jest.fn()
  };
  
  // 配置默认行为
  switch (mockBehavior) {
    case 'success':
      browser.close.mockResolvedValue(undefined);
      browser.newContext.mockResolvedValue({
        newPage: jest.fn().mockResolvedValue(createMockPage(mockBehavior))
      });
      browser.isConnected.mockReturnValue(true);
      break;
    case 'error':
      browser.close.mockRejectedValue(new Error('Browser close failed'));
      browser.newContext.mockRejectedValue(new Error('Context creation failed'));
      break;
  }
  
  return browser;
};

module.exports = {
  aiMock,
  createMockAgent,
  createMockPage,
  createMockBrowser
};