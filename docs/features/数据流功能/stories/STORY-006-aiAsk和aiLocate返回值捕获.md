# STORY-006: 为aiAsk和aiLocate/evaluateJavaScript添加返回值捕获

**Story ID**: STORY-006  
**Epic**: EPIC-001 数据流核心功能  
**Sprint**: Sprint 2  
**优先级**: Medium  
**估算**: 3 Story Points  
**分配给**: 全栈工程师  
**创建日期**: 2025-01-30  
**产品经理**: John  

---

## 📖 故事描述

**作为** 测试工程师  
**我希望** aiAsk、aiLocate和evaluateJavaScript这些辅助的Midscene AI方法也能够捕获返回值  
**以便** 我可以将AI问答结果、元素位置信息和JavaScript执行结果保存为变量  
**这样** 我就能创建更丰富的测试场景，充分利用所有Midscene API的数据输出能力  

---

## 🎯 验收标准

### AC-1: aiAsk方法返回值捕获
**给定** 我配置了一个aiAsk步骤并指定output_variable  
**当** 系统执行该步骤时  
**那么** aiAsk的文本回答应该被正确捕获并存储为字符串类型变量  

**配置示例**:
```json
{
  "action": "aiAsk",
  "params": {
    "query": "这个页面的主要功能是什么？"
  },
  "output_variable": "page_description",
  "description": "获取页面功能描述"
}
```

**期望结果**:
- 变量名: `page_description`
- 数据类型: `string`
- 变量值: `"这是一个电商网站的商品详情页面，用户可以查看商品信息、价格和购买选项"`

### AC-2: aiLocate方法返回值捕获
**给定** 我配置了一个aiLocate步骤并指定output_variable  
**当** 系统执行该步骤时  
**那么** aiLocate的位置信息应该被正确捕获并存储为对象类型变量  

**配置示例**:
```json
{
  "action": "aiLocate",
  "params": {
    "query": "购买按钮"
  },
  "output_variable": "buy_button_location",
  "description": "获取购买按钮位置"
}
```

**期望结果**:
- 变量名: `buy_button_location`
- 数据类型: `object`
- 变量值: 
```json
{
  "rect": {"x": 100, "y": 200, "width": 120, "height": 40},
  "center": {"x": 160, "y": 220},
  "scale": 1.0
}
```

### AC-3: evaluateJavaScript方法返回值捕获
**给定** 我配置了一个evaluateJavaScript步骤并指定output_variable  
**当** 系统执行该步骤时  
**那么** JavaScript执行结果应该被正确捕获并根据返回值类型存储  

**配置示例**:
```json
{
  "action": "evaluateJavaScript",
  "params": {
    "script": "return { title: document.title, url: window.location.href, itemCount: document.querySelectorAll('.item').length }"
  },
  "output_variable": "page_info",
  "description": "获取页面基本信息"
}
```

**期望结果**:
- 变量名: `page_info`
- 数据类型: `object`
- 变量值:
```json
{
  "title": "商品详情页",
  "url": "https://example.com/product/123", 
  "itemCount": 5
}
```

### AC-4: 复杂数据类型处理
**给定** AI方法返回复杂的数据结构  
**当** 系统捕获返回值时  
**那么** 应该正确处理和存储各种数据类型  

**数据类型支持**:
- aiAsk: 纯文本字符串
- aiLocate: 位置对象 {rect, center, scale}
- evaluateJavaScript: 任意JavaScript返回值（原始类型、对象、数组）

### AC-5: 错误场景处理
**给定** AI方法执行失败或返回异常  
**当** 系统尝试捕获返回值时  
**那么** 应该记录错误信息并优雅处理失败情况  

**错误处理要求**:
- AI询问无法回答时返回空字符串或null
- 元素定位失败时返回null
- JavaScript执行错误时记录错误信息
- 所有错误都应记录到execution log中

### AC-6: 变量引用支持
**给定** 捕获的变量数据被存储  
**当** 后续步骤引用这些变量时  
**那么** 应该能够正确访问复杂对象的属性  

**引用示例**:
```json
{
  "action": "ai_assert",
  "params": {
    "condition": "页面标题是${page_info.title}"
  }
},
{
  "action": "ai_tap",
  "params": {
    "locate": "在坐标${buy_button_location.center.x},${buy_button_location.center.y}点击"
  }
}
```

---

## 🔧 技术实现要求

