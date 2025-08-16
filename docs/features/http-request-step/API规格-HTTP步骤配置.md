# HTTP步骤配置API规格文档

## 文档信息
- **功能名称**: HTTP接口调用步骤API规格
- **版本**: v1.0
- **创建日期**: 2025-08-16
- **文档类型**: API规格文档
- **状态**: 规格定义完成

## 📋 目录
1. [步骤配置格式](#步骤配置格式)
2. [参数详细说明](#参数详细说明)
3. [响应数据格式](#响应数据格式)
4. [REST API接口](#rest-api接口)
5. [配置示例](#配置示例)
6. [错误码定义](#错误码定义)

---

## 🔧 步骤配置格式

### 基础配置结构
```typescript
interface HTTPStepConfig {
  action: "http_request";
  description?: string;
  params: HTTPRequestParams;
  output_variable?: string;
  on_error?: "continue" | "stop";
  retry_on_failure?: boolean;
}

interface HTTPRequestParams {
  method: HTTPMethod;
  url: string;
  headers?: Record<string, string>;
  body?: any;
  auth?: AuthConfig;
  timeout?: number;
  retries?: number;
  assertions?: Assertion[];
  extract_variables?: Record<string, string>;
  retry_status_codes?: number[];
}
```

### 支持的HTTP方法
```typescript
type HTTPMethod = "GET" | "POST" | "PUT" | "DELETE" | "PATCH";
```

### 认证配置
```typescript
interface AuthConfig {
  type: "bearer" | "apikey" | "basic" | "custom";
  
  // Bearer Token认证
  token?: string;
  
  // API Key认证  
  key?: string;
  value?: string;
  location?: "header" | "query";
  
  // Basic Auth认证
  username?: string;
  password?: string;
  
  // 自定义认证
  headers?: Record<string, string>;
  query?: Record<string, string>;
}
```

### 断言配置
```typescript
interface Assertion {
  type: AssertionType;
  description?: string;
  expected: any;
  operator?: ComparisonOperator;
  path?: string; // 用于json_path和json_content类型
}

type AssertionType = 
  | "status_code" 
  | "response_time"
  | "json_path"
  | "json_content"
  | "header_value"
  | "body_contains"
  | "body_matches";

type ComparisonOperator = 
  | "eq"      // 等于
  | "ne"      // 不等于  
  | "gt"      // 大于
  | "gte"     // 大于等于
  | "lt"      // 小于
  | "lte"     // 小于等于
  | "contains"// 包含
  | "exists"  // 存在
  | "matches"; // 正则匹配
```

---

## 📝 参数详细说明

### 必需参数

#### `method` (HTTPMethod)
- **描述**: HTTP请求方法
- **类型**: 枚举值
- **可选值**: `GET`, `POST`, `PUT`, `DELETE`, `PATCH`
- **默认值**: 无，必须指定
- **示例**: `"POST"`

#### `url` (string)
- **描述**: 请求URL，支持变量替换
- **类型**: 字符串
- **格式**: 有效的HTTP/HTTPS URL
- **变量支持**: 是，使用`${variable}`语法
- **示例**: `"${baseUrl}/api/users/${userId}"`

### 可选参数

#### `headers` (Record<string, string>)
- **描述**: 请求头键值对
- **类型**: 对象
- **默认值**: `{}`
- **变量支持**: 值支持变量替换
- **示例**:
  ```json
  {
    "Content-Type": "application/json",
    "Authorization": "Bearer ${authToken}",
    "X-API-Key": "${apiKey}"
  }
  ```

#### `body` (any)
- **描述**: 请求体数据
- **类型**: 任意类型（通常为对象或字符串）
- **默认值**: `null`
- **变量支持**: 是，对象属性和字符串值均支持
- **说明**: GET和DELETE请求通常不需要body
- **示例**:
  ```json
  {
    "username": "${userName}",
    "email": "${userEmail}",
    "age": 25,
    "active": true
  }
  ```

#### `timeout` (number)
- **描述**: 请求超时时间（秒）
- **类型**: 整数
- **范围**: 1-300
- **默认值**: `30`
- **示例**: `60`

#### `retries` (number)
- **描述**: 最大重试次数
- **类型**: 整数
- **范围**: 0-10
- **默认值**: `3`
- **示例**: `5`

#### `retry_status_codes` (number[])
- **描述**: 触发重试的HTTP状态码
- **类型**: 数字数组
- **默认值**: `[500, 502, 503, 504]`
- **示例**: `[429, 500, 502, 503, 504]`

### 认证参数说明

#### Bearer Token认证
```json
{
  "auth": {
    "type": "bearer",
    "token": "${authToken}"
  }
}
```

#### API Key认证
```json
{
  "auth": {
    "type": "apikey",
    "key": "X-API-Key",
    "value": "${apiKey}",
    "location": "header"
  }
}
```

#### Basic Auth认证
```json
{
  "auth": {
    "type": "basic", 
    "username": "${apiUser}",
    "password": "${apiPassword}"
  }
}
```

### 断言参数说明

#### 状态码断言
```json
{
  "type": "status_code",
  "expected": 201,
  "operator": "eq"
}
```

#### 响应时间断言
```json
{
  "type": "response_time",
  "expected": 5000,
  "operator": "lt"
}
```

#### JSON内容断言
```json
{
  "type": "json_content",
  "path": "$.user.id",
  "expected": "${expectedUserId}",
  "operator": "eq"
}
```

#### JSON路径存在性断言
```json
{
  "type": "json_path",
  "path": "$.data.items",
  "expected": true,
  "operator": "exists"
}
```

### 变量提取配置

#### 基础提取
```json
{
  "extract_variables": {
    "userId": "$.id",
    "userName": "$.username", 
    "userEmail": "$.email"
  }
}
```

#### 高级提取
```json
{
  "extract_variables": {
    "userId": "$.user.id",
    "firstItemName": "$.items[0].name",
    "allEmails": "$.users[*].email",
    "responseTime": "$timing.total",
    "statusCode": "$status",
    "requestId": "$headers['x-request-id']",
    "itemCount": "$.items.length()"
  }
}
```

---

## 📤 响应数据格式

### 执行结果结构
```typescript
interface HTTPStepResult {
  step_index: number;
  action: "http_request";
  status: "success" | "failed" | "error";
  start_time: string; // ISO 8601格式
  end_time: string;
  duration: number;   // 毫秒
  result: HTTPExecutionResult;
  error?: string;
  retry_count: number;
}

interface HTTPExecutionResult {
  request: HTTPRequestDetails;
  response: HTTPResponseDetails;
  assertions: AssertionResult[];
  extracted_variables: Record<string, any>;
}
```

### 请求详情
```typescript
interface HTTPRequestDetails {
  method: string;
  url: string;
  headers: Record<string, string>;
  body?: any;
  resolved_url: string;      // 变量解析后的实际URL
  resolved_headers: Record<string, string>; // 解析后的请求头
  resolved_body?: any;       // 解析后的请求体
}
```

### 响应详情
```typescript
interface HTTPResponseDetails {
  status: number;
  status_text: string;
  headers: Record<string, string>;
  data: any;
  timing: TimingDetails;
  size: {
    headers: number;    // 响应头大小（字节）
    body: number;      // 响应体大小（字节）
    total: number;     // 总大小（字节）
  };
}

interface TimingDetails {
  total: number;       // 总耗时（毫秒）
  dns: number;        // DNS解析时间
  connect: number;    // 连接时间
  tls: number;        // TLS握手时间
  request: number;    // 请求发送时间
  response: number;   // 响应接收时间
}
```

### 断言结果
```typescript
interface AssertionResult {
  type: string;
  description?: string;
  expected: any;
  actual: any;
  operator: string;
  passed: boolean;
  message: string;
  execution_time: number; // 断言执行时间（毫秒）
}
```

---

## 🌐 REST API接口

### 创建/更新HTTP步骤
```http
PUT /api/testcases/{testcase_id}/steps/{step_index}
Content-Type: application/json
Authorization: Bearer {token}

{
  "action": "http_request",
  "description": "创建用户账号",
  "params": {
    "method": "POST",
    "url": "${baseUrl}/api/users",
    "headers": {
      "Content-Type": "application/json"
    },
    "body": {
      "username": "${userName}",
      "email": "${userEmail}"
    },
    "auth": {
      "type": "bearer",
      "token": "${authToken}"
    },
    "assertions": [
      {
        "type": "status_code",
        "expected": 201
      }
    ],
    "extract_variables": {
      "userId": "$.id"
    }
  },
  "output_variable": "user_creation_result"
}
```

**响应示例**:
```json
{
  "code": 200,
  "message": "HTTP步骤创建成功",
  "data": {
    "step_index": 2,
    "action": "http_request",
    "description": "创建用户账号",
    "params": { /* ... */ },
    "created_at": "2025-08-16T10:30:00.000Z",
    "updated_at": "2025-08-16T10:30:00.000Z"
  }
}
```

### 验证HTTP步骤配置
```http
POST /api/http-steps/validate
Content-Type: application/json

{
  "step_config": {
    "action": "http_request",
    "params": {
      "method": "GET",
      "url": "${baseUrl}/api/users/${userId}",
      "headers": {
        "Authorization": "Bearer ${token}"
      }
    }
  },
  "variables": {
    "baseUrl": "https://api.example.com",
    "userId": 123,
    "token": "abc123def456"
  }
}
```

**响应示例**:
```json
{
  "code": 200,
  "data": {
    "valid": true,
    "errors": [],
    "resolved_config": {
      "method": "GET",
      "url": "https://api.example.com/api/users/123",
      "headers": {
        "Authorization": "Bearer abc123def456"
      }
    },
    "estimated_size": {
      "headers": 156,
      "body": 0,
      "total": 156
    }
  }
}
```

### 测试HTTP步骤执行
```http
POST /api/http-steps/test
Content-Type: application/json

{
  "step_config": {
    "action": "http_request",
    "params": {
      "method": "GET",
      "url": "https://httpbin.org/json"
    }
  }
}
```

**响应示例**:
```json
{
  "code": 200,
  "data": {
    "status": "success",
    "execution_time": 1250,
    "response": {
      "status": 200,
      "data": {
        "slideshow": {
          "title": "Sample Slideshow"
        }
      }
    }
  }
}
```

---

## 📚 配置示例

### 示例1: 用户注册API测试
```json
{
  "action": "http_request",
  "description": "注册新用户",
  "params": {
    "method": "POST",
    "url": "${apiBaseUrl}/auth/register",
    "headers": {
      "Content-Type": "application/json",
      "X-Client-Version": "1.0.0"
    },
    "body": {
      "username": "${testUserName}",
      "email": "${testUserEmail}",
      "password": "${testUserPassword}",
      "firstName": "${firstName}",
      "lastName": "${lastName}"
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
        "expected": 10000,
        "operator": "lt"
      },
      {
        "type": "json_content",
        "path": "$.user.username",
        "expected": "${testUserName}",
        "operator": "eq"
      },
      {
        "type": "json_path",
        "path": "$.user.id",
        "expected": true,
        "operator": "exists"
      }
    ],
    "extract_variables": {
      "newUserId": "$.user.id",
      "accessToken": "$.tokens.access_token",
      "refreshToken": "$.tokens.refresh_token",
      "userStatus": "$.user.status"
    }
  },
  "output_variable": "registration_result"
}
```

### 示例2: 带认证的数据获取
```json
{
  "action": "http_request", 
  "description": "获取用户详情",
  "params": {
    "method": "GET",
    "url": "${apiBaseUrl}/users/${userId}",
    "headers": {
      "Accept": "application/json"
    },
    "auth": {
      "type": "bearer",
      "token": "${accessToken}"
    },
    "timeout": 15,
    "assertions": [
      {
        "type": "status_code",
        "expected": 200,
        "operator": "eq"
      },
      {
        "type": "json_content",
        "path": "$.id",
        "expected": "${userId}",
        "operator": "eq"
      }
    ],
    "extract_variables": {
      "userProfile": "$",
      "lastLoginAt": "$.last_login_at",
      "userRoles": "$.roles[*].name"
    }
  }
}
```

### 示例3: 文件上传API
```json
{
  "action": "http_request",
  "description": "上传用户头像",
  "params": {
    "method": "POST",
    "url": "${apiBaseUrl}/users/${userId}/avatar",
    "headers": {
      "Authorization": "Bearer ${accessToken}"
    },
    "body": {
      "file": "${uploadFileContent}",
      "filename": "${uploadFileName}",
      "contentType": "image/jpeg"
    },
    "timeout": 60,
    "assertions": [
      {
        "type": "status_code",
        "expected": 200,
        "operator": "eq"
      },
      {
        "type": "json_path",
        "path": "$.avatar_url",
        "expected": true,
        "operator": "exists"
      }
    ],
    "extract_variables": {
      "avatarUrl": "$.avatar_url",
      "fileSize": "$.file_size",
      "uploadedAt": "$.uploaded_at"
    }
  }
}
```

### 示例4: 批量操作验证
```json
{
  "action": "http_request",
  "description": "批量删除用户",
  "params": {
    "method": "DELETE",
    "url": "${apiBaseUrl}/users/batch",
    "headers": {
      "Content-Type": "application/json"
    },
    "auth": {
      "type": "bearer",
      "token": "${adminToken}"
    },
    "body": {
      "user_ids": ["${userId1}", "${userId2}", "${userId3}"],
      "reason": "Test cleanup"
    },
    "assertions": [
      {
        "type": "status_code",
        "expected": 200,
        "operator": "eq"
      },
      {
        "type": "json_content",
        "path": "$.deleted_count",
        "expected": 3,
        "operator": "eq"
      },
      {
        "type": "json_path",
        "path": "$.failed_ids",
        "expected": [],
        "operator": "eq"
      }
    ],
    "extract_variables": {
      "deletedCount": "$.deleted_count",
      "failedIds": "$.failed_ids",
      "operationId": "$.operation_id"
    }
  }
}
```

---

## ❌ 错误码定义

### HTTP步骤特定错误码

| 错误码 | 错误名称 | 描述 | 解决建议 |
|--------|---------|------|----------|
| **H001** | INVALID_METHOD | 不支持的HTTP方法 | 使用GET/POST/PUT/DELETE/PATCH |
| **H002** | INVALID_URL | URL格式错误 | 检查URL格式，必须以http://或https://开头 |
| **H003** | VARIABLE_NOT_FOUND | 引用的变量不存在 | 检查变量名称拼写，确认变量在前面步骤中已定义 |
| **H004** | INVALID_JSON | 请求体JSON格式错误 | 检查JSON语法，使用JSON验证工具 |
| **H005** | AUTH_CONFIG_ERROR | 认证配置错误 | 检查认证类型和必需参数 |
| **H006** | TIMEOUT_ERROR | 请求超时 | 增加超时时间或检查网络连接 |
| **H007** | CONNECTION_ERROR | 网络连接错误 | 检查网络连接和目标服务器状态 |
| **H008** | ASSERTION_FAILED | 断言验证失败 | 检查断言条件和实际响应值 |
| **H009** | VARIABLE_EXTRACTION_ERROR | 变量提取失败 | 检查JSONPath表达式和响应结构 |
| **H010** | RETRY_EXHAUSTED | 重试次数用尽 | 检查服务器状态，增加重试次数或修复根本问题 |

### 通用错误响应格式
```json
{
  "code": 400,
  "message": "HTTP步骤配置错误",
  "error_code": "H002",
  "error_details": {
    "field": "params.url",
    "provided_value": "invalid-url",
    "expected_format": "http://... or https://...",
    "suggestion": "请提供完整的HTTP或HTTPS URL"
  },
  "timestamp": "2025-08-16T10:30:00.000Z",
  "request_id": "req-abc123"
}
```

### 执行时错误响应
```json
{
  "step_index": 2,
  "action": "http_request",
  "status": "failed",
  "error": {
    "code": "H006",
    "message": "HTTP请求超时",
    "details": {
      "timeout": 30000,
      "elapsed": 30001,
      "url": "https://api.example.com/slow-endpoint"
    },
    "retry_count": 3,
    "next_action": "step_failed"
  }
}
```

---

## 🔄 版本兼容性

### v1.0 支持的功能
- ✅ 基础HTTP方法 (GET/POST/PUT/DELETE/PATCH)
- ✅ 变量引用和提取
- ✅ 基础认证 (Bearer Token, API Key, Basic Auth)  
- ✅ 响应断言 (状态码、时间、内容)
- ✅ 错误处理和重试

### 未来版本计划
- 🔮 v1.1: 文件上传/下载支持
- 🔮 v1.2: GraphQL请求支持
- 🔮 v1.3: WebSocket连接支持
- 🔮 v2.0: 批量请求和并发控制

---

*本API规格文档将随着功能迭代持续更新，确保与实际实现保持一致*