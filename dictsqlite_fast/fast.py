"""Forwarder module.

実装は `extras.fast.dictsqlite_fast.fast` に移動しました。
このモジュールは後方互換のため残され、直接インポートしても同等のクラスを提供します。
"""
from __future__ import annotations
from extras.fast.dictsqlite_fast.fast import FastDictSQLite  # type: ignore  # noqa: F401,E402
__all__ = ["FastDictSQLite"]
