"""dictsqlite-fast: APSW ベース高速/互換版 DictSQLite

インポート例:
    from dictsqlite_fast import FastDictSQLite, AsyncFastDictSQLite
"""
from __future__ import annotations

__all__ = ["FastDictSQLite", "AsyncFastDictSQLite", "__version__"]

__version__ = "0.1.0"

from .fast import FastDictSQLite  # noqa: E402,F401
try:
    from .async_fast import AsyncFastDictSQLite  # noqa: E402,F401
except Exception:  # pragma: no cover
    # 非同期機能が壊れている/依存欠如時でも同期版は利用可能
    class AsyncFastDictSQLite:  # type: ignore
        def __init__(self, *_, **__):  # noqa: D401
            raise ImportError("AsyncFastDictSQLite 利用には 'apsw' と Python >=3.9 が必要です")
