"""
DictSQLite v4.0 Python Wrapper

High-performance wrapper with enhanced security features
"""

try:
    from dictsqlite._native import DictSQLiteV4 as _NativeDictSQLiteV4
    from dictsqlite._native import AsyncDictSQLite as _NativeAsyncDictSQLite
    _NATIVE_AVAILABLE = True
except ImportError:
    _NATIVE_AVAILABLE = False
    _NativeDictSQLiteV4 = None
    _NativeAsyncDictSQLite = None
import logging
# Import safe_pickle from the local "modules" package. When pytest imports this
# __init__ as a top-level module (no package context), a relative import fails
# with "attempted relative import with no known parent package". Use a robust
# strategy: try relative import first, then fall back to importing
# 'dictsqlite.modules.safe_pickle' (works when package is installed), and finally
# try 'modules.safe_pickle' as a last resort (works when current dir is on sys.path).
try:
    from .modules import safe_pickle  # normal package-relative import
except Exception:
    import importlib
    try:
        safe_pickle = importlib.import_module('dictsqlite.modules.safe_pickle')
    except Exception:
        try:
            safe_pickle = importlib.import_module('modules.safe_pickle')
        except Exception:
            raise

logger = logging.getLogger(__name__)


class Modes:
    """Persistence, Storage, and Table Modes"""

    # Persistence Modes
    MEMORY = "memory"          # All data in memory, no persistence
    LAZY = "lazy"              # Data persisted on flush or close
    WRITETHROUGH = "writethrough"  # Data persisted immediately on write

    # Storage Modes
    PICKLE = "pickle"          # Use Python pickle for serialization
    JSONB = "jsonb"            # Use JSONB for serialization (PostgreSQL compatible)
    BYTES = "bytes"
    JSON = "json"              # Use JSON for serialization

    # Table Modes
    TABLE_PREFIX = "prefix"    # Use key prefixes for table isolation (default)
    TABLE_SEPARATE = "separate"  # Use separate SQLite tables for complete isolation


