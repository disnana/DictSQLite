"""dictsqlite-fast (rebuilt)

fast.py に同期/非同期実装を統合。
利用例:
    from extras.fast.dictsqlite_fast import FastDictSQLite, AsyncFastDictSQLite
またはルートのフォワーダ:
    from dictsqlite_fast import FastDictSQLite
を継続利用可能。
"""
from __future__ import annotations

__all__ = ["FastDictSQLite", "AsyncFastDictSQLite", "__version__"]
from .fast import FastDictSQLite, AsyncFastDictSQLite, __version__  # noqa: F401,E402
