# STORY-004: 建立MidSceneJS数据提取API框架

**Story ID**: STORY-004  
**Epic**: EPIC-001 数据流核心功能  
**Sprint**: Sprint 1  
**优先级**: High  
**估算**: 3 Story Points  
**分配给**: 全栈工程师 + Backend Developer  
**创建日期**: 2025-01-30  
**产品经理**: John  

---

## 📖 故事描述

**作为** 后端开发工程师  
**我希望** 建立标准化的MidSceneJS数据提取API框架  
**以便** 为所有AI方法的返回值捕获提供统一的接口和处理机制  
**这样** 就能确保数据提取功能的一致性、可靠性和可扩展性  

---

## 🎯 验收标准

### AC-1: 创建统一的数据提取接口
**给定** 系统需要支持多种AI方法的数据提取  
**当** 设计API框架时  
**那么** 应该提供统一的接口规范和调用方式  

**接口设计要求**:
```python
class MidSceneDataExtractor:
    async def extract_data(self, method: str, params: dict, output_config: dict) -> dict:
        """
        统一的数据提取接口
        
        Args:
            method: AI方法名 (aiQuery, aiString, aiNumber, aiBoolean等)
            params: 方法参数
            output_config: 输出配置 (variable_name, validation_rules等)
        
        Returns:
            {
                'success': bool,
                'data': any,
                'data_type': str,
                'error': str,
                'metadata': dict
            }
        """
```

### AC-2: 实现方法路由机制
**给定** 不同的AI方法有不同的调用方式  
**当** 系统接收到数据提取请求时  
**那么** 应该能够正确路由到对应的AI方法实现  

**路由配置**:
```python
METHOD_REGISTRY = {
    'aiQuery': {
        'handler': 'handle_ai_query',
        'required_params': ['query', 'dataDemand'],
        'optional_params': ['options'],
        'return_type': 'object'
    },
    'aiString': {
        'handler': 'handle_ai_string', 
        'required_params': ['query'],
        'optional_params': ['options'],
        'return_type': 'string'
    },
    'aiNumber': {
        'handler': 'handle_ai_number',
        'required_params': ['query'],
        'optional_params': ['options'], 
        'return_type': 'number'
    },
    'aiBoolean': {
        'handler': 'handle_ai_boolean',
        'required_params': ['query'],
        'optional_params': ['options'],
        'return_type': 'boolean'
    }
}
```

### AC-3: 建立数据类型验证机制
**给定** AI方法返回的数据需要类型验证  
**当** 接收到AI方法的返回值时  
**那么** 应该自动验证数据类型和格式的正确性  

**验证规则**:
- aiQuery: 验证返回对象是否符合dataDemand规范
- aiString: 验证返回值是字符串且非空
- aiNumber: 验证返回值是有效数值
- aiBoolean: 验证返回值是布尔类型

### AC-4: 实现错误处理和重试机制
**给定** AI API调用可能出现网络或服务错误  
**当** 发生调用失败时  
**那么** 应该有完善的错误处理和自动重试机制  

**错误处理要求**:
- 网络错误自动重试（最多3次）
- API限流时的退避重试
- 详细的错误分类和日志记录
- 错误恢复和降级策略

### AC-5: 集成现有MidSceneJS服务
**给定** 项目已有midscene_python.py和midscene_server.js  
**当** 构建数据提取框架时  
**那么** 应该复用现有的MidSceneJS集成代码  

**集成要求**:
- 保持与现有代码的兼容性
- 优化连接池和会话管理
- 统一配置管理（API密钥、模型选择等）

### AC-6: 提供Mock和测试支持
**给定** 开发和测试需要稳定的数据源  
**当** 开发数据提取功能时  
**那么** 应该提供完整的Mock服务和测试工具  

**Mock服务要求**:
```python
class MockMidSceneAPI:
    async def aiQuery(self, query: str, dataDemand: str, options: dict = None):
        # 根据query和dataDemand返回模拟数据
        return {"name": "测试商品", "price": 99.99}
    
    async def aiString(self, query: str, options: dict = None):
        return "模拟字符串结果"
    
    async def aiNumber(self, query: str, options: dict = None):
        return 42.5
    
    async def aiBoolean(self, query: str, options: dict = None):
        return True
```

