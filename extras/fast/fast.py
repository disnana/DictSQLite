"""(互換ラッパ) このファイルは旧構成互換のため残されています。

実際の実装はサブパッケージ `dictsqlite_fast.fast` に移動済みです。
推奨:
    from dictsqlite_fast import FastDictSQLite
"""
from __future__ import annotations

from dictsqlite_fast.fast import FastDictSQLite  # noqa: F401
