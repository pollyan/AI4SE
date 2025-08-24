# STORY-009: 集成变量解析到步骤执行流程

**Story ID**: STORY-009  
**Epic**: EPIC-001 数据流核心功能  
**Sprint**: Sprint 2  
**优先级**: High  
**估算**: 8 Story Points  
**分配给**: 全栈工程师 + Backend Developer  
**创建日期**: 2025-01-30  
**产品经理**: John  

---

## 📖 故事描述

**作为** 系统架构师  
**我希望** 将变量解析功能完全集成到现有的测试步骤执行流程中  
**以便** 用户在运行测试时能够自动享受变量引用和数据流传递的功能  
**这样** 整个数据流功能就能无缝工作，为用户提供完整的端到端体验  

---

## 🎯 验收标准

### AC-1: 步骤执行前的参数预处理
**给定** 测试步骤包含变量引用语法  
**当** 系统准备执行该步骤时  
**那么** 应该自动解析所有变量引用并替换为实际值  

**预处理要求**:
- 在步骤执行前自动调用变量解析
- 支持所有参数字段的变量引用
- 保留原始配置用于调试和日志
- 解析失败时提供明确的错误信息

**示例**:
```json
// 原始步骤配置
{
  "action": "ai_input",
  "params": {
    "text": "搜索${product_name}，价格${product_info.price}元",
    "locate": "搜索框"
  }
}

// 解析后的执行配置
{
  "action": "ai_input",
  "params": {
    "text": "搜索iPhone 15，价格999元",
    "locate": "搜索框"
  }
}
```

### AC-2: 深度递归参数解析
**给定** 步骤参数包含嵌套对象和数组  
**当** 系统解析变量引用时  
**那么** 应该递归处理所有层级的参数  

**深度解析支持**:
- 嵌套对象中的变量引用
- 数组元素中的变量引用
- 复杂JSON结构的完整解析
- 支持任意深度的嵌套结构

### AC-3: 变量引用关系记录
**给定** 步骤使用了变量引用  
**当** 系统解析变量时  
**那么** 应该记录完整的引用关系到数据库  

**记录内容**:
- 使用变量的步骤索引
- 引用的变量名和路径
- 参数名称
- 原始表达式和解析结果
- 解析状态和错误信息

### AC-4: 执行流程无缝集成
**给定** 现有的测试执行流程正常工作  
**当** 集成变量解析功能时  
**那么** 不应该影响现有功能的正常运行  

**集成要求**:
- 100%向后兼容现有测试用例
- 不影响执行性能（延迟<10%）
- 保持现有错误处理机制
- 维持现有的日志和监控

### AC-5: 实时变量状态显示
**给定** 测试正在执行并使用变量  
**当** 用户查看执行状态时  
**那么** 应该能够看到当前的变量值和使用情况  

**显示功能**:
- 执行监控页面显示当前变量列表
- 步骤执行详情显示变量解析过程
- 变量值的实时更新
- 错误步骤的变量解析失败信息

---

## 🔧 技术实现要求

