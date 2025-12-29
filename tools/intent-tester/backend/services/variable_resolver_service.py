#!/usr/bin/env python3
"""
VariableResolverService - 变量解析服务核心实现
提供变量的存储、检索、缓存和管理功能
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from threading import Lock
from collections import OrderedDict

from ..models import db, ExecutionVariable, VariableReference

logger = logging.getLogger(__name__)


class VariableManager:
    """
    变量管理器 - 管理单个执行的变量数据
    """

    def __init__(self, execution_id: str):
        self.execution_id = execution_id
        self._cache = OrderedDict()  # LRU缓存
        self._cache_lock = Lock()
        self._max_cache_size = 1000
        self._cache_dirty = False
        logger.info(f"初始化变量管理器: {execution_id}")

    def store_variable(
        self,
        variable_name: str,
        value: Any,
        source_step_index: int,
        source_api_method: str = None,
        source_api_params: Dict = None,
    ) -> bool:
        """存储变量到数据库和缓存"""
        try:
            with self._cache_lock:
                # 检测数据类型
                data_type = self._detect_data_type(value)

                # 检查是否已存在
                existing_var = ExecutionVariable.query.filter_by(
                    execution_id=self.execution_id, variable_name=variable_name
                ).first()

                if existing_var:
                    # 更新现有变量
                    existing_var.variable_value = json.dumps(value, ensure_ascii=False)
                    existing_var.data_type = data_type
                    existing_var.source_step_index = source_step_index
                    existing_var.source_api_method = source_api_method
                    existing_var.source_api_params = json.dumps(source_api_params or {})
                    existing_var.created_at = datetime.utcnow()
                else:
                    # 创建新变量
                    new_var = ExecutionVariable(
                        execution_id=self.execution_id,
                        variable_name=variable_name,
                        variable_value=json.dumps(value, ensure_ascii=False),
                        data_type=data_type,
                        source_step_index=source_step_index,
                        source_api_method=source_api_method,
                        source_api_params=json.dumps(source_api_params or {}),
                    )
                    db.session.add(new_var)

                db.session.commit()

                # 更新缓存
                self._update_cache(
                    variable_name,
                    {
                        "value": value,
                        "data_type": data_type,
                        "source_step_index": source_step_index,
                        "source_api_method": source_api_method,
                        "metadata": {
                            "created_at": datetime.utcnow().isoformat(),
                            "source_api_params": source_api_params or {},
                        },
                    },
                )

                logger.info(
                    f"变量存储成功: {variable_name} = {value} (类型: {data_type})"
                )
                return True

        except Exception as e:
            db.session.rollback()
            logger.error(f"变量存储失败: {variable_name}, 错误: {str(e)}")
            return False

    def get_variable(self, variable_name: str) -> Optional[Any]:
        """获取变量值（优先从缓存）"""
        try:
            with self._cache_lock:
                # 先检查缓存
                if variable_name in self._cache:
                    # LRU: 移动到末尾
                    cached_data = self._cache.pop(variable_name)
                    self._cache[variable_name] = cached_data
                    logger.debug(f"从缓存获取变量: {variable_name}")
                    return cached_data["value"]

                # 从数据库查询
                var = ExecutionVariable.query.filter_by(
                    execution_id=self.execution_id, variable_name=variable_name
                ).first()

                if var:
                    value = var.get_typed_value()
                    # 加入缓存
                    self._update_cache(
                        variable_name,
                        {
                            "value": value,
                            "data_type": var.data_type,
                            "source_step_index": var.source_step_index,
                            "source_api_method": var.source_api_method,
                            "metadata": {
                                "created_at": (
                                    var.created_at.isoformat()
                                    if var.created_at
                                    else None
                                ),
                                "source_api_params": (
                                    json.loads(var.source_api_params)
                                    if var.source_api_params
                                    else {}
                                ),
                            },
                        },
                    )
                    logger.debug(f"从数据库获取变量: {variable_name}")
                    return value

                logger.warning(f"变量不存在: {variable_name}")
                return None

        except Exception as e:
            logger.error(f"获取变量失败: {variable_name}, 错误: {str(e)}")
            return None

    def get_variable_metadata(self, variable_name: str) -> Optional[Dict]:
        """获取变量元数据"""
        try:
            with self._cache_lock:
                # 先检查缓存
                if variable_name in self._cache:
                    cached_data = self._cache[variable_name]
                    return {
                        "variable_name": variable_name,
                        "data_type": cached_data["data_type"],
                        "source_step_index": cached_data["source_step_index"],
                        "source_api_method": cached_data["source_api_method"],
                        "created_at": cached_data["metadata"]["created_at"],
                        "source_api_params": cached_data["metadata"][
                            "source_api_params"
                        ],
                    }

                # 从数据库查询
                var = ExecutionVariable.query.filter_by(
                    execution_id=self.execution_id, variable_name=variable_name
                ).first()

                if var:
                    return {
                        "variable_name": var.variable_name,
                        "data_type": var.data_type,
                        "source_step_index": var.source_step_index,
                        "source_api_method": var.source_api_method,
                        "created_at": (
                            var.created_at.isoformat() if var.created_at else None
                        ),
                        "source_api_params": (
                            json.loads(var.source_api_params)
                            if var.source_api_params
                            else {}
                        ),
                    }

                return None

        except Exception as e:
            logger.error(f"获取变量元数据失败: {variable_name}, 错误: {str(e)}")
            return None

    def list_variables(self) -> List[Dict]:
        """列出所有变量（包含元数据）"""
        try:
            variables = (
                ExecutionVariable.query.filter_by(execution_id=self.execution_id)
                .order_by(ExecutionVariable.source_step_index)
                .all()
            )

            result = []
            for var in variables:
                var_dict = {
                    "variable_name": var.variable_name,
                    "data_type": var.data_type,
                    "source_step_index": var.source_step_index,
                    "source_api_method": var.source_api_method,
                    "created_at": (
                        var.created_at.isoformat() if var.created_at else None
                    ),
                    "value": var.get_typed_value(),
                }
                result.append(var_dict)

            logger.info(f"列出变量成功: {len(result)} 个变量")
            return result

        except Exception as e:
            logger.error(f"列出变量失败: {str(e)}")
            return []

    def clear_variables(self) -> bool:
        """清理所有变量"""
        try:
            with self._cache_lock:
                # 删除数据库记录
                deleted_vars = ExecutionVariable.query.filter_by(
                    execution_id=self.execution_id
                ).delete()
                deleted_refs = VariableReference.query.filter_by(
                    execution_id=self.execution_id
                ).delete()

                db.session.commit()

                # 清理缓存
                self._cache.clear()

                logger.info(
                    f"已清理执行 {self.execution_id} 的变量: {deleted_vars} 个变量, {deleted_refs} 个引用"
                )
                return True

        except Exception as e:
            db.session.rollback()
            logger.error(f"清理变量失败: {str(e)}")
            return False

    def export_variables(self) -> Dict:
        """导出所有变量数据"""
        try:
            variables = self.list_variables()
            export_data = {
                "execution_id": self.execution_id,
                "export_time": datetime.utcnow().isoformat(),
                "variable_count": len(variables),
                "variables": variables,
            }

            logger.info(f"导出变量成功: {len(variables)} 个变量")
            return export_data

        except Exception as e:
            logger.error(f"导出变量失败: {str(e)}")
            return {}

    def _update_cache(self, variable_name: str, data: Dict):
        """更新缓存（LRU策略）"""
        # 如果变量已存在，先删除
        if variable_name in self._cache:
            del self._cache[variable_name]

        # 添加到末尾
        self._cache[variable_name] = data

        # 如果超过最大缓存大小，删除最旧的
        while len(self._cache) > self._max_cache_size:
            oldest_key, _ = self._cache.popitem(last=False)
            logger.debug(f"LRU缓存清理: {oldest_key}")

    def _detect_data_type(self, value: Any) -> str:
        """检测数据类型"""
        if isinstance(value, bool):
            return "boolean"
        elif isinstance(value, int):
            return "number"
        elif isinstance(value, float):
            return "number"
        elif isinstance(value, str):
            return "string"
        elif isinstance(value, list):
            return "array"
        elif isinstance(value, dict):
            return "object"
        elif value is None:
            return "null"
        else:
            return "string"  # 默认转为字符串

    def get_cache_stats(self) -> Dict:
        """获取缓存统计信息"""
        with self._cache_lock:
            return {
                "cache_size": len(self._cache),
                "max_cache_size": self._max_cache_size,
                "cache_hit_rate": "N/A",  # 可以通过计数器实现
                "execution_id": self.execution_id,
            }


class VariableManagerFactory:
    """
    变量管理器工厂类
    """

    _instances = {}
    _lock = Lock()

    @classmethod
    def get_manager(cls, execution_id: str) -> VariableManager:
        """获取变量管理器实例（单例模式）"""
        with cls._lock:
            if execution_id not in cls._instances:
                cls._instances[execution_id] = VariableManager(execution_id)
                logger.info(f"创建新的变量管理器实例: {execution_id}")

            return cls._instances[execution_id]

    @classmethod
    def cleanup_manager(cls, execution_id: str):
        """清理指定的变量管理器"""
        with cls._lock:
            if execution_id in cls._instances:
                manager = cls._instances[execution_id]
                manager.clear_variables()
                del cls._instances[execution_id]
                logger.info(f"已清理变量管理器: {execution_id}")

    @classmethod
    def cleanup_all(cls):
        """清理所有变量管理器"""
        with cls._lock:
            for execution_id in list(cls._instances.keys()):
                cls.cleanup_manager(execution_id)
            logger.info("已清理所有变量管理器")

    @classmethod
    def get_active_managers(cls) -> List[str]:
        """获取所有活跃的管理器ID"""
        with cls._lock:
            return list(cls._instances.keys())

    @classmethod
    def get_factory_stats(cls) -> Dict:
        """获取工厂统计信息"""
        with cls._lock:
            return {
                "active_managers": len(cls._instances),
                "manager_ids": list(cls._instances.keys()),
            }


# 服务层接口函数
def get_variable_manager(execution_id: str) -> VariableManager:
    """获取变量管理器的便捷函数"""
    return VariableManagerFactory.get_manager(execution_id)


def cleanup_execution_variables(execution_id: str):
    """清理指定执行的变量数据"""
    VariableManagerFactory.cleanup_manager(execution_id)
