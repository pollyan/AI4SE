"""
VariableResolverService 单元测试
测试变量管理器的存储、检索、缓存和 LRU 淘汰功能
"""

import pytest
import json
from datetime import datetime
from unittest.mock import patch, MagicMock, PropertyMock
from collections import OrderedDict

from backend.services.variable_resolver_service import (
    VariableManager,
    VariableManagerFactory,
    get_variable_manager,
    cleanup_execution_variables,
)
from backend.models import db, ExecutionVariable, VariableReference


class TestVariableManagerInit:
    """测试 VariableManager 初始化"""

    def test_init_with_execution_id(self, app, db_session):
        """测试使用执行ID初始化"""
        # Given: 一个执行ID
        execution_id = "test-exec-001"

        # When: 创建 VariableManager
        manager = VariableManager(execution_id)

        # Then: 正确初始化
        assert manager.execution_id == execution_id
        assert manager._max_cache_size == 1000
        assert len(manager._cache) == 0

    def test_init_has_lru_cache(self, app, db_session):
        """测试初始化 LRU 缓存结构"""
        # Given: 一个执行ID
        execution_id = "test-exec-002"

        # When: 创建 VariableManager
        manager = VariableManager(execution_id)

        # Then: 使用 OrderedDict 作为 LRU 缓存
        assert isinstance(manager._cache, OrderedDict)


class TestVariableManagerStoreVariable:
    """测试 store_variable 方法"""

    def test_store_string_variable(self, app, db_session):
        """测试存储字符串变量"""
        # Given: VariableManager 实例
        manager = VariableManager("test-exec-store-001")

        # When: 存储字符串变量
        result = manager.store_variable(
            variable_name="test_var",
            value="test_value",
            source_step_index=0,
            source_api_method="aiQuery"
        )

        # Then: 存储成功
        assert result is True

    def test_store_number_variable(self, app, db_session):
        """测试存储数字变量"""
        # Given: VariableManager 实例
        manager = VariableManager("test-exec-store-002")

        # When: 存储数字变量
        result = manager.store_variable(
            variable_name="count",
            value=42,
            source_step_index=0,
            source_api_method="aiNumber"
        )

        # Then: 存储成功
        assert result is True

    def test_store_object_variable(self, app, db_session):
        """测试存储对象变量"""
        # Given: VariableManager 实例
        manager = VariableManager("test-exec-store-003")

        # When: 存储对象变量
        result = manager.store_variable(
            variable_name="user_data",
            value={"name": "Alice", "age": 30},
            source_step_index=1,
            source_api_method="aiQuery"
        )

        # Then: 存储成功
        assert result is True

    def test_store_array_variable(self, app, db_session):
        """测试存储数组变量"""
        # Given: VariableManager 实例
        manager = VariableManager("test-exec-store-004")

        # When: 存储数组变量
        result = manager.store_variable(
            variable_name="items",
            value=["item1", "item2", "item3"],
            source_step_index=2,
            source_api_method="aiQuery"
        )

        # Then: 存储成功
        assert result is True

    def test_store_boolean_variable(self, app, db_session):
        """测试存储布尔变量"""
        # Given: VariableManager 实例
        manager = VariableManager("test-exec-store-005")

        # When: 存储布尔变量
        result = manager.store_variable(
            variable_name="is_valid",
            value=True,
            source_step_index=0,
            source_api_method="aiBoolean"
        )

        # Then: 存储成功
        assert result is True

    def test_store_updates_existing_variable(self, app, db_session):
        """测试更新已存在的变量"""
        # Given: 已存储一个变量
        manager = VariableManager("test-exec-store-006")
        manager.store_variable(
            variable_name="counter",
            value=1,
            source_step_index=0,
            source_api_method="set_variable"
        )

        # When: 更新同一个变量
        result = manager.store_variable(
            variable_name="counter",
            value=2,
            source_step_index=1,
            source_api_method="set_variable"
        )

        # Then: 更新成功
        assert result is True
        assert manager.get_variable("counter") == 2

    def test_store_variable_updates_cache(self, app, db_session):
        """测试存储变量更新缓存"""
        # Given: VariableManager 实例
        manager = VariableManager("test-exec-store-007")

        # When: 存储变量
        manager.store_variable(
            variable_name="cached_var",
            value="cached_value",
            source_step_index=0,
            source_api_method="test"
        )

        # Then: 变量在缓存中
        assert "cached_var" in manager._cache
        assert manager._cache["cached_var"]["value"] == "cached_value"