### 核心集成组件
```python
# web_gui/services/execution_engine.py

class EnhancedExecutionEngine:
    """
    增强的执行引擎 - 集成变量解析功能
    """
    
    def __init__(self):
        self.variable_manager = None
        self.variable_resolver = None
        self.original_executor = None
    
    async def execute_test_case(self, test_case_id: int, execution_config: dict) -> dict:
        """执行测试用例（集成变量解析）"""
        execution_id = self._generate_execution_id()
        
        try:
            # 初始化变量管理器
            self.variable_manager = VariableManagerFactory.get_manager(execution_id)
            self.variable_resolver = VariableResolver(self.variable_manager)
            
            # 获取测试用例
            test_case = TestCase.query.get(test_case_id)
            if not test_case:
                raise ValueError(f"测试用例不存在: {test_case_id}")
            
            steps = json.loads(test_case.steps)
            
            # 创建执行历史记录
            execution_history = self._create_execution_history(
                execution_id, test_case_id, execution_config
            )
            
            # 执行步骤
            execution_results = []
            for step_index, step_config in enumerate(steps):
                step_result = await self._execute_step_with_variables(
                    step_config, step_index, execution_id
                )
                execution_results.append(step_result)
                
                # 如果步骤失败且配置为失败停止，则中断执行
                if step_result['status'] == 'failed' and execution_config.get('stop_on_failure'):
                    break
            
            # 更新执行历史
            self._update_execution_history(execution_history, execution_results)
            
            return {
                'execution_id': execution_id,
                'status': 'completed',
                'results': execution_results,
                'variables': self.variable_manager.list_variables()
            }
            
        except Exception as e:
            logger.error(f"测试执行失败: {str(e)}")
            return {
                'execution_id': execution_id,
                'status': 'failed',
                'error': str(e)
            }
        finally:
            # 清理资源（可选，取决于是否需要保留变量用于调试）
            if execution_config.get('cleanup_on_complete', False):
                VariableManagerFactory.cleanup_manager(execution_id)
    
    async def _execute_step_with_variables(self, step_config: dict, step_index: int, execution_id: str) -> dict:
        """执行单个步骤（集成变量解析）"""
        try:
            # 1. 保存原始配置用于调试
            original_config = copy.deepcopy(step_config)
            
            # 2. 预处理：解析变量引用
            resolved_config = self._resolve_step_variables(
                step_config, step_index, execution_id
            )
            
            # 3. 执行步骤
            step_result = await self._execute_resolved_step(
                resolved_config, step_index, execution_id
            )
            
            # 4. 后处理：捕获返回值（如果配置了output_variable）
            if resolved_config.get('output_variable') and step_result.get('result'):
                self._capture_step_output(
                    resolved_config, step_result, step_index
                )
            
            # 5. 记录步骤执行详情
            self._record_step_execution(
                execution_id, step_index, original_config, resolved_config, step_result
            )
            
            return step_result
            
        except Exception as e:
            logger.error(f"步骤执行失败 [步骤 {step_index}]: {str(e)}")
            return {
                'status': 'failed',
                'step_index': step_index,
                'error': str(e),
                'original_config': step_config
            }
    
    def _resolve_step_variables(self, step_config: dict, step_index: int, execution_id: str) -> dict:
        """解析步骤中的所有变量引用"""
        resolved_config = copy.deepcopy(step_config)
        
        # 递归解析参数中的变量引用
        if 'params' in resolved_config:
            resolved_config['params'] = self._resolve_object_variables(
                resolved_config['params'], step_index
            )
        
        # 解析其他可能包含变量的字段
        for field in ['description', 'expected_result']:
            if field in resolved_config:
                resolved_config[field] = self.variable_resolver.resolve_variable_references(
                    resolved_config[field], step_index
                )
        
        return resolved_config
    
    def _resolve_object_variables(self, obj: Any, step_index: int) -> Any:
        """递归解析对象中的变量引用"""
        if isinstance(obj, str):
            return self.variable_resolver.resolve_variable_references(obj, step_index)
        elif isinstance(obj, dict):
            return {
                key: self._resolve_object_variables(value, step_index)
                for key, value in obj.items()
            }
        elif isinstance(obj, list):
            return [
                self._resolve_object_variables(item, step_index)
                for item in obj
            ]
        else:
            return obj
    
    async def _execute_resolved_step(self, resolved_config: dict, step_index: int, execution_id: str) -> dict:
        """执行已解析变量的步骤"""
        action = resolved_config.get('action')
        
        # 路由到对应的执行器
        if action in ['aiQuery', 'aiString', 'aiNumber', 'aiBoolean', 'aiAsk', 'aiLocate']:
            return await self._execute_ai_action(resolved_config, step_index)
        elif action in ['navigate', 'ai_tap', 'ai_input', 'ai_assert']:
            return await self._execute_standard_action(resolved_config, step_index)
        else:
            raise ValueError(f"不支持的动作类型: {action}")
    
    def _capture_step_output(self, resolved_config: dict, step_result: dict, step_index: int):
        """捕获步骤输出到变量"""
        output_variable = resolved_config.get('output_variable')
        if not output_variable:
            return
        
        result_value = step_result.get('result')
        if result_value is None:
            logger.warning(f"步骤 {step_index} 没有返回值，无法捕获到变量 {output_variable}")
            return
        
        success = self.variable_manager.store_variable(
            variable_name=output_variable,
            value=result_value,
            source_step_index=step_index,
            source_api_method=resolved_config.get('action'),
            source_api_params=resolved_config.get('params')
        )
        
        if success:
            logger.info(f"成功捕获步骤 {step_index} 的输出到变量: {output_variable}")
        else:
            logger.error(f"捕获步骤输出失败: {output_variable}")
```

### API路由增强
```python
# web_gui/api_routes.py

@app.route('/api/v1/testcases/<int:test_case_id>/execute', methods=['POST'])
def execute_test_case_enhanced(test_case_id):
    """执行测试用例（增强版本）"""
    try:
        execution_config = request.get_json() or {}
        
        # 使用增强的执行引擎
        engine = EnhancedExecutionEngine()
        result = await engine.execute_test_case(test_case_id, execution_config)
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"测试执行API错误: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/executions/<execution_id>/variables', methods=['GET'])
def get_execution_variables(execution_id):
    """获取执行的变量列表"""
    try:
        manager = VariableManagerFactory.get_manager(execution_id)
        variables = manager.list_variables()
        
        return jsonify({
            'execution_id': execution_id,
            'variables': variables,
            'count': len(variables)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/executions/<execution_id>/variables/<variable_name>', methods=['GET'])
def get_variable_detail(execution_id, variable_name):
    """获取变量详细信息"""
    try:
        manager = VariableManagerFactory.get_manager(execution_id)
        metadata = manager.get_variable_metadata(variable_name)
        
        if metadata:
            return jsonify(metadata), 200
        else:
            return jsonify({'error': '变量不存在'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

### 前端集成支持
```typescript
// web_gui/static/js/execution-monitor.js

class ExecutionMonitor {
    constructor(executionId) {
        this.executionId = executionId;
        this.variables = new Map();
        this.websocket = null;
    }
    