class DictSQLite:
    """
    High-performance DictSQLite v4.0 with security features

    Features:
    - 100M+ ops/sec with lock-free concurrent hashmap
    - Optional AES-256-GCM encryption
    - Optional Safe Pickle validation
    - SQL injection protection

    Compatible with DictSQLite v1/v2/v3 API:
    - Dict-like operations: `db['key'] = 'value'`, `db.get('key')`, etc.
    - Context manager support: `with DictSQLite(...) as db:`
    - Iteration: `for key in db.keys():`
    """

    def __init__(
        self,
        db_path,
        hot_capacity=1_000_000,
        enable_async=True,
        persist_mode="writethrough",
        storage_mode="pickle",
        table_name="main",
        encryption_password=None,
        enable_safe_pickle=False,
        safe_pickle_allowed_modules=None,
        buffer_size=100,
        encoding='utf-8',
        table_mode="prefix",
        pool_size=20
    ):
        """
        Initialize DictSQLite v4.0

        Args:
            db_path: Path to database file
            hot_capacity: Maximum entries in hot tier (in-memory)
            enable_async: Enable async background flush
            persist_mode: "memory", "lazy", or "writethrough"
            storage_mode: "pickle" or "jsonb" (default: "pickle")
            table_name: Table name for storage (default: "main")
            encryption_password: Password for AES-256-GCM encryption (optional)
            enable_safe_pickle: Enable Safe Pickle validation (optional)
            safe_pickle_allowed_modules: List of module prefixes to allow in Safe Pickle (optional)
                                        Example: ["myapp", "mylib"] to allow myapp.* and mylib.*
            buffer_size: Buffer size for async operations (default: 100)
            encoding: Character encoding for string conversion (default: 'utf-8')
                     Strings are automatically encoded using this encoding
            table_mode: Table isolation mode (default: "prefix")
                       - "prefix": Use key prefixes for table isolation (current behavior)
                       - "separate": Use separate SQLite tables for complete isolation
            pool_size: Connection pool size for SQLite (default: 20)
                      Determines the maximum number of concurrent database connections
        """
        if not _NATIVE_AVAILABLE:
            raise RuntimeError(
                "DictSQLite native extension not available. "
                "Please build it using: cd dictsqlite && maturin build --release"
            )

        # For writethrough mode, use buffer_size=1 by default for immediate persistence
        # unless explicitly specified otherwise
        if persist_mode == "writethrough" and buffer_size == 100:
            buffer_size = 1

        self._encoding = encoding
        self._db = _NativeDictSQLiteV4(
            db_path,
            hot_capacity,
            enable_async,
            persist_mode,
            storage_mode,
            table_name,
            encryption_password,
            enable_safe_pickle,
            safe_pickle_allowed_modules,
            buffer_size,
            table_mode,
            pool_size
        )
        # Python-side safe_pickle control: when native extension isn't performing
        # safe unpickle checks (or when we prefer Python-side checking), honor
        # enable_safe_pickle here and keep allowed module prefixes for use
        # when deserializing values returned from the native layer.
        self._enable_safe_pickle = bool(enable_safe_pickle)
        if safe_pickle_allowed_modules is None:
            # default to allowing this package's modules
            self._safe_pickle_allowed_modules = ("dictsqlite",)
        else:
            self._safe_pickle_allowed_modules = tuple(safe_pickle_allowed_modules)
        self._closed = False

    def __getitem__(self, key):
        """Get value by key

        This delegates to the Rust implementation which automatically unpickles
        the data. When safe_pickle is enabled, the Rust side uses safe_loads
        for validation.
        """
        # Call Rust's __getitem__ which properly deserializes the data
        return self._db.__getitem__(str(key))

    def __setitem__(self, key, value):
        """Set value for key - Rust handles serialization automatically"""
        logger.debug(f"__setitem__ called with key={key}, value type={type(value)}")

        # If Safe Pickle is enabled, validate pickle-able values at write-time
        # Only validate if value would be pickled (not strings in pickle mode)
        if self._enable_safe_pickle and not isinstance(value, str):
            import pickle
            # Try to pickle it to validate
            try:
                pickled = pickle.dumps(value)
                safe_pickle.safe_loads(
                    pickled,
                    allowed_module_prefixes=self._safe_pickle_allowed_modules,
                )
            except pickle.UnpicklingError as e:
                logger.warning("Safe pickle rejected value for key=%s", key)
                # Wrap UnpicklingError as ValueError for consistent API
                raise ValueError(f"Safe pickle validation failed: {e}")
            except Exception:
                logger.warning("Safe pickle rejected value for key=%s", key)
                # Re-raise so callers/tests see an exception
                raise

        # Let Rust handle all serialization
        self._db.__setitem__(str(key), value)

    def __delitem__(self, key):
        """Delete key"""
        self._db.delete(str(key))

    def __contains__(self, key):
        """Check if key exists"""
        return self._db.contains(str(key))

    def __len__(self):
        """Get number of entries"""
        return self._db.len()

    def get(self, key, default=None):
        """Get value with default"""
        try:
            # Use Rust's __getitem__ to properly deserialize
            return self._db.__getitem__(str(key))
        except KeyError:
            return default

    def keys(self):
        """Get all keys"""
        return self._db.keys()

    def values(self):
        """Get all values"""
        # Use __getitem__ to properly deserialize each value
        return [self[k] for k in self.keys()]

    def items(self):
        """Get all items as (key, value) tuples"""
        # Use __getitem__ to properly deserialize each value
        return [(k, self[k]) for k in self.keys()]

    def update(self, other=None, **kwargs):
        """Update from dict or kwargs"""
        if other is not None:
            if hasattr(other, 'items'):
                for key, value in other.items():
                    self[key] = value
            else:
                for key, value in other:
                    self[key] = value
        for key, value in kwargs.items():
            self[key] = value

    def setdefault(self, key, default=None):
        """Set default if key doesn't exist"""
        if key not in self:
            self[key] = default
        return self[key]

    def pop(self, key, *default):
        """Remove and return value
        
        Args:
            key: Key to remove
            *default: Optional default value if key doesn't exist
        
        Returns:
            Value for the key, or default if key doesn't exist
        
        Raises:
            KeyError: If key doesn't exist and no default is provided
        """
        try:
            value = self[key]
            del self[key]
            return value
        except KeyError:
            if default:
                return default[0]
            raise  # Raise KeyError if no default is provided

    def __iter__(self):
        """Iterate over keys"""
        return iter(self.keys())

    def __eq__(self, other):
        """Compare with dict or another DictSQLite instance"""
        if isinstance(other, dict):
            return dict(self.items()) == other
        elif isinstance(other, DictSQLite):
            return dict(self.items()) == dict(other.items())
        return False

    def __repr__(self):
        """String representation: show all dict-like contents"""
        try:
            items = dict(self.items())
            return f"{dict(items)}"
        except Exception as e:
            logger.warning(f"Exception while printing dict: {e}")
            return "{}"

    def clear(self):
        """Clear all data"""
        self._db.clear()

    def table(self, table_name):
        """Get a table proxy for accessing a specific table"""
        return self._db.table(table_name)

    def bulk_insert(self, items):
        """Bulk insert items - uses __setitem__ for proper serialization"""
        if isinstance(items, dict):
            items = items.items()

        for key, value in items:
            self[key] = value

    def stats(self):
        """Get performance statistics"""
        return self._db.stats()

    def flush(self):
        """Flush hot tier to storage"""
        self._db.flush()

    def batch_get(self, keys):
        """Batch get multiple keys at once
        
        Args:
            keys: List of keys to retrieve
            
        Returns:
            Dict mapping keys to values (missing keys are omitted)
        """
        return self._db.batch_get([str(k) for k in keys])

    def batch_set(self, items):
        """Batch set multiple key-value pairs at once
        
        Args:
            items: List of (key, value) tuples or dict
        """
        if isinstance(items, dict):
            items = items.items()
        
        prepared = []
        for key, value in items:
            if isinstance(value, str):
                value = value.encode('utf-8')
            elif not isinstance(value, bytes):
                import pickle
                value = pickle.dumps(value)
            prepared.append((str(key), value))
        
        self._db.batch_set(prepared)

    def close(self):
        """Close database and flush all data"""
        if not self._closed:
            self.flush()
            self._closed = True

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensure data is flushed"""
        self.close()
        return False

    def __del__(self):
        """Destructor - ensure data is flushed"""
        if not getattr(self, '_closed', True):
            try:
                self.close()
            except:
                pass


class AsyncDictSQLite:
    """
    Async version of DictSQLite v4.0 for high-concurrency scenarios

    This class now provides true asyncio support with awaitable methods.

    New async methods (awaitable):
        - async aget(key): Get value asynchronously
        - async aset(key, value): Set value asynchronously
        - async abatch_get(keys): Batch get asynchronously
        - async abatch_set(items): Batch set asynchronously

    Backward-compatible sync methods:
        - get(key): Get value (synchronous wrapper)
        - set(key, value): Set value (synchronous wrapper)
        - batch_get(keys): Batch get (synchronous wrapper)
        - batch_set(items): Batch set (synchronous wrapper)
    """

    def __init__(self, db_path, capacity=1_000_000, persist_mode="lazy",
                 storage_mode="pickle", table_name="main", buffer_size=100,
                 table_mode="prefix"):
        """
        Initialize Async DictSQLite

        Args:
            db_path: Path to database file
            capacity: Maximum entries in cache
            persist_mode: "memory", "lazy", or "writethrough"
            storage_mode: "pickle", "json", "jsonb", or "bytes"
            table_name: Default table name for operations
            buffer_size: Write buffer size for batching (default: 100)
            table_mode: Table isolation mode (default: "prefix")
                       - "prefix": Use key prefixes for table isolation (current behavior)
                       - "separate": Use separate SQLite tables for complete isolation
        """
        if not _NATIVE_AVAILABLE:
            raise RuntimeError(
                "DictSQLite v4.0 native extension not available. "
                "Please build it using: cd dictsqlite_v4 && maturin build --release"
            )

        # For writethrough mode, use buffer_size=1 by default for immediate persistence
        if persist_mode == "writethrough" and buffer_size == 100:
            buffer_size = 1

        self._db = _NativeAsyncDictSQLite(
            db_path, capacity, persist_mode, storage_mode, table_name, buffer_size,
            table_mode
        )
        self._storage_mode = storage_mode
        self._closed = False

    # New awaitable async methods
    async def aget(self, key):
        """Get value asynchronously (awaitable)

        Args:
            key: Key to retrieve

        Returns:
            Deserialized value

        Raises:
            KeyError: If key not found
            RuntimeError: If database is closed
        """
        if self._closed:
            raise RuntimeError("Database is closed")
        
        result = await self._db.aget(str(key))
        if result is None:
            raise KeyError(f"Key not found: {key}")
        
        # Deserialize based on storage mode
        if self._storage_mode == "bytes":
            return result
        elif self._storage_mode == "pickle":
            import pickle  # nosec B403 - pickle used for internal data serialization
            return pickle.loads(result)  # nosec B301 - safe_pickle available for untrusted data
        elif self._storage_mode in ("json", "jsonb"):
            if self._storage_mode == "jsonb":
                import msgpack
                return msgpack.unpackb(result, raw=False)
            else:
                import json
                return json.loads(result.decode('utf-8'))
        else:
            return result

    async def aset(self, key, value):
        """Set value asynchronously (awaitable)

        Args:
            key: Key to set
            value: Value to store (will be serialized based on storage_mode)
        
        Raises:
            RuntimeError: If database is closed
        """
        if self._closed:
            raise RuntimeError("Database is closed")
        
        # Serialize based on storage mode
        if self._storage_mode == "bytes":
            if isinstance(value, str):
                value = value.encode('utf-8')
            elif not isinstance(value, bytes):
                raise ValueError("bytes mode requires bytes or str values")
        elif self._storage_mode == "pickle":
            import pickle
            value = pickle.dumps(value)
        elif self._storage_mode in ("json", "jsonb"):
            import json
            if self._storage_mode == "jsonb":
                import msgpack
                value = msgpack.packb(value, use_bin_type=True)
            else:
                value = json.dumps(value).encode('utf-8')
        
        await self._db.aset(str(key), value)

    async def abatch_get(self, keys):
        """Batch get values asynchronously (awaitable)

        Args:
            keys: List of keys to retrieve

        Returns:
            List of values (or None for missing keys)
        """
        return await self._db.abatch_get([str(k) for k in keys])

    async def abatch_set(self, items):
        """Batch set values asynchronously (awaitable)

        Args:
            items: List of (key, value) tuples or dict
        """
        if isinstance(items, dict):
            items = items.items()

        prepared = []
        for key, value in items:
            if isinstance(value, str):
                value = value.encode('utf-8')
            elif not isinstance(value, bytes):
                import pickle
                value = pickle.dumps(value)
            prepared.append((str(key), value))

        await self._db.abatch_set(prepared)

    async def acontains(self, key):
        """Check if key exists asynchronously (awaitable)

        Args:
            key: Key to check

        Returns:
            True if key exists, False otherwise
        """
        return await self._db.acontains(str(key))

    async def adelete(self, key):
        """Delete key asynchronously (awaitable)

        Args:
            key: Key to delete
        
        Raises:
            KeyError: If key not found
        """
        # Check if key exists first
        if not await self.acontains(key):
            raise KeyError(f"Key not found: {key}")
        
        await self._db.adelete(str(key))

    async def aflush(self):
        """Flush cached data to storage asynchronously (awaitable)"""
        await self._db.aflush()

    async def aclose(self):
        """Close database and flush data asynchronously (awaitable)"""
        if not self._closed:
            await self._db.aclose()
            self._closed = True

    # Backward-compatible synchronous methods
    def get(self, key):
        """Get value (synchronous wrapper for backward compatibility)"""
        return self._db.get_async(str(key))

    def set(self, key, value):
        """Set value (synchronous wrapper for backward compatibility)"""
        if isinstance(value, str):
            value = value.encode('utf-8')
        elif not isinstance(value, bytes):
            import pickle
            value = pickle.dumps(value)
        self._db.set_async(str(key), value)

    def get_async(self, key):
        """Get value asynchronously (non-blocking, synchronous method)
        
        Note: Despite the name, this is a synchronous method that calls
        the underlying non-blocking implementation. For true async/await
        support, use aget() instead.
        """
        return self._db.get_async(str(key))

    def set_async(self, key, value):
        """Set value asynchronously (non-blocking, synchronous method)
        
        Note: Despite the name, this is a synchronous method that calls
        the underlying non-blocking implementation. For true async/await
        support, use aset() instead.
        """
        if isinstance(value, str):
            value = value.encode('utf-8')
        elif not isinstance(value, bytes):
            import pickle  # nosec B403 - pickle used for data serialization, safe_pickle available
            value = pickle.dumps(value)
        self._db.set_async(str(key), value)

    def batch_get(self, keys):
        """Batch get (synchronous wrapper for backward compatibility)"""
        return self._db.batch_get([str(k) for k in keys])

    def batch_set(self, items):
        """Batch set (synchronous wrapper for backward compatibility)"""
        prepared = []
        for key, value in items:
            if isinstance(value, str):
                value = value.encode('utf-8')
            elif not isinstance(value, bytes):
                import pickle
                value = pickle.dumps(value)
            prepared.append((str(key), value))

        self._db.batch_set(prepared)

    def stats(self):
        """Get cache statistics"""
        size, capacity = self._db.stats()
        return {"size": size, "capacity": capacity}

    def flush(self):
        """Flush cached data to storage"""
        self._db.flush()

    def close(self):
        """Close database and flush data"""
        if not self._closed:
            self._db.close()
            self._closed = True

    def clear(self):
        """Clear all data"""
        self._db.clear()

    # Dict-like interface (synchronous)
    def __getitem__(self, key):
        """Get value by key"""
        return self._db.__getitem__(str(key))

    def __setitem__(self, key, value):
        """Set value for key"""
        self._db.__setitem__(str(key), value)

    def table(self, table_name):
        """Get a table proxy for accessing a specific table"""
        return self._db.table(table_name)

    # Context manager support
    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensure data is flushed"""
        self.close()
        return False

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        self.close()
        return False


def is_native_available():
    """Check if native extension is available"""
    return _NATIVE_AVAILABLE


__all__ = [
    'DictSQLite',
    'DictSQLiteV4',  # Alias for backward compatibility
    'AsyncDictSQLite',
    'is_native_available',
    'Modes',
]

# Backward compatibility alias
DictSQLiteV4 = DictSQLite
