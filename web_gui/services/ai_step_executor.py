#!/usr/bin/env python3
"""
AI步骤执行器 - 支持AI方法返回值捕获和变量管理
集成了VariableSuggestionService和MidSceneJS数据提取API框架
"""

import time
import asyncio
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from .variable_resolver_service import VariableManager, get_variable_manager
from ..models import db, ExecutionHistory, StepExecution
from midscene_framework import (
    MidSceneDataExtractor,
    DataExtractionMethod,
    ExtractionRequest,
    ExtractionResult
)

logger = logging.getLogger(__name__)


@dataclass 
class StepExecutionResult:
    """步骤执行结果"""
    success: bool
    step_index: int
    action: str
    description: str
    return_value: Any = None
    variable_assigned: Optional[str] = None
    execution_time: float = 0.0
    error_message: Optional[str] = None
    validation_warning: Optional[str] = None
    screenshot_path: Optional[str] = None
    metadata: Optional[Dict] = None


class AIStepExecutor:
    """AI步骤执行器 - 支持返回值捕获和变量管理"""
    
    def __init__(self, midscene_client=None, mock_mode: bool = False):
        """
        初始化执行器
        
        Args:
            midscene_client: MidSceneJS客户端实例
            mock_mode: 是否使用Mock模式
        """
        self.midscene_client = midscene_client
        self.mock_mode = mock_mode
        self.data_extractor = MidSceneDataExtractor(
            midscene_client=midscene_client, 
            mock_mode=mock_mode
        )
        self.logger = logger
        
        # 支持的AI数据提取方法
        self.ai_extraction_methods = {
            'aiQuery': DataExtractionMethod.AI_QUERY,
            'aiString': DataExtractionMethod.AI_STRING,
            'aiNumber': DataExtractionMethod.AI_NUMBER,
            'aiBoolean': DataExtractionMethod.AI_BOOLEAN,
            'aiAsk': DataExtractionMethod.AI_ASK,
            'aiLocate': DataExtractionMethod.AI_LOCATE
        }
        
        logger.info(f"初始化AI步骤执行器: mock_mode={mock_mode}")
    
    async def execute_step(
        self, 
        step_config: Dict[str, Any], 
        step_index: int,
        execution_id: str,
        variable_manager: VariableManager
    ) -> StepExecutionResult:
        """
        执行单个步骤
        
        Args:
            step_config: 步骤配置
            step_index: 步骤索引
            execution_id: 执行ID
            variable_manager: 变量管理器
            
        Returns:
            步骤执行结果
        """
        start_time = time.time()
        action = step_config.get('action', '')
        description = step_config.get('description', action)
        
        try:
            logger.info(f"执行步骤 {step_index}: {action} - {description}")
            
            # 处理参数中的变量引用，支持深度递归解析
            params = self._process_variable_references(step_config.get('params', {}), variable_manager, step_index)
            
            # 路由到对应的执行方法
            if action in self.ai_extraction_methods:
                result = await self._execute_ai_extraction_step(
                    action, params, step_config, step_index, variable_manager
                )
            else:
                result = await self._execute_legacy_step(
                    action, params, step_config, step_index, variable_manager
                )
            
            # 设置执行时间
            result.execution_time = time.time() - start_time
            
            # 记录步骤执行到数据库
            await self._record_step_execution(result, execution_id, step_config)
            
            logger.info(f"步骤 {step_index} 执行完成: success={result.success}")
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = str(e)
            
            logger.error(f"步骤 {step_index} 执行失败: {error_msg}")
            
            result = StepExecutionResult(
                success=False,
                step_index=step_index,
                action=action,
                description=description,
                execution_time=execution_time,
                error_message=error_msg
            )
            
            # 记录失败的步骤执行
            await self._record_step_execution(result, execution_id, step_config)
            
            return result
    
    async def _execute_ai_extraction_step(
        self,
        action: str,
        params: Dict[str, Any],
        step_config: Dict[str, Any],
        step_index: int,
        variable_manager: VariableManager
    ) -> StepExecutionResult:
        """执行AI数据提取步骤"""
        
        try:
            # 获取数据提取方法
            extraction_method = self.ai_extraction_methods[action]
            
            # 创建提取请求
            extraction_request = ExtractionRequest(
                method=extraction_method,
                params=params,
                output_variable=step_config.get('output_variable'),
                validation_rules=step_config.get('validation_rules')
            )
            
            # 执行数据提取
            extraction_result = await self.data_extractor.extract_data(extraction_request)
            
            # 处理提取结果
            step_result = StepExecutionResult(
                success=extraction_result.success,
                step_index=step_index,
                action=action,
                description=step_config.get('description', action),
                return_value=extraction_result.data,
                metadata={
                    'extraction_method': extraction_method.value,
                    'data_type': extraction_result.data_type,
                    'extraction_time': extraction_result.execution_time,
                    'extraction_metadata': extraction_result.metadata
                }
            )
            
            # 如果提取失败，设置错误信息
            if not extraction_result.success:
                step_result.error_message = extraction_result.error
                return step_result
            
            # 如果配置了输出变量，存储到变量管理器
            output_variable = step_config.get('output_variable')
            if output_variable and extraction_result.success:
                success = variable_manager.store_variable(
                    variable_name=output_variable,
                    value=extraction_result.data,
                    source_step_index=step_index,
                    source_api_method=action,
                    source_api_params=params
                )
                
                if success:
                    step_result.variable_assigned = output_variable
                    logger.info(f"变量存储成功: {output_variable} = {extraction_result.data}")
                else:
                    step_result.validation_warning = f"变量存储失败: {output_variable}"
                    logger.warning(f"变量存储失败: {output_variable}")
            
            return step_result
            
        except Exception as e:
            return StepExecutionResult(
                success=False,
                step_index=step_index,
                action=action,
                description=step_config.get('description', action),
                error_message=f"AI提取执行失败: {str(e)}"
            )
    
    async def _execute_legacy_step(
        self,
        action: str,
        params: Dict[str, Any],
        step_config: Dict[str, Any],
        step_index: int,
        variable_manager: VariableManager
    ) -> StepExecutionResult:
        """执行传统步骤（非AI数据提取）"""
        
        try:
            return_value = None
            
            # 变量操作不需要MidScene客户端
            if action == 'set_variable':
                # 直接设置变量
                var_name = params.get('name')
                var_value = params.get('value')
                if not var_name:
                    raise ValueError("set_variable操作缺少name参数")
                
                success = variable_manager.store_variable(
                    variable_name=var_name,
                    value=var_value,
                    source_step_index=step_index,
                    source_api_method='set_variable'
                )
                
                return StepExecutionResult(
                    success=success,
                    step_index=step_index,
                    action=action,
                    description=step_config.get('description', action),
                    variable_assigned=var_name if success else None,
                    return_value=var_value
                )
                
            elif action == 'get_variable':
                # 获取变量值
                var_name = params.get('name')
                if not var_name:
                    raise ValueError("get_variable操作缺少name参数")
                
                var_value = variable_manager.get_variable(var_name)
                return StepExecutionResult(
                    success=var_value is not None,
                    step_index=step_index,
                    action=action,
                    description=step_config.get('description', action),
                    return_value=var_value,
                    error_message=f"变量不存在: {var_name}" if var_value is None else None
                )
        
            # 其他操作需要MidScene客户端（除了evaluateJavaScript在Mock模式下）
            if not self.midscene_client and not (action == 'evaluateJavaScript' and self.mock_mode):
                return StepExecutionResult(
                    success=False,
                    step_index=step_index,
                    action=action,
                    description=step_config.get('description', action),
                    error_message="MidScene客户端未初始化"
                )
            
            # 执行需要MidScene客户端的传统步骤
            if action == 'navigate' or action == 'goto':
                url = params.get('url')
                if not url:
                    raise ValueError("navigate操作缺少url参数")
                return_value = await asyncio.to_thread(self.midscene_client.goto, url)
                
            elif action == 'ai_input':
                text = params.get('text')
                locate = params.get('locate')
                if not text or not locate:
                    raise ValueError("ai_input操作缺少text或locate参数")
                return_value = await asyncio.to_thread(self.midscene_client.ai_input, text, locate)
                
            elif action == 'ai_tap':
                prompt = params.get('prompt')
                if not prompt:
                    raise ValueError("ai_tap操作缺少prompt参数")
                return_value = await asyncio.to_thread(self.midscene_client.ai_tap, prompt)
                
            elif action == 'ai_assert':
                prompt = params.get('prompt')
                if not prompt:
                    raise ValueError("ai_assert操作缺少prompt参数")
                return_value = await asyncio.to_thread(self.midscene_client.ai_assert, prompt)
                
            elif action == 'evaluateJavaScript':
                script = params.get('script')
                if not script:
                    raise ValueError("evaluateJavaScript操作缺少script参数")
                
                # 执行JavaScript代码
                if self.mock_mode:
                    # Mock模式：返回模拟结果
                    return_value = await self._mock_evaluate_javascript(script)
                else:
                    # 真实模式：使用MidScene客户端执行
                    if hasattr(self.midscene_client, 'evaluate'):
                        return_value = await asyncio.to_thread(self.midscene_client.evaluate, script)
                    elif hasattr(self.midscene_client, 'page') and hasattr(self.midscene_client.page, 'evaluate'):
                        return_value = await asyncio.to_thread(self.midscene_client.page.evaluate, script)
                    else:
                        raise ValueError("MidScene客户端不支持JavaScript执行")
                
                # 验证返回值是否可序列化
                from midscene_framework.validators import DataValidator
                try:
                    return_value = DataValidator.validate_evaluate_javascript_result(return_value)
                except ValueError as e:
                    raise ValueError(f"JavaScript执行结果验证失败: {str(e)}")
                
            elif action == 'set_variable':
                # 直接设置变量
                var_name = params.get('name')
                var_value = params.get('value')
                if not var_name:
                    raise ValueError("set_variable操作缺少name参数")
                
                success = variable_manager.store_variable(
                    variable_name=var_name,
                    value=var_value,
                    source_step_index=step_index,
                    source_api_method='set_variable'
                )
                
                return StepExecutionResult(
                    success=success,
                    step_index=step_index,
                    action=action,
                    description=step_config.get('description', action),
                    variable_assigned=var_name if success else None,
                    return_value=var_value
                )
                
            elif action == 'get_variable':
                # 获取变量值
                var_name = params.get('name')
                if not var_name:
                    raise ValueError("get_variable操作缺少name参数")
                
                var_value = variable_manager.get_variable(var_name)
                return StepExecutionResult(
                    success=var_value is not None,
                    step_index=step_index,
                    action=action,
                    description=step_config.get('description', action),
                    return_value=var_value,
                    error_message=f"变量不存在: {var_name}" if var_value is None else None
                )
                
            else:
                raise ValueError(f'不支持的操作类型: {action}')
            
            # 处理输出变量（对于有返回值的传统步骤）
            step_result = StepExecutionResult(
                success=True,
                step_index=step_index,
                action=action,
                description=step_config.get('description', action),
                return_value=return_value
            )
            
            # 如果配置了输出变量，存储返回值
            output_variable = step_config.get('output_variable')
            if output_variable and return_value is not None:
                success = variable_manager.store_variable(
                    variable_name=output_variable,
                    value=return_value,
                    source_step_index=step_index,
                    source_api_method=action
                )
                
                if success:
                    step_result.variable_assigned = output_variable
                else:
                    step_result.validation_warning = f"变量存储失败: {output_variable}"
            
            return step_result
            
        except Exception as e:
            return StepExecutionResult(
                success=False,
                step_index=step_index,
                action=action,
                description=step_config.get('description', action),
                error_message=f"传统步骤执行失败: {str(e)}"
            )
    
    def _process_variable_references(
        self, 
        params: Dict[str, Any], 
        variable_manager: VariableManager,
        step_index: int = 0
    ) -> Dict[str, Any]:
        """
        处理参数中的变量引用
        基础变量解析功能，核心功能由执行引擎处理
        """
        try:
            # 简化变量解析：核心功能已集成在执行引擎中
            # 这里只进行基本的字符串替换
            resolved_params = self._basic_variable_resolution(params, variable_manager)
            
            logger.debug(f"变量引用解析完成 [步骤 {step_index}]: {params} -> {resolved_params}")
            return resolved_params
            
        except Exception as e:
            logger.warning(f"变量引用解析失败 [步骤 {step_index}]: {str(e)}, 返回原始参数")
            return params
    
    def _basic_variable_resolution(self, params: Dict[str, Any], variable_manager: VariableManager) -> Dict[str, Any]:
        """基础变量解析，简单的字符串替换"""
        import re
        import json
        
        def resolve_value(value):
            if isinstance(value, str):
                # 查找${variable}模式
                pattern = r'\$\{([^}]+)\}'
                matches = re.findall(pattern, value)
                
                resolved_value = value
                for match in matches:
                    try:
                        # 尝试从变量管理器获取值
                        var_value = variable_manager.get_variable(match)
                        if var_value is not None:
                            resolved_value = resolved_value.replace(f'${{{match}}}', str(var_value))
                    except:
                        # 如果获取失败，保留原始引用
                        pass
                        
                return resolved_value
            elif isinstance(value, dict):
                return {k: resolve_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [resolve_value(item) for item in value]
            else:
                return value
        
        return resolve_value(params)
    
    async def _mock_evaluate_javascript(self, script: str) -> Any:
        """Mock JavaScript执行"""
        import json
        import random
        
        # 根据JavaScript脚本内容返回不同的模拟结果
        script_lower = script.lower()
        
        if 'return' not in script_lower:
            # 没有return语句，返回undefined
            return None
        
        # 优先检查返回结构，然后再检查具体内容
        if '{' in script and '}' in script:
            # 返回对象 - 根据脚本内容构造对应的对象
            result = {}
            
            if 'title' in script_lower and 'document.title' in script:
                result["title"] = "测试页面标题"
            if 'url' in script_lower and 'window.location.href' in script:
                result["url"] = "https://test-example.com/page"
            if 'itemcount' in script_lower and 'queryselectorall' in script_lower:
                result["itemCount"] = random.randint(1, 10)
            if 'timestamp' in script_lower or 'time' in script_lower:
                result["timestamp"] = "2025-01-30T10:00:00Z"
            if 'nested' in script_lower:
                result["nested"] = {"data": [1, 2, 3]}
            if 'complex' in script_lower:
                result["complex"] = True
            if 'pageTitl' in script or 'currentTime' in script:
                result["pageTitle"] = "测试页面标题"
                result["currentTime"] = "2025-01-30T10:00:00Z"
            
            # 如果没有匹配到具体字段，返回通用对象
            if not result:
                result = {
                    "result": "通用JavaScript对象",
                    "value": random.randint(1, 100)
                }
            
            return result
            
        elif '[' in script and ']' in script:
            # 返回数组
            return ["item1", "item2", "item3"]
        elif 'return true' in script_lower:
            return True
        elif 'return false' in script_lower:
            return False
        elif 'return null' in script_lower:
            return None
        elif 'return ' in script_lower and any(char.isdigit() for char in script):
            # 返回数字
            if '42' in script:
                return 42
            elif '.' in script or 'float' in script_lower:
                return round(random.uniform(1, 100), 2)
            else:
                return random.randint(1, 100)
        elif 'return ' in script_lower and ("'" in script or '"' in script):
            # 返回字符串
            if 'hello' in script_lower:
                return "hello world"
            else:
                return "测试字符串"
        else:
            # 默认返回字符串
            return f"JavaScript执行结果: {script[:50]}..."
    
    async def _record_step_execution(
        self,
        result: StepExecutionResult,
        execution_id: str,
        step_config: Dict[str, Any]
    ):
        """记录步骤执行到数据库"""
        # 在测试环境中跳过数据库记录
        if hasattr(self, '_skip_db_recording') and self._skip_db_recording:
            return
            
        try:
            from datetime import datetime
            
            start_time = datetime.utcnow()
            end_time = datetime.utcnow()
            duration = int(result.execution_time * 1000) if result.execution_time else 0
            
            step_execution = StepExecution(
                execution_id=execution_id,
                step_index=result.step_index,
                step_description=result.description,
                status='success' if result.success else 'failed',
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                screenshot_path=result.screenshot_path,
                ai_confidence=0.8,  # 默认置信度
                ai_decision=str({
                    'action': result.action,
                    'params': step_config.get('params', {}),
                    'return_value': result.return_value,
                    'variable_assigned': result.variable_assigned
                }),
                error_message=result.error_message
            )
            
            db.session.add(step_execution)
            db.session.commit()
            
        except Exception as e:
            logger.error(f"记录步骤执行失败: {e}")
            if hasattr(db.session, 'rollback'):
                try:
                    db.session.rollback()
                except Exception:
                    pass  # 忽略rollback失败
    
    async def execute_test_case(
        self,
        test_case: Dict[str, Any],
        execution_id: str,
        mode: str = 'headless'
    ) -> Dict[str, Any]:
        """
        执行完整的测试用例
        
        Args:
            test_case: 测试用例配置
            execution_id: 执行ID
            mode: 执行模式
            
        Returns:
            执行结果
        """
        start_time = time.time()
        steps = test_case.get('steps', [])
        results = []
        
        # 获取变量管理器
        variable_manager = get_variable_manager(execution_id)
        
        logger.info(f"开始执行测试用例: {test_case.get('name', '未命名')}, 共 {len(steps)} 个步骤")
        
        try:
            for i, step_config in enumerate(steps):
                step_result = await self.execute_step(
                    step_config, i, execution_id, variable_manager
                )
                results.append(step_result)
                
                # 如果步骤失败且配置为遇错停止
                if not step_result.success and test_case.get('stop_on_failure', True):
                    logger.warning(f"步骤 {i} 失败，停止执行")
                    break
        
        except Exception as e:
            logger.error(f"测试用例执行异常: {e}")
            results.append(StepExecutionResult(
                success=False,
                step_index=len(results),
                action='execution_error',
                description='测试用例执行异常',
                error_message=str(e)
            ))
        
        # 统计结果
        total_steps = len(results)
        successful_steps = sum(1 for r in results if r.success)
        execution_time = time.time() - start_time
        
        # 导出变量
        variables = variable_manager.export_variables()
        
        execution_result = {
            'execution_id': execution_id,
            'test_case_name': test_case.get('name', '未命名'),
            'total_steps': total_steps,
            'successful_steps': successful_steps,
            'failed_steps': total_steps - successful_steps,
            'success': successful_steps == total_steps and total_steps > 0,
            'execution_time': execution_time,
            'steps': [self._step_result_to_dict(r) for r in results],
            'variables': variables,
            'mode': mode
        }
        
        logger.info(f"测试用例执行完成: {successful_steps}/{total_steps} 步骤成功, 耗时 {execution_time:.2f}s")
        
        return execution_result
    
    def _step_result_to_dict(self, result: StepExecutionResult) -> Dict[str, Any]:
        """将步骤执行结果转换为字典"""
        return {
            'success': result.success,
            'step_index': result.step_index,
            'action': result.action,
            'description': result.description,
            'return_value': result.return_value,
            'variable_assigned': result.variable_assigned,
            'execution_time': result.execution_time,
            'error_message': result.error_message,
            'validation_warning': result.validation_warning,
            'screenshot_path': result.screenshot_path,
            'metadata': result.metadata
        }
    
    def get_supported_actions(self) -> List[str]:
        """获取支持的操作类型"""
        ai_actions = list(self.ai_extraction_methods.keys())
        legacy_actions = ['navigate', 'goto', 'ai_input', 'ai_tap', 'ai_assert', 'evaluateJavaScript', 'set_variable', 'get_variable']
        return ai_actions + legacy_actions
    
    def get_stats(self) -> Dict[str, Any]:
        """获取执行器统计信息"""
        return {
            'mock_mode': self.mock_mode,
            'client_available': self.midscene_client is not None,
            'supported_ai_methods': len(self.ai_extraction_methods),
            'ai_methods': list(self.ai_extraction_methods.keys()),
            'data_extractor_stats': self.data_extractor.get_stats()
        }