    async startMonitoring() {
        // 建立WebSocket连接接收实时更新
        this.websocket = new WebSocket(`ws://localhost:5000/ws/execution/${this.executionId}`);
        
        this.websocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleExecutionUpdate(data);
        };
        
        // 初始加载变量数据
        await this.loadVariables();
    }
    
    async loadVariables() {
        try {
            const response = await fetch(`/api/v1/executions/${this.executionId}/variables`);
            const data = await response.json();
            
            this.updateVariableDisplay(data.variables);
        } catch (error) {
            console.error('加载变量失败:', error);
        }
    }
    
    handleExecutionUpdate(update) {
        if (update.type === 'variable_updated') {
            this.updateVariable(update.variable);
        } else if (update.type === 'step_completed') {
            this.updateStepStatus(update.step);
        }
    }
    
    updateVariableDisplay(variables) {
        const container = document.getElementById('variables-container');
        container.innerHTML = '';
        
        variables.forEach(variable => {
            const variableElement = this.createVariableElement(variable);
            container.appendChild(variableElement);
        });
    }
    
    createVariableElement(variable) {
        const element = document.createElement('div');
        element.className = 'variable-item';
        element.innerHTML = `
            <div class="variable-header">
                <span class="variable-name">${variable.variable_name}</span>
                <span class="variable-type">[${variable.data_type}]</span>
                <span class="variable-source">步骤 ${variable.source_step_index}</span>
            </div>
            <div class="variable-value">
                <pre>${JSON.stringify(variable.variable_value, null, 2)}</pre>
            </div>
        `;
        return element;
    }
}
```

---

## 🧪 测试计划

### 单元测试
1. **变量解析集成测试**
   ```python
   async def test_step_variable_resolution():
       engine = EnhancedExecutionEngine()
       
       # 准备测试数据
       execution_id = 'test-exec-001'
       manager = VariableManagerFactory.get_manager(execution_id)
       manager.store_variable('product_name', 'iPhone 15', 0)
       
       step_config = {
           "action": "ai_input",
           "params": {
               "text": "搜索${product_name}",
               "locate": "搜索框"
           }
       }
       
       # 执行步骤
       result = await engine._execute_step_with_variables(step_config, 1, execution_id)
       
       # 验证变量解析
       assert result['resolved_params']['text'] == '搜索iPhone 15'
   ```

2. **深度递归解析测试**
   ```python
   def test_deep_variable_resolution():
       complex_config = {
           "action": "aiQuery",
           "params": {
               "query": "查找${category}产品",
               "dataDemand": {
                   "items": [
                       {"name": "${product_name}", "price": "${min_price}"}
                   ]
               }
           }
       }
       
       resolved = engine._resolve_step_variables(complex_config, 1, execution_id)
       # 验证所有层级的变量都被正确解析
   ```

### 集成测试
1. **端到端执行流程测试**
   ```json
   [
     {
       "action": "navigate",
       "params": {"url": "https://test-shop.com"}
     },
     {
       "action": "aiQuery",
       "params": {
         "query": "获取商品信息",
         "dataDemand": "{name: string, price: number}"
       },
       "output_variable": "product_info"
     },
     {
       "action": "ai_input",
       "params": {
         "text": "搜索${product_info.name}",
         "locate": "搜索框"
       }
     },
     {
       "action": "ai_assert",
       "params": {
         "condition": "显示价格${product_info.price}元"
       }
     }
   ]
   ```

2. **错误处理集成测试**
3. **性能回归测试**
4. **并发执行测试**

---

## 📊 Definition of Done

- [ ] **无缝集成**: 变量解析完全集成到执行流程，不影响现有功能
- [ ] **深度解析**: 支持任意深度的嵌套参数变量解析
- [ ] **关系记录**: 变量引用关系完整记录到数据库
- [ ] **实时监控**: 执行监控界面显示变量状态和使用情况
- [ ] **向后兼容**: 100%保持现有测试用例的兼容性
- [ ] **性能要求**: 执行性能影响<10%
- [ ] **错误处理**: 完善的错误处理和用户友好提示
- [ ] **测试覆盖**: 集成测试覆盖所有主要场景

---

## 🔗 依赖关系

**前置依赖**:
- STORY-005: AI方法返回值捕获已完成
- STORY-007: output_variable参数解析已完成
- STORY-008: 变量引用语法解析已完成
- STORY-003: VariableResolverService基础架构已完成

**后续依赖**:
- STORY-010: SmartVariableInput智能提示组件
- STORY-012: 集成智能提示到测试用例编辑器

---

## 💡 实现注意事项

### 性能优化
- 变量解析结果缓存避免重复计算
- 批量处理变量引用关系记录
- 异步执行非关键路径操作

### 错误恢复
- 变量解析失败时的优雅降级
- 部分变量解析失败不影响整体执行
- 详细的错误日志便于问题排查

### 监控和调试
- 完整的执行轨迹记录
- 变量解析过程的详细日志
- 支持调试模式的详细输出

---

**状态**: 待开始  
**创建人**: John (Product Manager)  
**最后更新**: 2025-01-30  

*此Story将所有数据流组件整合为完整的用户体验，是功能交付的关键里程碑*