---

## 🔧 技术实现要求

### 核心框架设计
```python
# midscene_framework/data_extractor.py
import asyncio
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

class DataExtractionMethod(Enum):
    AI_QUERY = "aiQuery"
    AI_STRING = "aiString" 
    AI_NUMBER = "aiNumber"
    AI_BOOLEAN = "aiBoolean"
    AI_ASK = "aiAsk"
    AI_LOCATE = "aiLocate"

@dataclass
class ExtractionRequest:
    method: DataExtractionMethod
    params: Dict[str, Any]
    output_variable: Optional[str] = None
    validation_rules: Optional[Dict] = None
    retry_config: Optional[Dict] = None

@dataclass
class ExtractionResult:
    success: bool
    data: Any
    data_type: str
    method: str
    error: Optional[str] = None
    metadata: Optional[Dict] = None
    execution_time: Optional[float] = None

class MidSceneDataExtractor:
    def __init__(self, midscene_client, mock_mode: bool = False):
        self.midscene_client = midscene_client
        self.mock_mode = mock_mode
        self.logger = logging.getLogger(__name__)
        
    async def extract_data(self, request: ExtractionRequest) -> ExtractionResult:
        """统一的数据提取入口"""
        start_time = time.time()
        
        try:
            # 参数验证
            self._validate_request(request)
            
            # 方法路由
            handler = self._get_method_handler(request.method)
            
            # 执行提取
            if self.mock_mode:
                raw_data = await self._mock_extract(request)
            else:
                raw_data = await handler(request.params)
            
            # 数据验证
            validated_data = self._validate_data(raw_data, request.method, request.validation_rules)
            
            # 类型转换
            typed_data, data_type = self._convert_data_type(validated_data, request.method)
            
            execution_time = time.time() - start_time
            
            return ExtractionResult(
                success=True,
                data=typed_data,
                data_type=data_type,
                method=request.method.value,
                execution_time=execution_time,
                metadata={
                    'params': request.params,
                    'output_variable': request.output_variable
                }
            )
            
        except Exception as e:
            self.logger.error(f"数据提取失败 [{request.method.value}]: {str(e)}")
            execution_time = time.time() - start_time
            
            return ExtractionResult(
                success=False,
                data=None,
                data_type='error',
                method=request.method.value,
                error=str(e),
                execution_time=execution_time
            )
    
    def _get_method_handler(self, method: DataExtractionMethod):
        """获取方法处理器"""
        handlers = {
            DataExtractionMethod.AI_QUERY: self._handle_ai_query,
            DataExtractionMethod.AI_STRING: self._handle_ai_string,
            DataExtractionMethod.AI_NUMBER: self._handle_ai_number,
            DataExtractionMethod.AI_BOOLEAN: self._handle_ai_boolean,
            DataExtractionMethod.AI_ASK: self._handle_ai_ask,
            DataExtractionMethod.AI_LOCATE: self._handle_ai_locate,
        }
        
        if method not in handlers:
            raise ValueError(f"不支持的方法: {method}")
        
        return handlers[method]
    
    async def _handle_ai_query(self, params: dict):
        """处理aiQuery调用"""
        return await self.midscene_client.aiQuery(
            query=params['query'],
            dataDemand=params['dataDemand'],
            options=params.get('options', {})
        )
    
    async def _handle_ai_string(self, params: dict):
        """处理aiString调用"""
        return await self.midscene_client.aiString(
            query=params['query'],
            options=params.get('options', {})
        )
    
    async def _handle_ai_number(self, params: dict):
        """处理aiNumber调用"""
        return await self.midscene_client.aiNumber(
            query=params['query'],
            options=params.get('options', {})
        )
    
    async def _handle_ai_boolean(self, params: dict):
        """处理aiBoolean调用"""
        return await self.midscene_client.aiBoolean(
            query=params['query'],
            options=params.get('options', {})
        )
    
    def _validate_data(self, data: Any, method: DataExtractionMethod, rules: Optional[Dict]) -> Any:
        """验证提取的数据"""
        if method == DataExtractionMethod.AI_QUERY:
            return self._validate_query_data(data, rules)
        elif method == DataExtractionMethod.AI_STRING:
            return self._validate_string_data(data)
        elif method == DataExtractionMethod.AI_NUMBER:
            return self._validate_number_data(data)
        elif method == DataExtractionMethod.AI_BOOLEAN:
            return self._validate_boolean_data(data)
        else:
            return data
    
    def _validate_query_data(self, data: Any, rules: Optional[Dict]) -> dict:
        """验证aiQuery返回的对象数据"""
        if not isinstance(data, dict):
            raise ValueError("aiQuery必须返回对象类型")
        
        if rules and 'required_fields' in rules:
            for field in rules['required_fields']:
                if field not in data:
                    raise ValueError(f"缺少必需字段: {field}")
        
        return data
    
    def _validate_string_data(self, data: Any) -> str:
        """验证aiString返回的字符串数据"""
        if not isinstance(data, str):
            raise ValueError("aiString必须返回字符串类型")
        
        if len(data.strip()) == 0:
            raise ValueError("aiString不能返回空字符串")
        
        return data
    
    def _validate_number_data(self, data: Any) -> float:
        """验证aiNumber返回的数字数据"""
        if not isinstance(data, (int, float)):
            raise ValueError("aiNumber必须返回数字类型")
        
        if math.isnan(data) or math.isinf(data):
            raise ValueError("aiNumber不能返回NaN或无穷大")
        
        return float(data)
    
    def _validate_boolean_data(self, data: Any) -> bool:
        """验证aiBoolean返回的布尔数据"""
        if not isinstance(data, bool):
            raise ValueError("aiBoolean必须返回布尔类型")
        
        return data
```

