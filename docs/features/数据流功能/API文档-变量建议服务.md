# 变量建议服务API文档

**版本**: v1.0  
**实现日期**: 2025年1月31日  
**对应Story**: STORY-011  

---

## 📖 概述

变量建议服务提供了完整的后端API支持，为前端智能变量提示组件提供数据服务。实现了模糊搜索、属性探索、引用验证等核心功能。

### 基础URL
```
Production: https://intent-test-framework.vercel.app/api
Development: http://localhost:5000/api
```

### 认证
当前版本暂未启用认证，后续版本将支持API密钥认证。

### 响应格式
所有新版API（v1）统一返回JSON格式，旧版API保持原有格式以确保向后兼容。

---

## 🔧 API端点

### 1. 变量建议API (AC-1)

获取当前执行上下文中的所有可用变量及其元数据。

#### 新版端点
```http
GET /api/v1/executions/{execution_id}/variable-suggestions
```

**查询参数**:
- `step_index` (integer, optional): 当前步骤索引，只返回之前步骤的变量
- `include_properties` (boolean, optional): 是否包含对象属性信息，默认true
- `limit` (integer, optional): 限制返回数量

**响应示例**:
```json
{
  "execution_id": "exec-001",
  "current_step_index": 5,
  "variables": [
    {
      "name": "product_info",
      "data_type": "object", 
      "source_step_index": 2,
      "source_api_method": "aiQuery",
      "created_at": "2025-01-30T10:00:00Z",
      "preview_value": "{\"name\": \"iPhone 15\", \"price\": 999}",
      "properties": [
        {"name": "name", "type": "string", "value": "iPhone 15", "path": "product_info.name"},
        {"name": "price", "type": "number", "value": 999, "path": "product_info.price"}
      ]
    }
  ],
  "total_count": 3
}
```

#### 兼容端点
```http
GET /api/executions/{execution_id}/variable-suggestions
```

**响应格式**:
```json
{
  "code": 200,
  "data": {
    "execution_id": "exec-001",
    "suggestions": [...],
    "count": 3
  },
  "message": "获取变量建议成功"
}
```

---

### 2. 对象属性探索API (AC-2)

获取指定变量的所有可访问属性，支持嵌套对象探索。

#### 新版端点
```http
GET /api/v1/executions/{execution_id}/variables/{variable_name}/properties
```

**查询参数**:
- `max_depth` (integer, optional): 最大探索深度，默认3

**响应示例**:
```json
{
  "variable_name": "product_info",
  "data_type": "object",
  "properties": [
    {
      "name": "name",
      "type": "string", 
      "value": "iPhone 15",
      "path": "product_info.name"
    },
    {
      "name": "specs",
      "type": "object",
      "value": {"color": "blue", "storage": "128GB"},
      "path": "product_info.specs",
      "properties": [
        {"name": "color", "type": "string", "value": "blue", "path": "product_info.specs.color"},
        {"name": "storage", "type": "string", "value": "128GB", "path": "product_info.specs.storage"}
      ]
    }
  ]
}
```

**错误响应**:
```json
{
  "error": "变量 {variable_name} 不存在"
}
```
HTTP状态码: 404

---

### 3. 变量名模糊搜索API (AC-3)

根据用户输入进行模糊搜索，返回匹配的变量列表，按相关性排序。

#### 端点
```http
GET /api/v1/executions/{execution_id}/variable-suggestions/search
```

**查询参数**:
- `q` (string, required): 搜索查询字符串
- `limit` (integer, optional): 结果限制，默认10
- `step_index` (integer, optional): 步骤索引过滤

**请求示例**:
```http
GET /api/v1/executions/exec-001/variable-suggestions/search?q=prod&limit=5
```

**响应示例**:
```json
{
  "query": "prod",
  "matches": [
    {
      "name": "product_info",
      "match_score": 0.95,
      "highlighted_name": "<mark>prod</mark>uct_info",
      "data_type": "object",
      "source_step_index": 2,
      "preview_value": "{\"name\": \"iPhone\", \"price\": 999}"
    },
    {
      "name": "product_name", 
      "match_score": 0.88,
      "highlighted_name": "<mark>prod</mark>uct_name",
      "data_type": "string",
      "source_step_index": 1,
      "preview_value": "\"iPhone 15\""
    }
  ],
  "count": 2
}
```

**搜索算法**:
- 精确匹配: +0.5分
- 前缀匹配: +0.3分
- 子字符串匹配: +0.2分
- 单词前缀匹配: +0.15分
- 最低阈值: 0.2分

---

### 4. 变量引用验证API (AC-4)

验证变量引用的有效性，返回详细的错误信息和建议。

#### 端点
```http
POST /api/v1/executions/{execution_id}/variables/validate
```

**请求体**:
```json
{
  "references": [
    "${product_info.name}",
    "${product_info.specs.color}",
    "${undefined_var}",
    "${product_info.invalid_prop}"
  ],
  "step_index": 5
}
```

**响应示例**:
```json
{
  "validation_results": [
    {
      "reference": "${product_info.name}",
      "is_valid": true,
      "resolved_value": "iPhone 15",
      "data_type": "str"
    },
    {
      "reference": "${product_info.specs.color}",
      "is_valid": true, 
      "resolved_value": "blue",
      "data_type": "str"
    },
    {
      "reference": "${undefined_var}",
      "is_valid": false,
      "error": "变量 'undefined_var' 未定义",
      "suggestion": "可用变量: product_info, user_name, item_count"
    },
    {
      "reference": "${product_info.invalid_prop}",
      "is_valid": false,
      "error": "属性 'invalid_prop' 在对象中不存在",
      "suggestion": "可用属性: name, price, specs"
    }
  ]
}
```