class TestVariableManagerGetVariable:
    """测试 get_variable 方法"""

    def test_get_variable_from_cache(self, app, db_session):
        """测试从缓存获取变量"""
        # Given: 已存储的变量
        manager = VariableManager("test-exec-get-001")
        manager.store_variable(
            variable_name="cache_test",
            value="cached_value",
            source_step_index=0,
            source_api_method="test"
        )

        # When: 获取变量
        value = manager.get_variable("cache_test")

        # Then: 返回正确的值
        assert value == "cached_value"

    def test_get_variable_from_database(self, app, db_session):
        """测试从数据库获取变量（缓存未命中）"""
        # Given: 直接在数据库中创建变量
        execution_id = "test-exec-get-002"
        manager = VariableManager(execution_id)

        # 先存储变量（会同时写入数据库和缓存）
        manager.store_variable(
            variable_name="db_var",
            value="db_value",
            source_step_index=0,
            source_api_method="test"
        )

        # 清空缓存模拟缓存未命中
        manager._cache.clear()

        # When: 获取变量
        value = manager.get_variable("db_var")

        # Then: 从数据库加载并返回
        assert value == "db_value"

    def test_get_variable_not_found(self, app, db_session):
        """测试获取不存在的变量"""
        # Given: VariableManager 实例
        manager = VariableManager("test-exec-get-003")

        # When: 获取不存在的变量
        value = manager.get_variable("non_existent")

        # Then: 返回 None
        assert value is None

    def test_get_variable_updates_lru_order(self, app, db_session):
        """测试获取变量更新 LRU 顺序"""
        # Given: 存储多个变量
        manager = VariableManager("test-exec-get-004")
        manager.store_variable(variable_name="var1", value="v1", source_step_index=0, source_api_method="test")
        manager.store_variable(variable_name="var2", value="v2", source_step_index=0, source_api_method="test")
        manager.store_variable(variable_name="var3", value="v3", source_step_index=0, source_api_method="test")

        # When: 访问 var1
        manager.get_variable("var1")

        # Then: var1 应该在缓存的最后（最近访问）
        keys = list(manager._cache.keys())
        assert keys[-1] == "var1"


class TestVariableManagerLRUCache:
    """测试 LRU 缓存行为"""

    def test_lru_cache_eviction(self, app, db_session):
        """测试 LRU 缓存淘汰"""
        # Given: 缓存大小为 3
        manager = VariableManager("test-exec-lru-001")
        manager._max_cache_size = 3

        # When: 存储 4 个变量
        manager.store_variable(variable_name="var1", value="v1", source_step_index=0, source_api_method="test")
        manager.store_variable(variable_name="var2", value="v2", source_step_index=0, source_api_method="test")
        manager.store_variable(variable_name="var3", value="v3", source_step_index=0, source_api_method="test")
        manager.store_variable(variable_name="var4", value="v4", source_step_index=0, source_api_method="test")

        # Then: var1 被淘汰
        assert "var1" not in manager._cache
        assert "var4" in manager._cache

    def test_lru_cache_access_updates_order(self, app, db_session):
        """测试访问更新 LRU 顺序"""
        # Given: 缓存大小为 3，存储 3 个变量
        manager = VariableManager("test-exec-lru-002")
        manager._max_cache_size = 3
        manager.store_variable(variable_name="a", value="1", source_step_index=0, source_api_method="test")
        manager.store_variable(variable_name="b", value="2", source_step_index=0, source_api_method="test")
        manager.store_variable(variable_name="c", value="3", source_step_index=0, source_api_method="test")

        # When: 访问变量 "a"，然后存储新变量
        manager.get_variable("a")
        manager.store_variable(variable_name="d", value="4", source_step_index=0, source_api_method="test")

        # Then: "b" 被淘汰（因为 "a" 被访问后移到了最后）
        assert "b" not in manager._cache
        assert "a" in manager._cache