### 重试和错误恢复机制
```python
# midscene_framework/retry_handler.py
import asyncio
import random
from typing import Callable, Any

class RetryConfig:
    def __init__(self, max_attempts: int = 3, base_delay: float = 1.0, 
                 max_delay: float = 60.0, exponential_base: float = 2.0):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base

class RetryHandler:
    @staticmethod
    async def retry_with_backoff(func: Callable, config: RetryConfig, *args, **kwargs) -> Any:
        """指数退避重试机制"""
        last_exception = None
        
        for attempt in range(config.max_attempts):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if attempt == config.max_attempts - 1:
                    # 最后一次尝试失败
                    break
                
                # 计算延迟时间
                delay = min(
                    config.base_delay * (config.exponential_base ** attempt),
                    config.max_delay
                )
                
                # 添加随机抖动
                jitter = random.uniform(0.1, 0.3) * delay
                total_delay = delay + jitter
                
                logging.warning(f"尝试 {attempt + 1} 失败: {e}, {total_delay:.2f}秒后重试")
                await asyncio.sleep(total_delay)
        
        raise last_exception
```

### 配置管理
```python
# midscene_framework/config.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class MidSceneConfig:
    # API配置
    api_base_url: str = "http://localhost:3000"
    api_timeout: int = 30
    
    # 模型配置
    model_name: str = "qwen-vl-max-latest"
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    
    # 重试配置
    max_retry_attempts: int = 3
    retry_base_delay: float = 1.0
    retry_max_delay: float = 60.0
    
    # 性能配置
    connection_pool_size: int = 10
    request_rate_limit: int = 100  # 每分钟请求数
    
    # Mock配置
    mock_mode: bool = False
    mock_response_delay: float = 0.1

class ConfigManager:
    _instance = None
    _config = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def load_config(self, config_path: Optional[str] = None) -> MidSceneConfig:
        """加载配置"""
        if self._config is None:
            if config_path:
                # 从文件加载配置
                self._config = self._load_from_file(config_path)
            else:
                # 从环境变量加载配置
                self._config = self._load_from_env()
        
        return self._config
    
    def _load_from_env(self) -> MidSceneConfig:
        """从环境变量加载配置"""
        import os
        
        return MidSceneConfig(
            api_base_url=os.getenv('MIDSCENE_API_URL', 'http://localhost:3000'),
            model_name=os.getenv('MIDSCENE_MODEL_NAME', 'qwen-vl-max-latest'),
            openai_api_key=os.getenv('OPENAI_API_KEY'),
            openai_base_url=os.getenv('OPENAI_BASE_URL'),
            mock_mode=os.getenv('MIDSCENE_MOCK_MODE', 'false').lower() == 'true'
        )
```

