# STORY-011: 实现变量提示API

**Story ID**: STORY-011  
**Epic**: EPIC-001 数据流核心功能  
**Sprint**: Sprint 3  
**优先级**: High  
**估算**: 5 Story Points  
**分配给**: Backend Developer  
**创建日期**: 2025-01-30  
**产品经理**: John  

---

## 📖 故事描述

**作为** 前端开发工程师  
**我希望** 有完善的后端API来支持智能变量提示功能  
**以便** SmartVariableInput组件能够获取变量数据、对象属性和实时建议  
**这样** 前后端就能协作提供流畅的IDE级智能提示体验  

---

## 🎯 验收标准

### AC-1: 变量建议API
**给定** 前端组件需要获取可用变量列表  
**当** 调用变量建议API时  
**那么** 应该返回当前执行上下文中的所有可用变量及其元数据  

**API规格**:
```
GET /api/v1/executions/{execution_id}/variable-suggestions?step_index={current_step}

Response:
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
        {"name": "name", "type": "string", "value": "iPhone 15"},
        {"name": "price", "type": "number", "value": 999}
      ]
    }
  ],
  "total_count": 3
}
```

### AC-2: 对象属性探索API
**给定** 前端需要获取对象变量的属性列表  
**当** 调用属性探索API时  
**那么** 应该返回指定变量的所有可访问属性  

**API规格**:
```
GET /api/v1/executions/{execution_id}/variables/{variable_name}/properties

Response:
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
      "name": "price", 
      "type": "number",
      "value": 999,
      "path": "product_info.price"
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

### AC-3: 变量名模糊搜索API
**给定** 用户输入部分变量名进行搜索  
**当** 调用模糊搜索API时  
**那么** 应该返回匹配的变量列表，按相关性排序  

**API规格**:
```
GET /api/v1/executions/{execution_id}/variable-suggestions/search?q={query}&limit={limit}

Examples:
- /search?q=prod -> 匹配 "product_info", "product_name"
- /search?q=info -> 匹配 "product_info", "user_info"

Response:
{
  "query": "prod",
  "matches": [
    {
      "name": "product_info",
      "match_score": 0.95,
      "highlighted_name": "<mark>prod</mark>uct_info",
      "data_type": "object",
      "source_step_index": 2
    },
    {
      "name": "product_name", 
      "match_score": 0.88,
      "highlighted_name": "<mark>prod</mark>uct_name",
      "data_type": "string",
      "source_step_index": 1
    }
  ]
}
```

### AC-4: 变量引用验证API
**给定** 前端需要验证变量引用的有效性  
**当** 调用验证API时  
**那么** 应该返回引用是否有效以及详细的错误信息  

**API规格**:
```
POST /api/v1/executions/{execution_id}/variables/validate

Request Body:
{
  "references": [
    "${product_info.name}",
    "${product_info.specs.color}",
    "${undefined_var}",
    "${product_info.invalid_prop}"
  ],
  "step_index": 5
}