class TestVariableManagerListVariables:
    """测试 list_variables 方法"""

    def test_list_variables_empty(self, app, db_session):
        """测试列出空变量列表"""
        # Given: 没有变量的管理器
        manager = VariableManager("test-exec-list-001")

        # When: 列出变量
        variables = manager.list_variables()

        # Then: 返回空列表
        assert variables == []

    def test_list_variables_with_data(self, app, db_session):
        """测试列出多个变量"""
        # Given: 存储多个变量
        manager = VariableManager("test-exec-list-002")
        manager.store_variable(variable_name="var1", value="value1", source_step_index=0, source_api_method="test")
        manager.store_variable(variable_name="var2", value="value2", source_step_index=1, source_api_method="test")

        # When: 列出变量
        variables = manager.list_variables()

        # Then: 返回所有变量
        assert len(variables) == 2
        var_names = [v["variable_name"] for v in variables]
        assert "var1" in var_names
        assert "var2" in var_names

    def test_list_variables_includes_metadata(self, app, db_session):
        """测试列出变量包含元数据"""
        # Given: 存储一个变量
        manager = VariableManager("test-exec-list-003")
        manager.store_variable(
            variable_name="meta_var",
            value=123,
            source_step_index=5,
            source_api_method="aiNumber"
        )

        # When: 列出变量
        variables = manager.list_variables()

        # Then: 包含元数据
        var = next((v for v in variables if v["variable_name"] == "meta_var"), None)
        assert var is not None
        assert var["data_type"] == "number"
        assert var["source_step_index"] == 5
        assert var["source_api_method"] == "aiNumber"


class TestVariableManagerClearVariables:
    """测试 clear_variables 方法"""

    def test_clear_variables_removes_all(self, app, db_session):
        """测试清除所有变量"""
        # Given: 存储多个变量
        manager = VariableManager("test-exec-clear-001")
        manager.store_variable(variable_name="v1", value="1", source_step_index=0, source_api_method="test")
        manager.store_variable(variable_name="v2", value="2", source_step_index=0, source_api_method="test")

        # When: 清除变量
        result = manager.clear_variables()

        # Then: 所有变量被清除
        assert result is True
        assert manager.list_variables() == []
        assert len(manager._cache) == 0


class TestVariableManagerExportVariables:
    """测试 export_variables 方法"""

    def test_export_variables_structure(self, app, db_session):
        """测试导出变量数据结构"""
        # Given: 存储变量
        manager = VariableManager("test-exec-export-001")
        manager.store_variable(variable_name="export_test", value="export_value", source_step_index=0, source_api_method="test")

        # When: 导出变量
        export_data = manager.export_variables()

        # Then: 包含正确的结构
        assert "execution_id" in export_data
        assert "export_time" in export_data
        assert "variable_count" in export_data
        assert "variables" in export_data
        assert export_data["variable_count"] == 1


class TestVariableManagerDetectDataType:
    """测试 _detect_data_type 方法"""

    def test_detect_string_type(self, app, db_session):
        """测试检测字符串类型"""
        manager = VariableManager("test-exec-type-001")
        assert manager._detect_data_type("hello") == "string"

    def test_detect_integer_type(self, app, db_session):
        """测试检测整数类型"""
        manager = VariableManager("test-exec-type-002")
        assert manager._detect_data_type(42) == "number"

    def test_detect_float_type(self, app, db_session):
        """测试检测浮点数类型"""
        manager = VariableManager("test-exec-type-003")
        assert manager._detect_data_type(3.14) == "number"

    def test_detect_boolean_type(self, app, db_session):
        """测试检测布尔类型"""
        manager = VariableManager("test-exec-type-004")
        assert manager._detect_data_type(True) == "boolean"
        assert manager._detect_data_type(False) == "boolean"

    def test_detect_array_type(self, app, db_session):
        """测试检测数组类型"""
        manager = VariableManager("test-exec-type-005")
        assert manager._detect_data_type([1, 2, 3]) == "array"

    def test_detect_object_type(self, app, db_session):
        """测试检测对象类型"""
        manager = VariableManager("test-exec-type-006")
        assert manager._detect_data_type({"key": "value"}) == "object"

    def test_detect_null_type(self, app, db_session):
        """测试检测 null 类型"""
        manager = VariableManager("test-exec-type-007")
        assert manager._detect_data_type(None) == "null"


class TestVariableManagerGetCacheStats:
    """测试 get_cache_stats 方法"""

    def test_get_cache_stats(self, app, db_session):
        """测试获取缓存统计信息"""
        # Given: 存储一些变量
        manager = VariableManager("test-exec-stats-001")
        manager.store_variable(variable_name="s1", value="v1", source_step_index=0, source_api_method="test")
        manager.store_variable(variable_name="s2", value="v2", source_step_index=0, source_api_method="test")

        # When: 获取缓存统计
        stats = manager.get_cache_stats()

        # Then: 返回正确的统计信息
        assert stats["cache_size"] == 2
        assert stats["max_cache_size"] == 1000
        assert stats["execution_id"] == "test-exec-stats-001"


