"""Tools 共享模块"""

from .database import get_database_config
from .config import SharedConfig

__all__ = ['get_database_config', 'SharedConfig']