from __future__ import annotations
"""Backward compatibility stub.

実際の実装は同ディレクトリ fast.py に統合されています。
外部コードは引き続き:
    from extras.fast.dictsqlite_fast.async_fast import AsyncFastDictSQLite
で利用可能です。
"""
from .fast import AsyncFastDictSQLite  # noqa: F401
__all__ = ["AsyncFastDictSQLite"]
