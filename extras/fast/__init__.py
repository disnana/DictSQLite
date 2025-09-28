"""dictsqlite-fast shim module (development layout).

This directory name contains a hyphen so Python cannot import it as a package
normally. We keep this __init__ only so that pytest test collection does not
crash. Actual implementation lives in the inner package `dictsqlite_fast`.

End users should install / import:
    import dictsqlite_fast

During source tree tests we simply try to import the inner package and expose
its symbols. On failure we provide lightweight stubs so that test collection
continues (tests will then fail gracefully when used).
"""
from __future__ import annotations

import importlib

__all__ = ["FastDictSQLite", "AsyncFastDictSQLite", "__version__"]

try:
    _pkg = importlib.import_module("dictsqlite_fast")
    FastDictSQLite = getattr(_pkg, "FastDictSQLite")  # type: ignore
    AsyncFastDictSQLite = getattr(_pkg, "AsyncFastDictSQLite", None)  # type: ignore
    __version__ = getattr(_pkg, "__version__", "0.0")
except Exception:  # noqa: BLE001
    __version__ = "0.0.dev"

    class FastDictSQLite:  # type: ignore
        def __init__(self, *_, **__):  # noqa: D401
            raise ImportError("dictsqlite_fast implementation not found in source tree")

    class AsyncFastDictSQLite(FastDictSQLite):  # type: ignore
        pass