Response:
{
  "validation_results": [
    {
      "reference": "${product_info.name}",
      "is_valid": true,
      "resolved_value": "iPhone 15",
      "data_type": "string"
    },
    {
      "reference": "${product_info.specs.color}",
      "is_valid": true, 
      "resolved_value": "blue",
      "data_type": "string"
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

### AC-5: 实时变量状态API
**给定** 前端需要获取执行过程中的实时变量状态  
**当** 调用状态API时  
**那么** 应该返回当前所有变量的最新状态  

**API规格**:
```
GET /api/v1/executions/{execution_id}/variables/status

Response:
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

### AC-6: 性能和缓存要求
**给定** 智能提示需要快速响应  
**当** API处理请求时  
**那么** 应该在合理时间内返回结果并使用适当的缓存策略  

**性能要求**:
- 变量建议API响应时间 < 200ms
- 属性探索API响应时间 < 300ms  
- 模糊搜索API响应时间 < 150ms
- 支持Redis缓存优化频繁访问的数据
- 合理的HTTP缓存头设置

---

## 🔧 技术实现要求

### Flask API路由实现
```python
# web_gui/api_routes.py

from flask import jsonify, request
from web_gui.services.variable_manager import VariableManagerFactory
from web_gui.services.variable_suggestion_service import VariableSuggestionService

@app.route('/api/v1/executions/<execution_id>/variable-suggestions', methods=['GET'])
def get_variable_suggestions(execution_id):
    """获取变量建议列表"""
    try:
        step_index = request.args.get('step_index', type=int)
        include_properties = request.args.get('include_properties', 'true').lower() == 'true'
        
        # 获取变量管理器
        manager = VariableManagerFactory.get_manager(execution_id)
        suggestion_service = VariableSuggestionService(manager)
        
        # 获取建议数据
        suggestions = suggestion_service.get_variable_suggestions(
            step_index=step_index,
            include_properties=include_properties
        )
        
        return jsonify({
            'execution_id': execution_id,
            'current_step_index': step_index,
            'variables': suggestions,
            'total_count': len(suggestions)
        }), 200
        
    except Exception as e:
        logger.error(f"获取变量建议失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/executions/<execution_id>/variables/<variable_name>/properties', methods=['GET'])
def get_variable_properties(execution_id, variable_name):
    """获取变量属性列表"""
    try:
        max_depth = request.args.get('max_depth', 3, type=int)
        
        manager = VariableManagerFactory.get_manager(execution_id)
        suggestion_service = VariableSuggestionService(manager)
        
        properties = suggestion_service.get_variable_properties(
            variable_name=variable_name,
            max_depth=max_depth
        )
        
        if properties is None:
            return jsonify({'error': f'变量 {variable_name} 不存在'}), 404
        
        return jsonify(properties), 200
        
    except Exception as e:
        logger.error(f"获取变量属性失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/executions/<execution_id>/variable-suggestions/search', methods=['GET'])
def search_variables(execution_id):
    """模糊搜索变量"""
    try:
        query = request.args.get('q', '').strip()
        limit = request.args.get('limit', 10, type=int)
        step_index = request.args.get('step_index', type=int)
        
        if not query:
            return jsonify({'error': '搜索查询不能为空'}), 400
        
        manager = VariableManagerFactory.get_manager(execution_id)
        suggestion_service = VariableSuggestionService(manager)
        
        matches = suggestion_service.search_variables(
            query=query,
            limit=limit,
            step_index=step_index
        )
        
        return jsonify({
            'query': query,
            'matches': matches,
            'count': len(matches)
        }), 200
        
    except Exception as e:
        logger.error(f"变量搜索失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/executions/<execution_id>/variables/validate', methods=['POST'])
def validate_variable_references(execution_id):
    """验证变量引用"""
    try:
        data = request.get_json()
        if not data or 'references' not in data:
            return jsonify({'error': '请提供要验证的变量引用'}), 400
        
        references = data['references']
        step_index = data.get('step_index')
        
        manager = VariableManagerFactory.get_manager(execution_id)
        suggestion_service = VariableSuggestionService(manager)
        
        validation_results = suggestion_service.validate_references(
            references=references,
            step_index=step_index
        )
        
        return jsonify({
            'validation_results': validation_results
        }), 200
        
    except Exception as e:
        logger.error(f"变量引用验证失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/executions/<execution_id>/variables/status', methods=['GET'])
def get_variables_status(execution_id):
    """获取变量状态"""
    try:
        manager = VariableManagerFactory.get_manager(execution_id)
        suggestion_service = VariableSuggestionService(manager)
        
        status = suggestion_service.get_variables_status()
        
        return jsonify({
            'execution_id': execution_id,
            **status
        }), 200
        
    except Exception as e:
        logger.error(f"获取变量状态失败: {str(e)}")
        return jsonify({'error': str(e)}), 500
```

### 变量建议服务类
```python
# web_gui/services/variable_suggestion_service.py

import re
import json
from typing import List, Dict, Any, Optional
from difflib import SequenceMatcher
from collections import defaultdict

class VariableSuggestionService:
    """变量建议服务"""
    
    def __init__(self, variable_manager):
        self.variable_manager = variable_manager
        
    def get_variable_suggestions(self, step_index: int = None, include_properties: bool = True) -> List[Dict]:
        """获取变量建议列表"""
        variables = self.variable_manager.list_variables()
        
        suggestions = []
        for var in variables:
            # 只显示当前步骤之前的变量
            if step_index is not None and var['source_step_index'] >= step_index:
                continue
            
            suggestion = {
                'name': var['variable_name'],
                'data_type': var['data_type'],
                'source_step_index': var['source_step_index'],
                'source_api_method': var['source_api_method'],
                'created_at': var['created_at'],
                'preview_value': self._format_preview_value(var['variable_value'], var['data_type'])
            }
            
            # 如果需要包含属性信息
            if include_properties and var['data_type'] in ['object', 'array']:
                suggestion['properties'] = self._extract_properties(
                    var['variable_value'], 
                    var['variable_name']
                )
            
            suggestions.append(suggestion)
        
        return suggestions
    
    def get_variable_properties(self, variable_name: str, max_depth: int = 3) -> Optional[Dict]:
        """获取变量属性详情"""
        var_data = self.variable_manager.get_variable_metadata(variable_name)
        if not var_data:
            return None
        
        if var_data['data_type'] not in ['object', 'array']:
            return {
                'variable_name': variable_name,
                'data_type': var_data['data_type'],
                'properties': []
            }
        
        properties = self._extract_properties_deep(
            var_data['value'], 
            variable_name, 
            max_depth=max_depth
        )
        
        return {
            'variable_name': variable_name,
            'data_type': var_data['data_type'],
            'properties': properties
        }
    
    def search_variables(self, query: str, limit: int = 10, step_index: int = None) -> List[Dict]:
        """模糊搜索变量"""
        variables = self.variable_manager.list_variables()
        
        # 过滤步骤索引
        if step_index is not None:
            variables = [v for v in variables if v['source_step_index'] < step_index]
        
        matches = []
        for var in variables:
            var_name = var['variable_name']
            
            # 计算匹配分数
            score = SequenceMatcher(None, query.lower(), var_name.lower()).ratio()
            
            # 子字符串匹配加分
            if query.lower() in var_name.lower():
                score += 0.3
            
            # 前缀匹配加分
            if var_name.lower().startswith(query.lower()):
                score += 0.2
            
            if score > 0.3:  # 最低匹配阈值
                matches.append({
                    'name': var_name,
                    'match_score': score,
                    'highlighted_name': self._highlight_match(var_name, query),
                    'data_type': var['data_type'],
                    'source_step_index': var['source_step_index'],
                    'preview_value': self._format_preview_value(var['variable_value'], var['data_type'])
                })
        
        # 按匹配分数排序
        matches.sort(key=lambda x: x['match_score'], reverse=True)
        
        return matches[:limit]
    
    def validate_references(self, references: List[str], step_index: int = None) -> List[Dict]:
        """验证变量引用"""
        results = []
        
        for ref in references:
            try:
                # 解析变量引用
                var_path = self._parse_variable_reference(ref)
                if not var_path:
                    results.append({
                        'reference': ref,
                        'is_valid': False,
                        'error': '无效的变量引用格式',
                        'suggestion': '使用 ${variable_name} 或 ${variable.property} 格式'
                    })
                    continue
                
                # 验证变量是否存在
                var_name = var_path.split('.')[0]
                var_value = self.variable_manager.get_variable(var_name)
                
                if var_value is None:
                    # 提供变量建议
                    available_vars = [v['variable_name'] for v in self.variable_manager.list_variables()]
                    results.append({
                        'reference': ref,
                        'is_valid': False,
                        'error': f"变量 '{var_name}' 未定义",
                        'suggestion': f"可用变量: {', '.join(available_vars[:5])}"
                    })
                    continue
                
                # 验证属性路径
                try:
                    resolved_value = self._resolve_property_path(var_value, var_path)
                    results.append({
                        'reference': ref,
                        'is_valid': True,
                        'resolved_value': resolved_value,
                        'data_type': type(resolved_value).__name__
                    })
                except Exception as e:
                    results.append({
                        'reference': ref,
                        'is_valid': False,
                        'error': str(e),
                        'suggestion': self._get_property_suggestions(var_value, var_path)
                    })
                    
            except Exception as e:
                results.append({
                    'reference': ref,
                    'is_valid': False,
                    'error': f'验证失败: {str(e)}'
                })
        
        return results
    
    def get_variables_status(self) -> Dict:
        """获取变量状态概览"""
        variables = self.variable_manager.list_variables()
        
        # 统计变量使用情况
        usage_stats = self._calculate_usage_statistics()
        
        return {
            'variables_count': len(variables),
            'variables': [
                {
                    'name': var['variable_name'],
                    'status': 'available',
                    'last_updated': var['created_at'],
                    'usage_count': usage_stats.get(var['variable_name'], 0)
                }
                for var in variables
            ],
            'recent_references': self._get_recent_references()
        }
    
    def _format_preview_value(self, value: Any, data_type: str) -> str:
        """格式化预览值"""
        if data_type == 'string':
            return f'"{str(value)[:50]}{"..." if len(str(value)) > 50 else ""}"'
        elif data_type in ['object', 'array']:
            return json.dumps(value, ensure_ascii=False)[:100] + "..."
        else:
            return str(value)
    
    def _extract_properties(self, value: Any, parent_name: str) -> List[Dict]:
        """提取对象属性（浅层）"""
        if not isinstance(value, dict):
            return []
        
        properties = []
        for key, val in value.items():
            properties.append({
                'name': key,
                'type': type(val).__name__,
                'value': val,
                'path': f"{parent_name}.{key}"
            })
        
        return properties
    
    def _highlight_match(self, text: str, query: str) -> str:
        """高亮匹配的文本"""
        pattern = re.compile(re.escape(query), re.IGNORECASE)
        return pattern.sub(f'<mark>{query}</mark>', text)
    
    def _parse_variable_reference(self, reference: str) -> Optional[str]:
        """解析变量引用，提取变量路径"""
        pattern = r'^\$\{([^}]+)\}$'
        match = re.match(pattern, reference)
        return match.group(1) if match else None
    
    def _resolve_property_path(self, obj: Any, path: str) -> Any:
        """解析属性路径"""
        parts = path.split('.')
        current = obj
        
        for part in parts[1:]:  # 跳过变量名本身
            if isinstance(current, dict) and part in current:
                current = current[part]
            elif isinstance(current, list):
                try:
                    index = int(part)
                    current = current[index]
                except (ValueError, IndexError):
                    raise ValueError(f"无效的数组索引: {part}")
            else:
                raise ValueError(f"属性 '{part}' 不存在")
        
        return current
```

---

## 🧪 测试计划

### API端点测试
1. **变量建议API测试**
   ```python
   def test_variable_suggestions_api():
       response = client.get('/api/v1/executions/test-exec/variable-suggestions?step_index=5')
       
       assert response.status_code == 200
       data = response.get_json()
       assert 'variables' in data
       assert 'total_count' in data
   ```

2. **属性探索API测试**
3. **模糊搜索API测试**
4. **变量验证API测试**

### 性能测试
1. **响应时间测试**
2. **并发请求测试**
3. **大量变量处理测试**

### 缓存测试
1. **Redis缓存集成测试**
2. **缓存失效测试**
3. **缓存命中率测试**

---

## 📊 Definition of Done

- [ ] **API完整性**: 所有5个核心API端点实现完成
- [ ] **性能达标**: 所有API响应时间符合要求
- [ ] **错误处理**: 完善的异常处理和错误信息
- [ ] **数据格式**: API返回格式标准化且完整
- [ ] **单元测试**: API测试覆盖率>90%
- [ ] **集成测试**: 与前端组件集成测试通过
- [ ] **文档**: API文档和使用示例完整

---

## 🔗 依赖关系

**前置依赖**:
- STORY-003: VariableResolverService基础架构已完成
- STORY-007: output_variable参数解析已完成
- Flask API框架已设置

**后续依赖**:
- STORY-010: SmartVariableInput智能提示组件（前端消费这些API）
- STORY-012: 集成智能提示到测试用例编辑器

---

## 💡 实现注意事项

### 性能优化
- 使用Redis缓存频繁访问的变量数据
- 实现增量数据加载避免大量数据传输
- 合理的分页和限制策略

### 安全考虑
- 输入验证防止注入攻击
- 访问权限控制确保数据安全
- 敏感变量数据的处理

### 可扩展性
- API版本化支持未来扩展
- 插件化的变量类型处理
- 支持自定义搜索和过滤逻辑

---

**状态**: 待开始  
**创建人**: John (Product Manager)  
**最后更新**: 2025-01-30  

*此Story为前端智能提示功能提供强大的后端API支持*