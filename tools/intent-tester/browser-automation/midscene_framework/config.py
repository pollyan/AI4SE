#!/usr/bin/env python3
"""
配置管理
统一的配置管理系统
"""

import os
import json
import logging
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class MidSceneConfig:
    """MidScene配置类"""

    # API配置
    api_base_url: str = "http://localhost:3001"
    api_timeout: int = 30

    # 模型配置
    model_name: str = "qwen-vl-max-latest"
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None

    # 重试配置
    max_retry_attempts: int = 3
    retry_base_delay: float = 1.0
    retry_max_delay: float = 60.0
    retry_exponential_base: float = 2.0

    # 性能配置
    connection_pool_size: int = 10
    request_rate_limit: int = 100  # 每分钟请求数

    # Mock配置
    mock_mode: bool = False
    mock_response_delay: float = 0.1

    # 日志配置
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # 缓存配置
    enable_cache: bool = True
    cache_ttl: int = 300  # 缓存过期时间（秒）

    def __post_init__(self):
        """参数验证"""
        if self.api_timeout <= 0:
            raise ValueError("api_timeout必须大于0")

        if self.max_retry_attempts < 1:
            raise ValueError("max_retry_attempts必须大于等于1")

        if self.retry_base_delay <= 0:
            raise ValueError("retry_base_delay必须大于0")

        if self.connection_pool_size <= 0:
            raise ValueError("connection_pool_size必须大于0")

        if self.request_rate_limit <= 0:
            raise ValueError("request_rate_limit必须大于0")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MidSceneConfig":
        """从字典创建配置"""
        return cls(**data)


class ConfigManager:
    """配置管理器（单例模式）"""

    _instance = None
    _config = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load_config(self, config_path: Optional[str] = None) -> MidSceneConfig:
        """
        加载配置

        Args:
            config_path: 配置文件路径，如果为None则从环境变量加载

        Returns:
            配置实例
        """
        if self._config is None:
            if config_path and Path(config_path).exists():
                self._config = self._load_from_file(config_path)
                logger.info(f"从文件加载配置: {config_path}")
            else:
                self._config = self._load_from_env()
                logger.info("从环境变量加载配置")

        return self._config

    def get_config(self) -> Optional[MidSceneConfig]:
        """获取当前配置"""
        return self._config

    def update_config(self, **kwargs) -> MidSceneConfig:
        """
        更新配置

        Args:
            **kwargs: 要更新的配置项

        Returns:
            更新后的配置
        """
        if self._config is None:
            self._config = self._load_from_env()

        # 更新配置
        config_dict = self._config.to_dict()
        config_dict.update(kwargs)

        self._config = MidSceneConfig.from_dict(config_dict)
        logger.info(f"配置已更新: {list(kwargs.keys())}")

        return self._config

    def save_config(self, config_path: str):
        """
        保存配置到文件

        Args:
            config_path: 配置文件路径
        """
        if self._config is None:
            raise ValueError("没有可保存的配置")

        config_dict = self._config.to_dict()

        # 处理敏感信息
        if config_dict.get("openai_api_key"):
            config_dict["openai_api_key"] = "***hidden***"

        Path(config_path).parent.mkdir(parents=True, exist_ok=True)

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_dict, f, indent=2, ensure_ascii=False)

        logger.info(f"配置已保存到: {config_path}")

    def _load_from_file(self, config_path: str) -> MidSceneConfig:
        """从文件加载配置"""
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)

            # 如果API密钥被隐藏，从环境变量加载
            if config_data.get("openai_api_key") == "***hidden***":
                config_data["openai_api_key"] = os.getenv("OPENAI_API_KEY")

            return MidSceneConfig.from_dict(config_data)

        except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
            logger.error(f"加载配置文件失败: {e}")
            logger.info("回退到环境变量配置")
            return self._load_from_env()

    def _load_from_env(self) -> MidSceneConfig:
        """从环境变量加载配置"""
        return MidSceneConfig(
            # API配置
            api_base_url=os.getenv("MIDSCENE_API_URL", "http://localhost:3001"),
            api_timeout=int(os.getenv("MIDSCENE_API_TIMEOUT", "30")),
            # 模型配置
            model_name=os.getenv("MIDSCENE_MODEL_NAME", "qwen-vl-max-latest"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_base_url=os.getenv(
                "OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
            ),
            # 重试配置
            max_retry_attempts=int(os.getenv("MIDSCENE_MAX_RETRY_ATTEMPTS", "3")),
            retry_base_delay=float(os.getenv("MIDSCENE_RETRY_BASE_DELAY", "1.0")),
            retry_max_delay=float(os.getenv("MIDSCENE_RETRY_MAX_DELAY", "60.0")),
            retry_exponential_base=float(
                os.getenv("MIDSCENE_RETRY_EXPONENTIAL_BASE", "2.0")
            ),
            # 性能配置
            connection_pool_size=int(os.getenv("MIDSCENE_CONNECTION_POOL_SIZE", "10")),
            request_rate_limit=int(os.getenv("MIDSCENE_REQUEST_RATE_LIMIT", "100")),
            # Mock配置
            mock_mode=os.getenv("MIDSCENE_MOCK_MODE", "false").lower() == "true",
            mock_response_delay=float(os.getenv("MIDSCENE_MOCK_RESPONSE_DELAY", "0.1")),
            # 日志配置
            log_level=os.getenv("MIDSCENE_LOG_LEVEL", "INFO"),
            log_format=os.getenv(
                "MIDSCENE_LOG_FORMAT",
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            ),
            # 缓存配置
            enable_cache=os.getenv("MIDSCENE_ENABLE_CACHE", "true").lower() == "true",
            cache_ttl=int(os.getenv("MIDSCENE_CACHE_TTL", "300")),
        )

    def reset_config(self):
        """重置配置"""
        self._config = None
        logger.info("配置已重置")

    def validate_config(self) -> list[str]:
        """
        验证配置

        Returns:
            验证错误列表
        """
        errors = []

        if self._config is None:
            errors.append("配置未加载")
            return errors

        # 验证API密钥
        if not self._config.openai_api_key:
            errors.append("OPENAI_API_KEY未设置")

        # 验证API地址
        if not self._config.api_base_url:
            errors.append("api_base_url未设置")
        elif not self._config.api_base_url.startswith(("http://", "https://")):
            errors.append("api_base_url格式不正确")

        # 验证模型名称
        if not self._config.model_name:
            errors.append("model_name未设置")

        return errors

    def get_environment_info(self) -> Dict[str, Any]:
        """获取环境信息"""
        return {
            "python_version": os.sys.version,
            "platform": os.name,
            "cwd": os.getcwd(),
            "env_vars": {
                key: value
                for key, value in os.environ.items()
                if key.startswith("MIDSCENE_") and "KEY" not in key
            },
        }


# 全局配置管理器实例
config_manager = ConfigManager()


def get_config() -> MidSceneConfig:
    """获取全局配置"""
    return config_manager.load_config()


def update_config(**kwargs) -> MidSceneConfig:
    """更新全局配置"""
    return config_manager.update_config(**kwargs)
