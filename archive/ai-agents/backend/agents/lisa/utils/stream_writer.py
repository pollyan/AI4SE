def get_robust_stream_writer(config=None):
    """
    Robustly get the stream writer from config by patching Python 3.9's missing contextvars.
    """
    if config:
        try:
            from langchain_core.runnables.config import var_child_runnable_config
            # 核心修复: 强制在当前线程中恢复 ContextVar，修复 Python 3.9 下 ThreadPool 丢失上下文的问题
            var_child_runnable_config.set(config)
        except ImportError:
            pass

    try:
        from langgraph.config import get_stream_writer
        return get_stream_writer()
    except Exception:
        return None
