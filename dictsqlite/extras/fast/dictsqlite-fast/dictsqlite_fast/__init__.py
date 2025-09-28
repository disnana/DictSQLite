"""dictsqlite-fast: APSW + asyncio を用いた高速/堅牢 DictSQLite 実装.

公開API:
    from dictsqlite_fast import FastDictSQLite, AsyncFastDictSQLite

APSW が未導入の場合、クラス初期化時に ImportError を送出します。
"""
from __future__ import annotations

__all__ = ["FastDictSQLite", "AsyncFastDictSQLite"]

try:  # 実体インポート
    from .fast import FastDictSQLite  # type: ignore  # noqa: F401
    from .async_fast import AsyncFastDictSQLite  # type: ignore  # noqa: F401
except Exception as _e:  # noqa: BLE001
    class _MissingAPSW:  # pylint: disable=too-few-public-methods
        def __init__(self, *_, **__):
            raise ImportError(
                "dictsqlite-fast を利用するには 'apsw' が必要です. "
                "インストール例: pip install dictsqlite-fast"
            ) from _e

    class FastDictSQLite(_MissingAPSW):  # type: ignore
        pass

    class AsyncFastDictSQLite(_MissingAPSW):  # type: ignore
        pass