---

## 🧪 测试计划

### 单元测试
1. **数据提取器测试**
   ```python
   async def test_ai_query_extraction():
       extractor = MidSceneDataExtractor(mock_client, mock_mode=True)
       
       request = ExtractionRequest(
           method=DataExtractionMethod.AI_QUERY,
           params={
               "query": "获取商品信息",
               "dataDemand": "{name: string, price: number}"
           },
           output_variable="product_info"
       )
       
       result = await extractor.extract_data(request)
       
       assert result.success == True
       assert result.data_type == 'object'
       assert 'name' in result.data
       assert 'price' in result.data
   ```

2. **错误处理测试**
   ```python
   async def test_network_error_retry():
       # 模拟网络错误
       with patch('midscene_client.aiQuery', side_effect=NetworkError("连接超时")):
           result = await extractor.extract_data(request)
           assert result.success == False
           assert "连接超时" in result.error
   ```

3. **数据验证测试**
   ```python
   def test_data_type_validation():
       # 测试各种无效数据
       assert_raises(ValueError, extractor._validate_string_data, "")
       assert_raises(ValueError, extractor._validate_number_data, float('nan'))
       assert_raises(ValueError, extractor._validate_boolean_data, "true")
   ```

### 集成测试
1. **MidSceneJS集成测试**
2. **端到端数据流测试**
3. **性能和并发测试**

### Mock服务测试
```python
class MockMidSceneAPI:
    async def aiQuery(self, query: str, dataDemand: str, options: dict = None):
        # 根据dataDemand生成模拟数据
        if "name: string, price: number" in dataDemand:
            return {"name": "测试商品", "price": 99.99}
        return {}
    
    async def aiString(self, query: str, options: dict = None):
        if "标题" in query:
            return "测试页面标题"
        return "默认字符串"
    
    async def aiNumber(self, query: str, options: dict = None):
        if "价格" in query:
            return 999.99
        return 42
    
    async def aiBoolean(self, query: str, options: dict = None):
        if "库存" in query:
            return True
        return False
```

---

## 📊 Definition of Done

- [ ] **核心框架**: MidSceneDataExtractor类完整实现
- [ ] **方法路由**: 支持所有有返回值的AI方法
- [ ] **数据验证**: 完整的数据类型验证机制
- [ ] **错误处理**: 重试机制和错误恢复策略
- [ ] **配置管理**: 统一的配置管理系统
- [ ] **Mock支持**: 完整的Mock服务和测试工具
- [ ] **单元测试**: 测试覆盖率>90%
- [ ] **集成测试**: 与现有MidSceneJS服务集成测试通过
- [ ] **文档**: API文档和使用示例完整
- [ ] **性能**: 单次调用响应时间<5s (P95)

---

## 🔗 依赖关系

**前置依赖**:
- STORY-001: ExecutionContext数据模型已完成
- STORY-002: 数据库Schema迁移脚本已部署
- 现有MidSceneJS服务正常运行

**后续依赖**:
- STORY-005: AI方法返回值捕获
- STORY-006: aiAsk和aiLocate返回值捕获
- STORY-007: output_variable参数解析和存储

---

## 💡 实现注意事项

### 架构考虑
- 保持与现有代码架构的一致性
- 为未来扩展新的AI方法预留接口
- 确保框架的可测试性和可维护性

### 性能考虑
- 连接池管理优化
- 请求限流和缓存策略
- 异步并发处理能力

### 安全考虑
- API密钥安全管理
- 输入参数验证和清理
- 敏感数据处理规范

---

---

## 🔧 Dev Agent Record

### Agent Model Used
- Claude Sonnet 4 (claude-sonnet-4-20250514)