**验证规则**:
- 引用格式: `${variable_name}` 或 `${variable.property}`
- 变量存在性检查
- 属性路径有效性验证
- 数组索引边界检查
- 类型兼容性验证

---

### 5. 实时变量状态API (AC-5)

获取执行过程中的实时变量状态和使用统计。

#### 端点
```http
GET /api/v1/executions/{execution_id}/variables/status
```

**响应示例**:
```json
{
  "execution_id": "exec-001",
  "execution_status": "running",
  "current_step_index": 5,
  "variables_count": 3,
  "variables": [
    {
      "name": "product_info",
      "status": "available",
      "last_updated": "2025-01-30T10:05:00Z",
      "usage_count": 2
    },
    {
      "name": "user_name", 
      "status": "available",
      "last_updated": "2025-01-30T10:01:00Z", 
      "usage_count": 1
    }
  ],
  "recent_references": [
    {
      "step_index": 4,
      "reference": "${product_info.price}",
      "status": "success"
    }
  ]
}
```

**状态类型**:
- `available`: 变量可用
- `pending`: 正在生成中
- `error`: 生成失败
- `expired`: 已过期

---

## ⚡ 性能规格 (AC-6)

### 响应时间要求
- 变量建议API: < 200ms
- 属性探索API: < 300ms  
- 模糊搜索API: < 150ms
- 引用验证API: < 250ms
- 状态查询API: < 100ms

### 缓存策略
- 变量数据缓存: 60秒
- 属性结构缓存: 300秒
- 搜索结果缓存: 30秒

### 限制和配额
- 搜索结果最大数量: 50
- 属性探索最大深度: 5
- 引用验证最大数量: 20
- 并发请求限制: 100/分钟

---

## 🔧 错误处理

### 标准错误格式
```json
{
  "error": "错误描述信息",
  "code": "ERROR_CODE",
  "details": {
    "field": "specific_error_info"
  }
}
```

### 常见错误码
- `400`: 请求参数错误
- `404`: 资源不存在
- `429`: 请求频率超限
- `500`: 服务器内部错误

### 错误示例
```json
{
  "error": "搜索查询不能为空",
  "code": "INVALID_QUERY",
  "details": {
    "parameter": "q",
    "value": ""
  }
}
```

---

## 📚 使用示例

### JavaScript前端调用
```javascript
// 获取变量建议
async function getVariableSuggestions(executionId, stepIndex) {
  const response = await fetch(
    `/api/v1/executions/${executionId}/variable-suggestions?step_index=${stepIndex}`
  );
  return response.json();
}

// 搜索变量
async function searchVariables(executionId, query) {
  const response = await fetch(
    `/api/v1/executions/${executionId}/variable-suggestions/search?q=${encodeURIComponent(query)}`
  );
  return response.json();
}

// 验证引用
async function validateReferences(executionId, references) {
  const response = await fetch(
    `/api/v1/executions/${executionId}/variables/validate`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ references })
    }
  );
  return response.json();
}
```

### Python后端调用
```python
import requests

def get_variable_suggestions(execution_id, step_index=None):
    url = f"/api/v1/executions/{execution_id}/variable-suggestions"
    params = {}
    if step_index is not None:
        params['step_index'] = step_index
    
    response = requests.get(url, params=params)
    return response.json()

def validate_variable_references(execution_id, references):
    url = f"/api/v1/executions/{execution_id}/variables/validate"
    data = {'references': references}
    
    response = requests.post(url, json=data)
    return response.json()
```

---

## 🧪 测试环境

### 测试数据
测试环境提供了丰富的模拟数据，包括：
- 多种数据类型的变量
- 嵌套对象结构
- 数组和复杂数据
- 错误场景模拟

### 测试端点
```
Test Base URL: http://localhost:5000/api
Test Execution ID: test-execution-123
```

### 示例测试请求
```bash
# 获取变量建议
curl "http://localhost:5000/api/v1/executions/test-execution-123/variable-suggestions"

# 搜索变量
curl "http://localhost:5000/api/v1/executions/test-execution-123/variable-suggestions/search?q=user"

# 验证引用
curl -X POST "http://localhost:5000/api/v1/executions/test-execution-123/variables/validate" \
  -H "Content-Type: application/json" \
  -d '{"references": ["${user_name}", "${product_info.price}"]}'
```

---

## 📈 监控和调试

### 健康检查
```http
GET /api/health
```

### 指标端点
```http
GET /api/metrics
```

### 日志配置
- 请求日志: INFO级别
- 错误日志: ERROR级别
- 性能日志: DEBUG级别

---

## 🔮 未来计划

### v1.1 计划功能
- [ ] Redis缓存集成
- [ ] API密钥认证
- [ ] 更丰富的搜索算法
- [ ] 实时WebSocket推送

### v1.2 计划功能
- [ ] 变量依赖关系分析
- [ ] 自动补全建议优化
- [ ] 批量操作支持
- [ ] 性能监控面板

---

**文档版本**: 1.0  
**最后更新**: 2025年1月31日  
**维护者**: Intent Test Framework Team