### MidSceneJS集成扩展
```python
# enhanced_step_executor.py 扩展

class EnhancedStepExecutor:
    # ... 现有代码 ...
    
    async def execute_ai_ask(self, step_config: dict, step_index: int) -> dict:
        """执行aiAsk并捕获返回值"""
        try:
            # 执行原有的aiAsk逻辑
            result = await self.page.aiAsk(
                query=step_config['params']['query'],
                options=step_config['params'].get('options', {})
            )
            
            # 处理返回值（确保是字符串）
            processed_result = str(result) if result is not None else ""
            
            # 如果配置了输出变量，则存储结果
            if step_config.get('output_variable'):
                success = self.variable_manager.store_variable(
                    variable_name=step_config['output_variable'],
                    value=processed_result,
                    source_step_index=step_index,
                    source_api_method='aiAsk',
                    source_api_params=step_config['params']
                )
                
                if not success:
                    logger.warning(f"aiAsk变量存储失败: {step_config['output_variable']}")
            
            return {
                'status': 'success',
                'result': processed_result,
                'variable_stored': step_config.get('output_variable') is not None,
                'step_type': 'aiAsk'
            }
            
        except Exception as e:
            logger.error(f"aiAsk执行失败: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e),
                'variable_stored': False,
                'step_type': 'aiAsk'
            }
    
    async def execute_ai_locate(self, step_config: dict, step_index: int) -> dict:
        """执行aiLocate并捕获返回值"""
        try:
            # 执行原有的aiLocate逻辑
            result = await self.page.aiLocate(
                query=step_config['params']['query'],
                options=step_config['params'].get('options', {})
            )
            
            # 处理位置信息返回值
            location_data = None
            if result:
                location_data = {
                    'rect': {
                        'x': result.rect.x,
                        'y': result.rect.y, 
                        'width': result.rect.width,
                        'height': result.rect.height
                    },
                    'center': {
                        'x': result.center.x,
                        'y': result.center.y
                    },
                    'scale': getattr(result, 'scale', 1.0)
                }
            
            # 如果配置了输出变量，则存储结果
            if step_config.get('output_variable') and location_data:
                success = self.variable_manager.store_variable(
                    variable_name=step_config['output_variable'],
                    value=location_data,
                    source_step_index=step_index,
                    source_api_method='aiLocate',
                    source_api_params=step_config['params']
                )
                
                if not success:
                    logger.warning(f"aiLocate变量存储失败: {step_config['output_variable']}")
            
            return {
                'status': 'success',
                'result': location_data,
                'variable_stored': step_config.get('output_variable') is not None and location_data is not None,
                'step_type': 'aiLocate'
            }
            
        except Exception as e:
            logger.error(f"aiLocate执行失败: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e),
                'variable_stored': False,
                'step_type': 'aiLocate'
            }
    
    async def execute_evaluate_javascript(self, step_config: dict, step_index: int) -> dict:
        """执行evaluateJavaScript并捕获返回值"""
        try:
            # 执行JavaScript代码
            script = step_config['params']['script']
            result = await self.page.evaluate(script)
            
            # 如果配置了输出变量，则存储结果
            if step_config.get('output_variable'):
                success = self.variable_manager.store_variable(
                    variable_name=step_config['output_variable'],
                    value=result,
                    source_step_index=step_index,
                    source_api_method='evaluateJavaScript',
                    source_api_params=step_config['params']
                )
                
                if not success:
                    logger.warning(f"evaluateJavaScript变量存储失败: {step_config['output_variable']}")
            
            return {
                'status': 'success',
                'result': result,
                'variable_stored': step_config.get('output_variable') is not None,
                'step_type': 'evaluateJavaScript'
            }
            
        except Exception as e:
            logger.error(f"evaluateJavaScript执行失败: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e),
                'variable_stored': False,
                'step_type': 'evaluateJavaScript'
            }
    
    async def execute_step(self, step_config: dict, step_index: int) -> dict:
        """扩展步骤执行路由"""
        action = step_config.get('action')
        
        # 路由到对应的执行器
        if action == 'aiQuery':
            return await self.execute_ai_query(step_config, step_index)
        elif action == 'aiString':
            return await self.execute_ai_string(step_config, step_index)
        elif action == 'aiNumber':
            return await self.execute_ai_number(step_config, step_index)
        elif action == 'aiBoolean':
            return await self.execute_ai_boolean(step_config, step_index)
        elif action == 'aiAsk':
            return await self.execute_ai_ask(step_config, step_index)
        elif action == 'aiLocate':
            return await self.execute_ai_locate(step_config, step_index)
        elif action == 'evaluateJavaScript':
            return await self.execute_evaluate_javascript(step_config, step_index)
        else:
            # 执行其他类型的步骤
            return await self.execute_legacy_step(step_config, step_index)
```

### 数据验证扩展
```python
# DataValidator类扩展
class DataValidator:
    # ... 现有方法 ...
    
    @staticmethod
    def validate_ai_ask_result(result: any) -> bool:
        """验证aiAsk结果"""
        return isinstance(result, str)
    
    @staticmethod
    def validate_ai_locate_result(result: any) -> bool:
        """验证aiLocate结果"""
        if not isinstance(result, dict):
            return False
        
        required_fields = ['rect', 'center']
        for field in required_fields:
            if field not in result:
                return False
        
        # 验证rect结构
        if not isinstance(result['rect'], dict):
            return False
        rect_fields = ['x', 'y', 'width', 'height']
        for field in rect_fields:
            if field not in result['rect'] or not isinstance(result['rect'][field], (int, float)):
                return False
        
        # 验证center结构
        if not isinstance(result['center'], dict):
            return False
        center_fields = ['x', 'y']
        for field in center_fields:
            if field not in result['center'] or not isinstance(result['center'][field], (int, float)):
                return False
        
        return True
    
    @staticmethod
    def validate_evaluate_javascript_result(result: any) -> bool:
        """验证evaluateJavaScript结果"""
        # JavaScript可以返回任何类型，包括null/undefined
        # 主要验证是否是可序列化的类型
        try:
            json.dumps(result)
            return True
        except (TypeError, ValueError):
            return False
```