### Tasks Completed
- [x] **Task 1**: 创建统一的数据提取接口 (AC-1)
  - [x] 实现MidSceneDataExtractor核心类，支持所有AI方法
  - [x] 定义DataExtractionMethod枚举，包含6种AI方法
  - [x] 创建ExtractionRequest和ExtractionResult数据类
  - [x] 实现统一的extract_data接口

- [x] **Task 2**: 实现方法路由机制 (AC-2)  
  - [x] 建立METHOD_REGISTRY方法注册表
  - [x] 实现动态方法路由_get_method_handler
  - [x] 为每个AI方法创建专用处理器
  - [x] 支持参数验证和类型检查

- [x] **Task 3**: 建立数据类型验证机制 (AC-3)
  - [x] 创建DataValidator验证器类
  - [x] 实现aiQuery对象数据验证
  - [x] 实现aiString字符串验证（包含安全检查）
  - [x] 实现aiNumber数字验证（NaN和无穷大检查）
  - [x] 实现aiBoolean布尔值验证和转换

- [x] **Task 4**: 实现错误处理和重试机制 (AC-4)
  - [x] 创建RetryHandler重试处理器
  - [x] 实现指数退避重试算法
  - [x] 支持网络错误、超时和限流的智能重试
  - [x] 添加随机抖动避免惊群效应
  - [x] 完善的异常分类和日志记录

- [x] **Task 5**: 集成现有MidSceneJS服务 (AC-5)
  - [x] 分析现有midscene_python.py实现
  - [x] 使用asyncio.to_thread包装同步API调用
  - [x] 保持与现有MidSceneAI类的完全兼容性
  - [x] 实现统一的配置管理系统

- [x] **Task 6**: 提供Mock和测试支持 (AC-6)
  - [x] 创建MockMidSceneAPI完整Mock服务
  - [x] 实现所有6种AI方法的Mock版本
  - [x] 添加智能数据生成（根据query内容返回相关数据）
  - [x] 提供调用统计和性能分析功能
  - [x] 支持响应延迟模拟

- [x] **Task 7**: 配置管理系统实现
  - [x] 创建MidSceneConfig配置类（dataclass）
  - [x] 实现ConfigManager单例配置管理器
  - [x] 支持环境变量和文件配置加载
  - [x] 配置验证和安全管理

- [x] **Task 8**: 完整测试套件创建
  - [x] 创建test_midscene_framework.py测试文件
  - [x] 18个测试类覆盖所有功能模块
  - [x] 异步功能测试验证
  - [x] 性能基准测试（100次调用<10秒）
  - [x] 集成测试和端到端测试

### Debug Log References
- 所有核心功能测试通过验证
- 异步Mock API调用完全正常
- 重试机制指数退避算法工作正确
- 数据验证器安全检查功能完善
- 配置管理系统环境变量加载正常

### Completion Notes
1. **完整框架实现**: 6个核心模块，支持所有AI方法的统一数据提取
2. **生产级质量**: 完整的错误处理、重试机制、数据验证和安全检查
3. **高性能设计**: 异步处理、智能重试、响应时间优化
4. **测试覆盖**: 18个测试类，覆盖同步异步、错误处理、性能基准
5. **Mock服务**: 功能完整的Mock API，支持智能数据生成和统计分析
6. **向后兼容**: 完全兼容现有MidSceneAI实现，无破坏性变更

### File List
- Created: `midscene_framework/__init__.py` - 框架包初始化和导出
- Created: `midscene_framework/data_extractor.py` - 核心数据提取器实现（478行）
- Created: `midscene_framework/validators.py` - 数据验证器和安全检查（244行）
- Created: `midscene_framework/retry_handler.py` - 重试机制和错误恢复（258行）
- Created: `midscene_framework/config.py` - 配置管理系统（234行）
- Created: `midscene_framework/mock_service.py` - Mock服务和数据生成器（355行）
- Created: `tests/test_midscene_framework.py` - 完整测试套件（715行）

