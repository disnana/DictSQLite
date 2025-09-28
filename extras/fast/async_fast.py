"""(互換ラッパ) 旧配置との互換のためのフォワーダ。

実装本体は `dictsqlite_fast.async_fast` にあります。
推奨インポート:
    from dictsqlite_fast import AsyncFastDictSQLite
"""
from __future__ import annotations

from dictsqlite_fast.async_fast import AsyncFastDictSQLite  # noqa: F401
