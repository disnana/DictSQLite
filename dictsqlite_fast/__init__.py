"""Compatibility wrapper package.

実装本体は `extras.fast.dictsqlite_fast` に集約されました。
ユーザは引き続き:
    from dictsqlite_fast import FastDictSQLite, AsyncFastDictSQLite
で利用可能です。
"""
from __future__ import annotations

from extras.fast.dictsqlite_fast import FastDictSQLite, AsyncFastDictSQLite  # type: ignore  # noqa: F401,E402
from extras.fast.dictsqlite_fast import __version__  # type: ignore  # noqa: F401,E402

__all__ = ["FastDictSQLite", "AsyncFastDictSQLite", "__version__"]

