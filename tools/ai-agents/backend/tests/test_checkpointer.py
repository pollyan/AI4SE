"""
共享 Checkpointer 模块单元测试

测试 shared/checkpointer.py 中的单例模式和 reset 功能。
"""



class TestGetCheckpointer:
    """测试 get_checkpointer 函数"""
    
    def test_returns_memory_saver_instance(self):
        """应返回 MemorySaver 实例"""
        from backend.agents.shared.checkpointer import get_checkpointer, reset_checkpointer
        from langgraph.checkpoint.memory import MemorySaver
        
        reset_checkpointer()
        checkpointer = get_checkpointer()
        
        assert isinstance(checkpointer, MemorySaver)
    
    def test_singleton_returns_same_instance(self):
        """多次调用应返回同一个实例（单例模式）"""
        from backend.agents.shared.checkpointer import get_checkpointer, reset_checkpointer
        
        reset_checkpointer()
        
        first = get_checkpointer()
        second = get_checkpointer()
        third = get_checkpointer()
        
        assert first is second
        assert second is third
    
    def test_different_modules_get_same_instance(self):
        """不同模块导入应获得同一个实例"""
        from backend.agents.shared.checkpointer import get_checkpointer, reset_checkpointer
        from backend.agents.shared import get_checkpointer as get_checkpointer_from_init
        
        reset_checkpointer()
        
        direct_instance = get_checkpointer()
        init_instance = get_checkpointer_from_init()
        
        assert direct_instance is init_instance


class TestResetCheckpointer:
    """测试 reset_checkpointer 函数"""
    
    def test_reset_creates_new_instance(self):
        """reset 后应创建新实例"""
        from backend.agents.shared.checkpointer import get_checkpointer, reset_checkpointer
        
        reset_checkpointer()
        first = get_checkpointer()
        
        reset_checkpointer()
        second = get_checkpointer()
        
        assert first is not second
    
    def test_reset_clears_global_state(self):
        """reset 应清除全局状态"""
        from backend.agents.shared import checkpointer
        
        checkpointer.get_checkpointer()
        assert checkpointer._checkpointer is not None
        
        checkpointer.reset_checkpointer()
        assert checkpointer._checkpointer is None


class TestCheckpointerExport:
    """测试 shared/__init__.py 的导出"""
    
    def test_get_checkpointer_exported(self):
        """get_checkpointer 应从 shared 模块导出"""
        from backend.agents.shared import get_checkpointer
        
        assert callable(get_checkpointer)
    
    def test_reset_checkpointer_exported(self):
        """reset_checkpointer 应从 shared 模块导出"""
        from backend.agents.shared import reset_checkpointer
        
        assert callable(reset_checkpointer)