class TestVariableManagerGetVariableMetadata:
    """测试 get_variable_metadata 方法"""

    def test_get_variable_metadata_success(self, app, db_session):
        """测试获取变量元数据"""
        # Given: 存储变量
        manager = VariableManager("test-exec-meta-001")
        manager.store_variable(
            variable_name="meta_test",
            value="test_value",
            source_step_index=3,
            source_api_method="aiQuery"
        )

        # When: 获取元数据
        metadata = manager.get_variable_metadata("meta_test")

        # Then: 返回正确的元数据
        assert metadata is not None
        assert metadata["variable_name"] == "meta_test"
        assert metadata["data_type"] == "string"
        assert metadata["source_step_index"] == 3
        assert metadata["source_api_method"] == "aiQuery"

    def test_get_variable_metadata_not_found(self, app, db_session):
        """测试获取不存在变量的元数据"""
        # Given: VariableManager 实例
        manager = VariableManager("test-exec-meta-002")

        # When: 获取不存在的变量元数据
        metadata = manager.get_variable_metadata("non_existent")

        # Then: 返回 None
        assert metadata is None


class TestVariableManagerFactory:
    """测试 VariableManagerFactory 类"""

    def test_get_manager_creates_new(self, app, db_session):
        """测试工厂创建新的管理器"""
        # Given: 一个执行ID
        execution_id = "factory-test-001"

        # When: 获取管理器
        manager = VariableManagerFactory.get_manager(execution_id)

        # Then: 返回新的管理器实例
        assert manager is not None
        assert manager.execution_id == execution_id

    def test_get_manager_returns_same_instance(self, app, db_session):
        """测试工厂返回相同实例（单例）"""
        # Given: 同一个执行ID
        execution_id = "factory-test-002"

        # When: 多次获取管理器
        manager1 = VariableManagerFactory.get_manager(execution_id)
        manager2 = VariableManagerFactory.get_manager(execution_id)

        # Then: 返回同一个实例
        assert manager1 is manager2

    def test_cleanup_manager(self, app, db_session):
        """测试清理管理器"""
        # Given: 创建一个管理器
        execution_id = "factory-test-003"
        VariableManagerFactory.get_manager(execution_id)

        # When: 清理管理器
        VariableManagerFactory.cleanup_manager(execution_id)

        # Then: 管理器被移除
        assert execution_id not in VariableManagerFactory._instances

    def test_get_active_managers(self, app, db_session):
        """测试获取活跃管理器列表"""
        # Given: 创建多个管理器
        VariableManagerFactory.get_manager("active-1")
        VariableManagerFactory.get_manager("active-2")

        # When: 获取活跃管理器列表
        active = VariableManagerFactory.get_active_managers()

        # Then: 包含所有活跃的管理器ID
        assert "active-1" in active
        assert "active-2" in active

    def test_get_factory_stats(self, app, db_session):
        """测试获取工厂统计信息"""
        # Given: 创建一些管理器
        VariableManagerFactory.get_manager("stats-1")
        VariableManagerFactory.get_manager("stats-2")

        # When: 获取统计信息
        stats = VariableManagerFactory.get_factory_stats()

        # Then: 返回正确的统计
        assert stats["active_managers"] >= 2
        assert "stats-1" in stats["manager_ids"]
        assert "stats-2" in stats["manager_ids"]


class TestConvenienceFunctions:
    """测试便捷函数"""

    def test_get_variable_manager_function(self, app, db_session):
        """测试 get_variable_manager 便捷函数"""
        # Given: 一个执行ID
        execution_id = "convenience-test-001"

        # When: 调用便捷函数
        manager = get_variable_manager(execution_id)

        # Then: 返回正确的管理器
        assert manager is not None
        assert manager.execution_id == execution_id

    def test_cleanup_execution_variables_function(self, app, db_session):
        """测试 cleanup_execution_variables 便捷函数"""
        # Given: 创建一个管理器
        execution_id = "convenience-test-002"
        get_variable_manager(execution_id)

        # When: 调用清理函数
        cleanup_execution_variables(execution_id)

        # Then: 管理器被清理
        assert execution_id not in VariableManagerFactory._instances