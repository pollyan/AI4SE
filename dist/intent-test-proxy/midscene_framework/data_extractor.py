#!/usr/bin/env python3
"""
MidSceneJS数据提取器核心实现
提供统一的数据提取接口和方法路由
"""

import asyncio
import logging
import time
import math
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from .validators import DataValidator
from .retry_handler import RetryHandler, RetryConfig

logger = logging.getLogger(__name__)


class DataExtractionMethod(Enum):
    """支持的数据提取方法枚举"""

    AI_QUERY = "aiQuery"
    AI_STRING = "aiString"
    AI_NUMBER = "aiNumber"
    AI_BOOLEAN = "aiBoolean"
    AI_ASK = "aiAsk"
    AI_LOCATE = "aiLocate"


@dataclass
class ExtractionRequest:
    """数据提取请求"""

    method: DataExtractionMethod
    params: Dict[str, Any]
    output_variable: Optional[str] = None
    validation_rules: Optional[Dict] = None
    retry_config: Optional[Dict] = None


@dataclass
class ExtractionResult:
    """数据提取结果"""

    success: bool
    data: Any
    data_type: str
    method: str
    error: Optional[str] = None
    metadata: Optional[Dict] = None
    execution_time: Optional[float] = None


class MidSceneDataExtractor:
    """
    MidSceneJS数据提取器
    统一的数据提取接口，支持多种AI方法和Mock模式
    """

    # 方法注册表
    METHOD_REGISTRY = {
        DataExtractionMethod.AI_QUERY: {
            "handler": "_handle_ai_query",
            "required_params": ["query", "dataDemand"],
            "optional_params": ["options"],
            "return_type": "object",
        },
        DataExtractionMethod.AI_STRING: {
            "handler": "_handle_ai_string",
            "required_params": ["query"],
            "optional_params": ["options"],
            "return_type": "string",
        },
        DataExtractionMethod.AI_NUMBER: {
            "handler": "_handle_ai_number",
            "required_params": ["query"],
            "optional_params": ["options"],
            "return_type": "number",
        },
        DataExtractionMethod.AI_BOOLEAN: {
            "handler": "_handle_ai_boolean",
            "required_params": ["query"],
            "optional_params": ["options"],
            "return_type": "boolean",
        },
        DataExtractionMethod.AI_ASK: {
            "handler": "_handle_ai_ask",
            "required_params": ["query"],
            "optional_params": ["options"],
            "return_type": "string",
        },
        DataExtractionMethod.AI_LOCATE: {
            "handler": "_handle_ai_locate",
            "required_params": ["query"],
            "optional_params": ["options"],
            "return_type": "object",
        },
    }

    def __init__(self, midscene_client=None, mock_mode: bool = False):
        """
        初始化数据提取器

        Args:
            midscene_client: MidSceneJS客户端实例
            mock_mode: 是否使用Mock模式
        """
        self.midscene_client = midscene_client
        self.mock_mode = mock_mode
        self.logger = logger
        self.data_validator = DataValidator()

        # 设置默认重试配置
        self.default_retry_config = RetryConfig(
            max_attempts=3, base_delay=1.0, max_delay=60.0, exponential_base=2.0
        )

        logger.info(f"初始化MidSceneDataExtractor: mock_mode={mock_mode}")

    async def extract_data(self, request: ExtractionRequest) -> ExtractionResult:
        """
        统一的数据提取入口

        Args:
            request: 数据提取请求

        Returns:
            数据提取结果
        """
        start_time = time.time()

        try:
            # 参数验证
            self._validate_request(request)

            # 获取方法处理器
            handler = self._get_method_handler(request.method)

            # 设置重试配置
            retry_config = self._get_retry_config(request.retry_config)

            # 执行提取（带重试）
            if self.mock_mode:
                raw_data = await self._mock_extract(request)
            else:
                # 使用重试机制执行真实的API调用
                raw_data = await RetryHandler.retry_with_backoff(
                    handler, retry_config, request.params
                )

            # 数据验证
            validated_data = self._validate_data(
                raw_data, request.method, request.validation_rules
            )

            # 类型转换和检测
            typed_data, data_type = self._convert_data_type(
                validated_data, request.method
            )

            execution_time = time.time() - start_time

            result = ExtractionResult(
                success=True,
                data=typed_data,
                data_type=data_type,
                method=request.method.value,
                execution_time=execution_time,
                metadata={
                    "params": request.params,
                    "output_variable": request.output_variable,
                    "validation_rules": request.validation_rules,
                    "retry_attempts": 0,  # TODO: 从重试处理器获取实际重试次数
                },
            )

            logger.info(
                f"数据提取成功 [{request.method.value}]: {data_type}, 耗时 {execution_time:.3f}s"
            )
            return result

        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = str(e)

            logger.error(
                f"数据提取失败 [{request.method.value}]: {error_msg}, 耗时 {execution_time:.3f}s"
            )

            return ExtractionResult(
                success=False,
                data=None,
                data_type="error",
                method=request.method.value,
                error=error_msg,
                execution_time=execution_time,
                metadata={"params": request.params, "error_type": type(e).__name__},
            )

    def _validate_request(self, request: ExtractionRequest):
        """验证请求参数"""
        if not isinstance(request.method, DataExtractionMethod):
            raise ValueError(f"不支持的方法类型: {request.method}")

        if request.method not in self.METHOD_REGISTRY:
            raise ValueError(f"未注册的方法: {request.method}")

        # 验证必需参数
        method_config = self.METHOD_REGISTRY[request.method]
        required_params = method_config["required_params"]

        for param in required_params:
            if param not in request.params:
                raise ValueError(f"缺少必需参数: {param}")

        # 验证参数类型
        if "query" in request.params and not isinstance(request.params["query"], str):
            raise ValueError("query参数必须是字符串")

        if "dataDemand" in request.params and not isinstance(
            request.params["dataDemand"], str
        ):
            raise ValueError("dataDemand参数必须是字符串")

    def _get_method_handler(self, method: DataExtractionMethod) -> Callable:
        """获取方法处理器"""
        method_config = self.METHOD_REGISTRY[method]
        handler_name = method_config["handler"]

        if not hasattr(self, handler_name):
            raise ValueError(f"未找到处理器方法: {handler_name}")

        return getattr(self, handler_name)

    def _get_retry_config(self, custom_config: Optional[Dict]) -> RetryConfig:
        """获取重试配置"""
        if custom_config:
            return RetryConfig(
                max_attempts=custom_config.get(
                    "max_attempts", self.default_retry_config.max_attempts
                ),
                base_delay=custom_config.get(
                    "base_delay", self.default_retry_config.base_delay
                ),
                max_delay=custom_config.get(
                    "max_delay", self.default_retry_config.max_delay
                ),
                exponential_base=custom_config.get(
                    "exponential_base", self.default_retry_config.exponential_base
                ),
            )
        return self.default_retry_config

    async def _handle_ai_query(self, params: dict):
        """处理aiQuery调用"""
        if not self.midscene_client:
            raise ValueError("MidScene客户端未初始化")

        return await asyncio.to_thread(
            self.midscene_client.ai_query,
            data_demand=params["dataDemand"],
            options=params.get("options", {}),
        )

    async def _handle_ai_string(self, params: dict):
        """处理aiString调用"""
        if not self.midscene_client:
            raise ValueError("MidScene客户端未初始化")

        return await asyncio.to_thread(
            self.midscene_client.ai_string,
            query=params["query"],
            options=params.get("options", {}),
        )

    async def _handle_ai_number(self, params: dict):
        """处理aiNumber调用"""
        if not self.midscene_client:
            raise ValueError("MidScene客户端未初始化")

        return await asyncio.to_thread(
            self.midscene_client.ai_number,
            query=params["query"],
            options=params.get("options", {}),
        )

    async def _handle_ai_boolean(self, params: dict):
        """处理aiBoolean调用"""
        if not self.midscene_client:
            raise ValueError("MidScene客户端未初始化")

        return await asyncio.to_thread(
            self.midscene_client.ai_boolean,
            query=params["query"],
            options=params.get("options", {}),
        )

    async def _handle_ai_ask(self, params: dict):
        """处理aiAsk调用"""
        if not self.midscene_client:
            raise ValueError("MidScene客户端未初始化")

        # 假设MidSceneAI有ai_ask方法，如果没有则需要添加
        if hasattr(self.midscene_client, "ai_ask"):
            return await asyncio.to_thread(
                self.midscene_client.ai_ask,
                query=params["query"],
                options=params.get("options", {}),
            )
        else:
            raise NotImplementedError("ai_ask方法尚未在MidSceneAI中实现")

    async def _handle_ai_locate(self, params: dict):
        """处理aiLocate调用"""
        if not self.midscene_client:
            raise ValueError("MidScene客户端未初始化")

        # 假设MidSceneAI有ai_locate方法，如果没有则需要添加
        if hasattr(self.midscene_client, "ai_locate"):
            return await asyncio.to_thread(
                self.midscene_client.ai_locate,
                query=params["query"],
                options=params.get("options", {}),
            )
        else:
            raise NotImplementedError("ai_locate方法尚未在MidSceneAI中实现")

    async def _mock_extract(self, request: ExtractionRequest) -> Any:
        """Mock数据提取"""
        from .mock_service import MockMidSceneAPI

        mock_api = MockMidSceneAPI()

        # 添加一点延迟模拟真实API调用
        await asyncio.sleep(0.1)

        if request.method == DataExtractionMethod.AI_QUERY:
            return await mock_api.aiQuery(
                query=request.params["query"],
                dataDemand=request.params["dataDemand"],
                options=request.params.get("options", {}),
            )
        elif request.method == DataExtractionMethod.AI_STRING:
            return await mock_api.aiString(
                query=request.params["query"], options=request.params.get("options", {})
            )
        elif request.method == DataExtractionMethod.AI_NUMBER:
            return await mock_api.aiNumber(
                query=request.params["query"], options=request.params.get("options", {})
            )
        elif request.method == DataExtractionMethod.AI_BOOLEAN:
            return await mock_api.aiBoolean(
                query=request.params["query"], options=request.params.get("options", {})
            )
        elif request.method == DataExtractionMethod.AI_ASK:
            return await mock_api.aiAsk(
                query=request.params["query"], options=request.params.get("options", {})
            )
        elif request.method == DataExtractionMethod.AI_LOCATE:
            return await mock_api.aiLocate(
                query=request.params["query"], options=request.params.get("options", {})
            )
        else:
            raise ValueError(f"Mock模式不支持的方法: {request.method}")

    def _validate_data(
        self, data: Any, method: DataExtractionMethod, rules: Optional[Dict]
    ) -> Any:
        """验证提取的数据"""
        if method == DataExtractionMethod.AI_QUERY:
            return self.data_validator.validate_query_data(data, rules)
        elif method == DataExtractionMethod.AI_STRING:
            return self.data_validator.validate_string_data(data)
        elif method == DataExtractionMethod.AI_NUMBER:
            return self.data_validator.validate_number_data(data)
        elif method == DataExtractionMethod.AI_BOOLEAN:
            return self.data_validator.validate_boolean_data(data)
        elif method == DataExtractionMethod.AI_ASK:
            return self.data_validator.validate_ai_ask_result(data)
        elif method == DataExtractionMethod.AI_LOCATE:
            return self.data_validator.validate_ai_locate_result(data)
        else:
            # 对于其他方法，进行基本验证
            if data is None:
                raise ValueError(f"{method.value}不能返回None")
            return data

    def _convert_data_type(
        self, data: Any, method: DataExtractionMethod
    ) -> tuple[Any, str]:
        """类型转换和检测"""
        method_config = self.METHOD_REGISTRY[method]
        expected_type = method_config["return_type"]

        # 检测实际类型
        if isinstance(data, bool):
            actual_type = "boolean"
        elif isinstance(data, int):
            actual_type = "number"
        elif isinstance(data, float):
            actual_type = "number"
        elif isinstance(data, str):
            actual_type = "string"
        elif isinstance(data, list):
            actual_type = "array"
        elif isinstance(data, dict):
            actual_type = "object"
        elif data is None:
            actual_type = "null"
        else:
            actual_type = "unknown"

        # 验证类型是否匹配预期
        if expected_type != actual_type and expected_type != "unknown":
            logger.warning(f"类型不匹配: 预期 {expected_type}, 实际 {actual_type}")

        return data, actual_type

    def get_supported_methods(self) -> list[str]:
        """获取支持的方法列表"""
        return [method.value for method in self.METHOD_REGISTRY.keys()]

    def get_method_info(self, method: DataExtractionMethod) -> Dict:
        """获取方法信息"""
        if method not in self.METHOD_REGISTRY:
            raise ValueError(f"未注册的方法: {method}")

        return self.METHOD_REGISTRY[method].copy()

    def get_stats(self) -> Dict:
        """获取提取器统计信息"""
        return {
            "supported_methods": len(self.METHOD_REGISTRY),
            "mock_mode": self.mock_mode,
            "client_available": self.midscene_client is not None,
            "methods": list(self.METHOD_REGISTRY.keys()),
        }