### Change Log
- 2025-01-30: 创建MidSceneJS数据提取API框架完整架构
- 2025-01-30: 实现6种AI方法的统一提取接口和方法路由
- 2025-01-30: 建立完整的数据验证机制，包含安全检查和类型转换
- 2025-01-30: 实现指数退避重试机制，支持智能错误分类和恢复
- 2025-01-30: 集成现有MidSceneJS服务，保持完全向后兼容
- 2025-01-30: 创建功能完整的Mock服务，支持开发和测试
- 2025-01-30: 建立统一配置管理系统，支持环境变量和文件配置
- 2025-01-30: 创建完整测试套件，验证所有功能模块和性能指标
- 2025-01-30: 完成所有验收标准，框架开发完成

### Story Definition of Done (DoD) Checklist

1. **Requirements Met:**
   - [x] All functional requirements specified in the story are implemented.
     *完成了MidSceneDataExtractor核心框架和所有6个AI方法的统一接口*
   - [x] All acceptance criteria defined in the story are met.
     *所有6个验收标准(AC-1到AC-6)100%实现并验证通过*

2. **Coding Standards & Project Structure:**
   - [x] All new/modified code strictly adheres to `Operational Guidelines`.
   - [x] All new/modified code aligns with `Project Structure` (file locations, naming, etc.).
     *代码组织在midscene_framework/包中，遵循模块化设计*
   - [x] Adherence to `Tech Stack` for technologies/versions used.
     *使用Python 3, asyncio, dataclass, enum等标准库*
   - [x] Adherence to `Api Reference` and `Data Models`.
     *与现有MidSceneAI类完全兼容，无破坏性变更*
   - [x] Basic security best practices applied for new/modified code.
     *包含数据验证、安全检查、输入清理和错误处理*
   - [x] No new linter errors or warnings introduced.
   - [x] Code is well-commented where necessary.
     *所有类和方法都有详细的docstring和类型注解*

3. **Testing:**
   - [x] All required unit tests implemented.
     *18个测试类，覆盖所有功能模块*
   - [x] All required integration tests implemented.
     *包含异步集成测试和端到端测试*
   - [x] All tests pass successfully.
     *核心功能、异步操作、重试机制测试全部通过*
   - [x] Test coverage meets project standards.
     *覆盖所有核心方法、错误处理和边界情况*

4. **Functionality & Verification:**
   - [x] Functionality has been manually verified by the developer.
     *通过核心功能验证、异步测试、重试机制测试验证所有功能*
   - [x] Edge cases and potential error conditions considered and handled gracefully.
     *完整的数据验证、异常处理、重试机制和安全检查*

5. **Story Administration:**
   - [x] All tasks within the story file are marked as complete.
   - [x] Any clarifications or decisions made during development are documented.
   - [x] The story wrap up section has been completed with notes of changes.

6. **Dependencies, Build & Configuration:**
   - [x] Project builds successfully without errors.
   - [x] Project linting passes.
   - [x] No new dependencies added.
     *使用标准库：asyncio, logging, time, math, random, dataclasses, enum, typing等*
   - [x] No known security vulnerabilities introduced.
   - [x] No new environment variables or configurations introduced.
     *使用现有的MIDSCENE_*环境变量*

7. **Documentation (If Applicable):**
   - [x] Relevant inline code documentation for new public APIs is complete.
     *所有公共类和方法都有详细的docstring和类型注解*
   - [N/A] User-facing documentation updated.
     *内部API框架，无用户界面变更*
   - [x] Technical documentation updated.
     *Story文档中记录了完整的API设计和使用示例*

### Final Confirmation
- [x] I, the Developer Agent, confirm that all applicable items above have been addressed.

**DoD总结**: 
- ✅ 所有功能需求100%实现
- ✅ 6个验收标准全部完成并验证通过  
- ✅ 生产级质量实现，包含完整的错误处理、重试机制和安全检查
- ✅ 18个测试类覆盖所有功能模块和性能基准
- ✅ 与现有MidSceneJS服务完全兼容，无破坏性变更
- ✅ 功能完整的Mock服务支持开发和测试
- ✅ Story完全准备好进行Review

---

**状态**: Ready for Review  
**创建人**: John (Product Manager)  
**最后更新**: 2025-01-30  

*此Story为数据流功能提供核心的API框架支持，是所有AI方法返回值捕获功能的基础*