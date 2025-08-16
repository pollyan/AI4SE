# HTTP接口调用功能技术设计文档

## 文档信息
- **功能名称**: HTTP接口调用步骤
- **版本**: v1.0
- **创建日期**: 2025-08-16
- **文档类型**: 技术设计文档 (TDD)
- **状态**: 设计完成

## 📋 目录
1. [架构设计](#架构设计)
2. [技术选型](#技术选型)
3. [模块设计](#模块设计)
4. [数据结构](#数据结构)
5. [接口设计](#接口设计)
6. [实现细节](#实现细节)
7. [部署方案](#部署方案)

---

## 🏗️ 架构设计

### 整体架构图
```
┌─────────────────────────────────────────────────────────────────┐
│                    Web GUI Layer                               │
├─────────────────────────────────────────────────────────────────┤
│  Step Editor  │  HTTP Config  │  Variable Input  │  Debug View  │
└─────────────────┬───────────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────────┐
│                   API Layer                                    │
├─────────────────────────────────────────────────────────────────┤
│  Step CRUD    │  Execution    │  Variable Mgmt  │  Result API   │
└─────────────────┬───────────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────────┐
│                MidScene Server (Node.js)                      │
├─────────────────────────────────────────────────────────────────┤
│  Step Executor │ HTTP Handler │ Variable Resolver│  AI Engine   │
└─────────────────┬───────────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────────┐
│              Playwright Browser Context                       │
├─────────────────────────────────────────────────────────────────┤
│    AI Steps    │   HTTP Fetch   │   Cookie State   │   Session   │
└─────────────────┬───────────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────────┐
│                Python Backend                                 │
├─────────────────────────────────────────────────────────────────┤
│  Variable Extraction (jsonpath-ng)  │  Data Storage  │ Logging  │
└─────────────────────────────────────────────────────────────────┘
```

### 执行流程图
```
用户配置HTTP步骤
      │
      ▼
前端提交步骤配置
      │
      ▼
API保存步骤配置到数据库
      │
      ▼
用户触发测试执行
      │
      ▼
MidScene服务器接收执行请求
      │
      ▼
步骤执行器解析HTTP步骤
      │
      ▼
变量解析器处理URL/Header/Body中的变量
      │
      ▼
Playwright Browser Context执行fetch请求
      │
      ▼
接收HTTP响应并记录日志
      │
      ▼
Python后端使用jsonpath-ng提取变量
      │
      ▼
更新变量存储并继续后续步骤
```

---

## 🔧 技术选型

### 技术栈对比分析

#### HTTP客户端选择
**方案A: Playwright fetch API (推荐)**
```javascript
// 优势: 统一执行环境，共享浏览器状态
await page.evaluate(async (config) => {
  return await fetch(config.url, {
    method: config.method,
    headers: config.headers,
    body: JSON.stringify(config.body)
  });
}, httpConfig);
```

**方案B: Python requests (备选)**
```python  
# 优势: 功能丰富，但架构复杂
import requests
response = requests.post(url, json=data, headers=headers)
```

**选择理由**:
- ✅ 统一执行环境，减少跨进程通信
- ✅ 自动共享Cookie和认证状态  
- ✅ 简化变量作用域管理
- ✅ 与现有AI步骤协作更自然

#### JSON处理库选择
**jsonpath-ng vs jsonpath-rw**

| 特性 | jsonpath-ng | jsonpath-rw |
|------|-------------|-------------|
| 标准兼容性 | ✅ 高 | ⚠️ 中等 |
| 性能表现 | ✅ 优秀 | ✅ 良好 |
| 维护状态 | ✅ 活跃 | ❌ 较少 |
| 功能完整性 | ✅ 完整 | ⚠️ 有限 |
| 学习成本 | ✅ 低 | ✅ 低 |

**最终选择**: jsonpath-ng

---

## 📦 模块设计

### 前端模块 (Web GUI)

#### HTTP步骤配置组件
```typescript
// HTTPStepConfigComponent.tsx
interface HTTPStepConfig {
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  url: string;
  headers: Record<string, string>;
  body?: any;
  auth?: {
    type: 'bearer' | 'apikey' | 'basic';
    token?: string;
    key?: string;
    username?: string;
    password?: string;
  };
  assertions: Assertion[];
  extractVariables: Record<string, string>;
  timeout: number;
  retries: number;
}
```

#### 变量输入增强组件  
```typescript
// SmartVariableInput扩展
interface VariableInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  supportedTypes: ('string' | 'number' | 'boolean' | 'object')[];
  validationRules?: ValidationRule[];
}
```

### 后端模块 (Python)

#### HTTP步骤执行器
```python  
# web_gui/services/http_step_executor.py
class HTTPStepExecutor:
    def __init__(self, variable_resolver: VariableResolver):
        self.variable_resolver = variable_resolver
        self.logger = logging.getLogger(__name__)
    
    async def execute(self, step_config: dict, execution_context: dict) -> dict:
        """执行HTTP步骤"""
        pass
    
    def _resolve_variables(self, template: str, variables: dict) -> str:
        """解析变量引用"""
        pass
    
    def _extract_variables(self, response: dict, extract_config: dict) -> dict:
        """从响应中提取变量"""
        pass
```

#### 变量提取服务
```python
# web_gui/services/variable_extractor.py  
from jsonpath_ng import parse

class VariableExtractor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def extract_from_response(self, response_data: dict, 
                            extract_config: dict) -> dict:
        """使用JSONPath从响应中提取变量"""
        extracted = {}
        for var_name, json_path in extract_config.items():
            try:
                jsonpath_expr = parse(json_path)
                matches = jsonpath_expr.find(response_data)
                if matches:
                    extracted[var_name] = matches[0].value
                else:
                    self.logger.warning(f"JSONPath未匹配: {json_path}")
            except Exception as e:
                self.logger.error(f"变量提取失败 {var_name}: {e}")
        return extracted
```

### Node.js模块 (MidScene Server)

#### HTTP请求处理器
```javascript
// midscene_server.js - HTTP步骤处理
async function executeHttpStep(page, stepConfig) {
  const { method, url, headers, body, timeout, auth } = stepConfig.params;
  
  try {
    // 在浏览器上下文中执行HTTP请求
    const response = await page.evaluate(async (config) => {
      const startTime = performance.now();
      
      // 处理认证
      const fetchHeaders = { ...config.headers };
      if (config.auth) {
        switch (config.auth.type) {
          case 'bearer':
            fetchHeaders['Authorization'] = `Bearer ${config.auth.token}`;
            break;
          case 'apikey':
            fetchHeaders[config.auth.key] = config.auth.value;
            break;
        }
      }
      
      // 执行fetch请求
      const fetchResponse = await fetch(config.url, {
        method: config.method,
        headers: fetchHeaders,
        body: config.body ? JSON.stringify(config.body) : undefined,
        signal: AbortSignal.timeout(config.timeout * 1000)
      });
      
      const endTime = performance.now();
      let responseData;
      const contentType = fetchResponse.headers.get('content-type');
      
      if (contentType && contentType.includes('application/json')) {
        responseData = await fetchResponse.json();
      } else {
        responseData = await fetchResponse.text();
      }
      
      return {
        status: fetchResponse.status,
        statusText: fetchResponse.statusText,
        headers: Object.fromEntries(fetchResponse.headers.entries()),
        data: responseData,
        timing: {
          total: endTime - startTime,
          start: startTime,
          end: endTime
        },
        url: fetchResponse.url
      };
    }, { method, url, headers, body, timeout, auth });
    
    return await processHttpResponse(response, stepConfig);
    
  } catch (error) {
    throw new Error(`HTTP请求失败: ${error.message}`);
  }
}
```

---

## 🗃️ 数据结构

### HTTP步骤配置数据结构
```json
{
  "action": "http_request",
  "description": "创建用户账号",
  "params": {
    "method": "POST",
    "url": "${baseUrl}/api/users",
    "headers": {
      "Content-Type": "application/json",
      "Authorization": "Bearer ${authToken}",
      "X-API-Key": "${apiKey}"
    },
    "auth": {
      "type": "bearer",
      "token": "${authToken}"
    },
    "body": {
      "username": "${newUserName}",
      "email": "${newUserEmail}",
      "password": "${newUserPassword}"
    },
    "timeout": 30,
    "retries": 3,
    "assertions": [
      {
        "type": "status_code",
        "expected": 201,
        "operator": "eq"
      },
      {
        "type": "response_time", 
        "expected": 5000,
        "operator": "lt"
      },
      {
        "type": "json_path",
        "path": "$.id",
        "condition": "exists"
      },
      {
        "type": "json_content",
        "path": "$.username",
        "expected": "${newUserName}",
        "operator": "eq"
      }
    ],
    "extract_variables": {
      "userId": "$.id",
      "createdAt": "$.created_at", 
      "userStatus": "$.status",
      "responseHeaders": "$headers",
      "responseTime": "$timing.total"
    }
  },
  "output_variable": "user_creation_result",
  "on_error": "continue",
  "retry_on_failure": true
}
```

### 执行结果数据结构
```json
{
  "step_index": 2,
  "action": "http_request", 
  "status": "success",
  "start_time": "2025-08-16T10:30:00.000Z",
  "end_time": "2025-08-16T10:30:02.150Z",
  "duration": 2150,
  "result": {
    "request": {
      "method": "POST",
      "url": "https://api.example.com/users",
      "headers": {
        "Content-Type": "application/json",
        "Authorization": "Bearer abc123"
      },
      "body": {
        "username": "testuser",
        "email": "test@example.com"
      }
    },
    "response": {
      "status": 201,
      "statusText": "Created",
      "headers": {
        "content-type": "application/json",
        "x-request-id": "req-12345"
      },
      "data": {
        "id": 12345,
        "username": "testuser", 
        "email": "test@example.com",
        "created_at": "2025-08-16T10:30:01.000Z",
        "status": "active"
      },
      "timing": {
        "total": 1500,
        "dns": 50,
        "connect": 100,
        "request": 200,
        "response": 1150
      }
    },
    "assertions": [
      {
        "type": "status_code",
        "expected": 201,
        "actual": 201,
        "passed": true
      }
    ],
    "extracted_variables": {
      "userId": 12345,
      "createdAt": "2025-08-16T10:30:01.000Z",
      "userStatus": "active"
    }
  },
  "error": null,
  "retry_count": 0
}
```

### 变量提取配置
```json
{
  "extract_variables": {
    "userId": "$.id",                          // 简单路径
    "userName": "$.user.name",                 // 嵌套路径  
    "firstEmail": "$.users[0].email",          // 数组索引
    "allEmails": "$.users[*].email",           // 数组所有元素
    "responseTime": "$timing.total",           // 特殊路径：时间统计
    "statusCode": "$status",                   // 特殊路径：状态码
    "requestId": "$headers['x-request-id']",   // 特殊路径：响应头
    "hasData": "$.data",                       // 存在性检查
    "countItems": "$.items.length()"          // 计算表达式
  }
}
```

---

## 🔌 接口设计

### REST API接口

#### 创建/更新HTTP步骤
```http
PUT /api/testcases/{id}/steps/{index}
Content-Type: application/json

{
  "action": "http_request",
  "description": "HTTP接口调用",
  "params": {
    "method": "POST",
    "url": "${baseUrl}/api/endpoint",
    "headers": {},
    "body": {},
    "auth": {},
    "timeout": 30,
    "assertions": [],
    "extract_variables": {}
  }
}
```

#### 验证HTTP步骤配置
```http  
POST /api/testcases/steps/validate
Content-Type: application/json

{
  "step_config": {
    "action": "http_request",
    "params": { ... }
  },
  "variables": {
    "baseUrl": "https://api.example.com",
    "authToken": "abc123"
  }
}

Response:
{
  "valid": true,
  "errors": [],
  "resolved_config": { ... }
}
```

### WebSocket事件

#### HTTP步骤执行事件
```json
{
  "event": "http_step_start",
  "data": {
    "execution_id": "exec-123",
    "step_index": 2,
    "method": "POST",
    "url": "https://api.example.com/users"
  }
}

{
  "event": "http_step_complete", 
  "data": {
    "execution_id": "exec-123",
    "step_index": 2,
    "status": "success",
    "duration": 1500,
    "response": {
      "status": 201,
      "data": { ... }
    }
  }
}

{
  "event": "http_step_error",
  "data": {
    "execution_id": "exec-123", 
    "step_index": 2,
    "error": "Connection timeout",
    "retry_count": 1
  }
}
```

---

## 💻 实现细节

### 变量解析实现
```python
import re
from typing import Any, Dict

class VariableResolver:
    def __init__(self, variables: Dict[str, Any]):
        self.variables = variables
        
    def resolve(self, template: str) -> str:
        """解析模板中的变量引用"""
        if not isinstance(template, str):
            return template
            
        # 匹配 ${variable} 和 ${object.property} 格式
        pattern = r'\$\{([^}]+)\}'
        
        def replace_var(match):
            var_path = match.group(1)
            try:
                return str(self._get_nested_value(var_path))
            except (KeyError, AttributeError, TypeError):
                # 如果变量不存在，保持原始引用
                return match.group(0)
                
        return re.sub(pattern, replace_var, template)
    
    def _get_nested_value(self, path: str) -> Any:
        """获取嵌套变量值"""
        parts = path.split('.')
        value = self.variables
        
        for part in parts:
            if isinstance(value, dict):
                value = value[part]
            elif isinstance(value, list):
                value = value[int(part)]
            else:
                raise AttributeError(f"无法访问路径: {path}")
                
        return value
```

### 断言验证实现
```python
class AssertionValidator:
    def __init__(self):
        self.operators = {
            'eq': lambda a, b: a == b,
            'ne': lambda a, b: a != b, 
            'gt': lambda a, b: a > b,
            'gte': lambda a, b: a >= b,
            'lt': lambda a, b: a < b,
            'lte': lambda a, b: a <= b,
            'contains': lambda a, b: b in a,
            'exists': lambda a, b: a is not None,
            'matches': lambda a, b: re.search(b, str(a)) is not None
        }
    
    def validate_assertions(self, response: dict, assertions: list) -> list:
        """验证所有断言"""
        results = []
        
        for assertion in assertions:
            result = self._validate_single_assertion(response, assertion)
            results.append(result)
            
        return results
    
    def _validate_single_assertion(self, response: dict, assertion: dict) -> dict:
        """验证单个断言"""
        assertion_type = assertion['type']
        expected = assertion['expected']
        operator = assertion.get('operator', 'eq')
        
        try:
            if assertion_type == 'status_code':
                actual = response['status']
            elif assertion_type == 'response_time':
                actual = response['timing']['total']
            elif assertion_type == 'json_path':
                path = assertion['path']
                actual = self._extract_json_path(response['data'], path)
            elif assertion_type == 'json_content':
                path = assertion['path'] 
                actual = self._extract_json_path(response['data'], path)
            else:
                raise ValueError(f"未知断言类型: {assertion_type}")
            
            passed = self.operators[operator](actual, expected)
            
            return {
                'type': assertion_type,
                'expected': expected,
                'actual': actual,
                'operator': operator,
                'passed': passed,
                'message': f"断言{'通过' if passed else '失败'}: {actual} {operator} {expected}"
            }
            
        except Exception as e:
            return {
                'type': assertion_type,
                'expected': expected,
                'actual': None,
                'operator': operator,
                'passed': False,
                'message': f"断言执行错误: {str(e)}"
            }
```

### 错误处理和重试机制
```python
import asyncio
from typing import Optional

class HTTPRequestHandler:
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        
    async def execute_with_retry(self, request_func, step_config: dict) -> dict:
        """带重试的HTTP请求执行"""
        retries = 0
        last_error = None
        
        while retries <= self.max_retries:
            try:
                response = await request_func(step_config)
                
                # 检查是否需要重试（基于状态码）
                if self._should_retry(response, step_config):
                    retries += 1
                    if retries <= self.max_retries:
                        wait_time = self._calculate_backoff_time(retries)
                        await asyncio.sleep(wait_time)
                        continue
                
                return response
                
            except Exception as e:
                last_error = e
                retries += 1
                
                if retries <= self.max_retries:
                    wait_time = self._calculate_backoff_time(retries)
                    await asyncio.sleep(wait_time)
                else:
                    break
        
        # 重试次数用尽，抛出最后一个错误
        raise Exception(f"HTTP请求失败，重试{self.max_retries}次: {str(last_error)}")
    
    def _should_retry(self, response: dict, config: dict) -> bool:
        """判断是否应该重试"""
        status = response.get('status', 0)
        retry_codes = config.get('retry_status_codes', [500, 502, 503, 504])
        return status in retry_codes
        
    def _calculate_backoff_time(self, retry_count: int) -> float:
        """计算退避等待时间（指数退避）"""
        return min(2 ** retry_count, 30)  # 最大等待30秒
```

---

## 🚀 部署方案

### 开发环境部署
```bash
# 1. 安装Python依赖
pip install jsonpath-ng>=1.5.0

# 2. 更新Node.js依赖 (如果需要)
npm install

# 3. 数据库迁移 (如果有新字段)
python web_gui/migrations/add_http_step_support.py

# 4. 启动开发服务
python web_gui/run_enhanced.py
node midscene_server.js
```

### 生产环境部署
```yaml
# docker-compose.yml 更新
version: '3.8'
services:
  web:
    build: .
    environment:
      - ENABLE_HTTP_STEPS=true
      - HTTP_REQUEST_TIMEOUT=30
      - HTTP_MAX_RETRIES=3
    volumes:
      - ./web_gui:/app/web_gui
      
  midscene:
    build: .
    command: node midscene_server.js
    environment:
      - HTTP_REQUEST_ENABLED=true
    volumes:
      - ./midscene_server.js:/app/midscene_server.js
```

### 配置管理
```python
# web_gui/config/http_settings.py
class HTTPStepSettings:
    # 默认超时时间 (秒)
    DEFAULT_TIMEOUT = 30
    
    # 最大重试次数
    MAX_RETRIES = 3
    
    # 支持的HTTP方法
    SUPPORTED_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']
    
    # 支持的认证类型
    SUPPORTED_AUTH_TYPES = ['bearer', 'apikey', 'basic']
    
    # 默认请求头
    DEFAULT_HEADERS = {
        'User-Agent': 'Intent-Test-Framework/1.0',
        'Accept': 'application/json'
    }
    
    # JSONPath提取器配置
    JSONPATH_CONFIG = {
        'auto_id': True,        # 自动处理数字ID
        'debug': False          # 调试模式
    }
```

---

## 📊 监控和日志

### 日志记录策略
```python
import logging

# HTTP步骤专用日志记录器
http_logger = logging.getLogger('intent_test.http_step')

class HTTPStepLogger:
    def __init__(self, execution_id: str, step_index: int):
        self.execution_id = execution_id
        self.step_index = step_index
        self.logger = http_logger
        
    def log_request(self, method: str, url: str, headers: dict, body: any):
        """记录HTTP请求"""
        self.logger.info(f"[{self.execution_id}:{self.step_index}] "
                        f"HTTP {method} {url}")
        self.logger.debug(f"请求头: {headers}")
        if body:
            self.logger.debug(f"请求体: {body}")
    
    def log_response(self, status: int, timing: float, data_size: int):
        """记录HTTP响应"""
        self.logger.info(f"[{self.execution_id}:{self.step_index}] "
                        f"响应: {status}, {timing}ms, {data_size}bytes")
    
    def log_variable_extraction(self, extracted: dict):
        """记录变量提取"""
        self.logger.info(f"[{self.execution_id}:{self.step_index}] "
                        f"提取变量: {list(extracted.keys())}")
        self.logger.debug(f"变量值: {extracted}")
```

### 性能监控
```python
class HTTPStepMetrics:
    def __init__(self):
        self.request_count = 0
        self.success_count = 0
        self.error_count = 0
        self.total_time = 0
        self.response_times = []
        
    def record_request(self, success: bool, response_time: float):
        """记录请求指标"""
        self.request_count += 1
        if success:
            self.success_count += 1
        else:
            self.error_count += 1
        
        self.total_time += response_time
        self.response_times.append(response_time)
        
        # 保持最近1000个响应时间
        if len(self.response_times) > 1000:
            self.response_times.pop(0)
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        if self.request_count == 0:
            return {}
            
        return {
            'total_requests': self.request_count,
            'success_rate': self.success_count / self.request_count,
            'average_response_time': self.total_time / self.request_count,
            'p95_response_time': self._percentile(self.response_times, 0.95),
            'p99_response_time': self._percentile(self.response_times, 0.99)
        }
```

---

## 🧪 测试策略

### 单元测试
```python
# tests/test_http_step_executor.py
import pytest
from web_gui.services.http_step_executor import HTTPStepExecutor

class TestHTTPStepExecutor:
    def test_variable_resolution(self):
        """测试变量解析功能"""
        variables = {'baseUrl': 'https://api.example.com', 'userId': 123}
        resolver = VariableResolver(variables)
        
        result = resolver.resolve('${baseUrl}/users/${userId}')
        assert result == 'https://api.example.com/users/123'
    
    def test_json_extraction(self):
        """测试JSON变量提取"""
        response_data = {'user': {'id': 123, 'name': 'John'}}
        extractor = VariableExtractor()
        
        result = extractor.extract_from_response(
            response_data, 
            {'userId': '$.user.id', 'userName': '$.user.name'}
        )
        
        assert result == {'userId': 123, 'userName': 'John'}
```

### 集成测试
```python
# tests/test_http_integration.py
@pytest.mark.asyncio
async def test_http_step_integration():
    """测试HTTP步骤的完整执行流程"""
    step_config = {
        'action': 'http_request',
        'params': {
            'method': 'GET',
            'url': 'https://httpbin.org/json',
            'extract_variables': {
                'slideshow_title': '$.slideshow.title'
            }
        }
    }
    
    executor = HTTPStepExecutor(variable_resolver)
    result = await executor.execute(step_config, {})
    
    assert result['status'] == 'success'
    assert 'slideshow_title' in result['extracted_variables']
```

---

*本技术设计文档将根据实现过程中的技术细节持续更新和完善*