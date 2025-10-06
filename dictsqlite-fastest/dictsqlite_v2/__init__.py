"""DictSQLite-v2.0 - 最高性能を目指す統合版

Dictsqlite-Fastest と Beta 版の最良部分を統合し、
継続的なパフォーマンス最適化を実現する自律開発システム。
"""

__version__ = '2.0.0'

try:
    from .core import DictSQLiteV2, AsyncDictSQLiteV2
except ImportError:
    # Fallback for direct script execution
    from core import DictSQLiteV2, AsyncDictSQLiteV2

__all__ = [
    'DictSQLiteV2',
    'AsyncDictSQLiteV2',
]