---

## 🧪 测试计划

### 单元测试
1. **aiAsk返回值捕获测试**
   ```python
   async def test_ai_ask_capture():
       step_config = {
           "action": "aiAsk",
           "params": {"query": "测试问题"},
           "output_variable": "ai_answer"
       }
       
       # Mock aiAsk返回值
       with patch('midscene_python.aiAsk', return_value="测试回答"):
           result = await executor.execute_ai_ask(step_config, 1)
           
           assert result['status'] == 'success'
           assert result['variable_stored'] == True
           
           # 验证变量存储
           stored_var = variable_manager.get_variable('ai_answer')
           assert stored_var == "测试回答"
   ```

2. **aiLocate返回值捕获测试**
   ```python
   async def test_ai_locate_capture():
       # Mock位置信息对象
       mock_location = MockLocation(
           rect=MockRect(100, 200, 120, 40),
           center=MockPoint(160, 220)
       )
       
       with patch('midscene_python.aiLocate', return_value=mock_location):
           result = await executor.execute_ai_locate(step_config, 1)
           
           stored_var = variable_manager.get_variable('element_location')
           assert stored_var['center']['x'] == 160
           assert stored_var['rect']['width'] == 120
   ```

3. **evaluateJavaScript返回值捕获测试**
   ```python
   async def test_evaluate_javascript_capture():
       test_cases = [
           ("return 42", 42, 'number'),
           ("return 'hello'", 'hello', 'string'),
           ("return {a: 1, b: 2}", {'a': 1, 'b': 2}, 'object'),
           ("return [1, 2, 3]", [1, 2, 3], 'array'),
           ("return true", True, 'boolean')
       ]
       
       for script, expected_value, expected_type in test_cases:
           step_config = {
               "action": "evaluateJavaScript", 
               "params": {"script": script},
               "output_variable": f"js_result_{expected_type}"
           }
           
           with patch('page.evaluate', return_value=expected_value):
               result = await executor.execute_evaluate_javascript(step_config, 1)
               
               stored_var = variable_manager.get_variable(f"js_result_{expected_type}")
               assert stored_var == expected_value
   ```

### 集成测试
1. **复杂数据流测试**
   ```json
   [
     {
       "action": "aiLocate",
       "params": {"query": "搜索按钮"},
       "output_variable": "search_btn_pos"
     },
     {
       "action": "aiAsk", 
       "params": {"query": "这个按钮的作用是什么？"},
       "output_variable": "button_purpose"
     },
     {
       "action": "evaluateJavaScript",
       "params": {"script": "return {x: ${search_btn_pos.center.x}, y: ${search_btn_pos.center.y}}"},
       "output_variable": "click_coords"
     }
   ]
   ```

2. **变量引用链测试**
3. **错误处理集成测试**

---

## 📊 Definition of Done

- [ ] **功能完整**: aiAsk、aiLocate、evaluateJavaScript都支持返回值捕获
- [ ] **数据类型**: 正确处理各种返回值类型
- [ ] **变量引用**: 捕获的变量可以在后续步骤中正确引用
- [ ] **错误处理**: 完善的异常处理和错误记录
- [ ] **单元测试**: 测试覆盖率>90%
- [ ] **集成测试**: 复杂数据流测试场景通过
- [ ] **向后兼容**: 不影响现有功能
- [ ] **文档更新**: API使用示例和说明更新

---

## 🔗 依赖关系

**前置依赖**:
- STORY-005: 主要AI方法返回值捕获已完成
- STORY-007: output_variable参数解析已完成
- STORY-003: VariableResolverService基础架构已完成

**后续依赖**:
- STORY-008: 变量引用语法解析（需要支持复杂对象属性访问）
- STORY-009: 集成变量解析到步骤执行流程

---

## 💡 实现注意事项

### 数据处理
- aiLocate返回的位置对象需要标准化格式
- JavaScript返回值可能包含不可序列化的对象
- aiAsk返回值可能为空或包含特殊字符

### 性能考虑
- 复杂JavaScript执行可能耗时较长
- 位置信息对象相对较小，存储开销不大
- AI问答结果通常是文本，存储高效

### 错误恢复
- AI方法失败时的优雅降级
- JavaScript执行错误时的安全处理
- 元素定位失败时的清晰提示

---

**状态**: 待开始  
**创建人**: John (Product Manager)  
**最后更新**: 2025-01-30  

*此Story扩展了数据流功能的覆盖范围，支持更多样化的测试场景*