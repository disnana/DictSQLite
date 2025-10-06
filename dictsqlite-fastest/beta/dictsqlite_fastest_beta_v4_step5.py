"""
DictSQLite-Fastest Beta v4 - Step 5: Sequential Read Optimization

Step 5 implements critical sequential read optimizations to achieve v2+ performance:
- Ultra-fast cache-only path for preloaded data
- Bypasses all overhead when data is in memory
- Direct dict access for maximum speed
- Target: >= 1,700,000 ops/sec for sequential reads

This step focuses on eliminating ALL overhead in the fast path.
"""

import asyncio
import aiosqlite
import json
import time
import threading
import weakref
from typing import Any, Dict, Optional, List
from contextlib import asynccontextmanager
from collections import OrderedDict


# Import components from previous steps
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# From Step 3
from dictsqlite_fastest_beta_v4_step3 import (
    DatabaseSizeAnalyzer,
    HybridCache,
    BackgroundStatsCollector as BackgroundStatsCollectorV3
)

# From Step 4
from dictsqlite_fastest_beta_v4_step4 import (
    BackgroundStatsCollector,
    ExternalStatsDB
)


class AsyncDictSQLiteFastestBetaV4:
    """
    AsyncDictSQLiteFastestBetaV4 - Step 5: Sequential Read Optimization
    
    Optimized for maximum sequential read performance while maintaining
    all v4 features. Uses ultra-fast cache-only path when data is preloaded.
    
    Key Optimizations in Step 5:
    - Direct dict __getitem__ for cache hits (bypasses all overhead)
    - Fast-path checks for preloaded data
    - Minimal branching in hot path
    - Zero-overhead cache lookups
    
    Performance targets:
    - Sequential reads: >= 1,700,000 ops/sec (v2 baseline)
    - Concurrent reads: >= 10,000 ops/sec (v3 baseline)
    - Cache hit rate: 95%+ for sequential access
    """
    
    def __init__(
        self,
        db_name: str,
        table_name: str = 'data',
        max_connections: int = 8,
        pool_min_size: int = 2,
        pool_max_size: int = 8,
        pool_auto_scale: bool = True,
        pool_idle_timeout: float = 60.0,
        enable_prefetch: bool = False,
        prefetch_size: int = 10,
        adaptive_batch: bool = True,
        batch_size_min: int = 10,
        batch_size_max: int = 1000,
        extended_stats: bool = False,
        auto_preload: bool = True,
        preload_max_entries: int = 100000,
        preload_max_size_mb: int = 100,
        cache_strategy: str = 'hybrid',  # 'lru', 'lfu', 'hybrid'
        cache_max_size: int = 10000,
        stats_db_path: Optional[str] = None,
        stats_flush_interval: float = 5.0,
        enable_sequential_optimization: bool = True,  # NEW in Step 5
    ):
        """
        Initialize AsyncDictSQLiteFastestBetaV4 with Step 5 optimizations.
        
        Step 5 Parameters:
        enable_sequential_optimization: Enable ultra-fast sequential read path (default: True)
        """
        try:
            import aiosqlite
        except ImportError:
            raise ImportError(
                "aiosqlite is required for AsyncDictSQLiteFastestBetaV3. "
                "Install with: pip install aiosqlite"
            )
        
        self.db_name = db_name
        self.table_name = table_name
        self._max_connections = max_connections
        
        # Pool configuration
        self.pool_min_size = pool_min_size
        self.pool_max_size = pool_max_size
        self.pool_auto_scale = pool_auto_scale
        self.pool_idle_timeout = pool_idle_timeout
        
        # Prefetch configuration
        self.enable_prefetch = enable_prefetch
        self.prefetch_size = prefetch_size
        
        # Adaptive batch configuration
        self.adaptive_batch = adaptive_batch
        self.batch_size_min = batch_size_min
        self.batch_size_max = batch_size_max
        self._current_batch_size = 100
        self._batch_latency_history = []
        
        # Extended stats configuration
        self.extended_stats = extended_stats
        
        # Auto-preload configuration (Step 3)
        self.auto_preload = auto_preload
        self.preload_max_entries = preload_max_entries
        self.preload_max_size_mb = preload_max_size_mb
        self._preloaded = False
        
        # Cache configuration (Step 3)
        self.cache_strategy = cache_strategy
        self.cache_max_size = cache_max_size
        self._hybrid_cache = None
        
        # External stats DB (Step 4)
        self.stats_db_path = stats_db_path
        self.stats_flush_interval = stats_flush_interval
        self._external_stats_db = None
        
        # Sequential optimization (Step 5)
        self.enable_sequential_optimization = enable_sequential_optimization
        
        # Core state
        self._initialized = False
        self._connection_pool = []
        self._available_connections = None
        self._pool_lock = None
        
        # Cache and buffers
        self._cache = {}
        self._delete_buffer = set()
        self._write_buffer = {}
        
        # Async locks
        self._async_buffer_lock = None
        self._async_write_lock = None
        
        # Background commit
        self._commit_stop_event = None
        self._commit_task = None
        self._background_commit_interval = 1.0
        
        # Prefetch state
        self._prefetch_cache = {}
        self._access_patterns = {}
        
        # Extended stats (Step 2)
        self._stats_collector = BackgroundStatsCollector()
        
        # Pool stats
        self._pool_stats = {
            'peak_connections': 0,
            'current_connections': 0,
            'connection_waits': 0,
            'idle_cleanups': 0,
        }
        
        # Connection tracking
        self._connection_last_used = {}
        self._idle_cleanup_task = None
        
    async def _ensure_initialized(self) -> None:
        """非同期コンポーネントの初期化（スレッドセーフ）."""
        if self._initialized:
            return
        
        # Use a simple flag-based initialization
        if not hasattr(self, '_initializing'):
            self._initializing = True
            
            # asyncio関連の初期化
            self._available_connections = asyncio.Queue(maxsize=self._max_connections)
            self._pool_lock = asyncio.Lock()
            self._async_buffer_lock = asyncio.Lock()
            self._async_write_lock = asyncio.Lock()
            self._commit_stop_event = asyncio.Event()
            
            # 接続プールの作成
            for _ in range(self._max_connections):
                conn = await aiosqlite.connect(self.db_name)
                
                # 最適化PRAGMA設定
                await conn.execute("PRAGMA journal_mode=WAL")
                await conn.execute("PRAGMA synchronous=NORMAL")
                await conn.execute("PRAGMA cache_size=-64000")
                await conn.execute("PRAGMA temp_store=MEMORY")
                await conn.execute("PRAGMA mmap_size=268435456")
                
                # テーブル作成
                schema = f'CREATE TABLE IF NOT EXISTS {self._quote_ident(self.table_name)} (key TEXT PRIMARY KEY, value TEXT)'
                await conn.execute(schema)
                await conn.commit()
                
                self._connection_pool.append(conn)
                await self._available_connections.put(conn)
                self._connection_last_used[id(conn)] = time.time()
            
            self._pool_stats['current_connections'] = len(self._connection_pool)
            self._pool_stats['peak_connections'] = len(self._connection_pool)
            
            # バックグラウンドコミットタスクの開始
            self._commit_task = asyncio.create_task(self._background_commit_worker())
            
            # アイドル接続クリーンアップタスクの開始
            if self.pool_auto_scale:
                self._idle_cleanup_task = asyncio.create_task(self._idle_connection_cleanup())
            
            # Initialize hybrid cache (Step 3)
            if self.cache_strategy in ['lru', 'lfu', 'hybrid']:
                self._hybrid_cache = HybridCache(
                    max_size=self.cache_max_size,
                    strategy=self.cache_strategy
                )
            
            # Auto-preload if enabled (Step 3)
            if self.auto_preload:
                await self._try_auto_preload()
            
            # Initialize external stats DB (Step 4)
            if self.stats_db_path:
                self._external_stats_db = ExternalStatsDB(
                    self.stats_db_path,
                    self.stats_flush_interval
                )
                await self._external_stats_db.start()
            
            self._initialized = True
            delattr(self, '_initializing')
    
    async def _try_auto_preload(self):
        """Try to preload entire database if it's small enough (Step 3)."""
        try:
            analyzer = DatabaseSizeAnalyzer(self.db_name, self.table_name)
            should_preload, stats = await analyzer.should_preload(
                self.preload_max_entries,
                self.preload_max_size_mb
            )
            
            if should_preload:
                # Preload all data into cache
                async with self._get_connection() as conn:
                    cursor = await conn.execute(
                        f'SELECT key, value FROM {self._quote_ident(self.table_name)}'
                    )
                    rows = await cursor.fetchall()
                    
                    for key, value_json in rows:
                        try:
                            value = json.loads(value_json)
                            self._cache[key] = value
                            if self._hybrid_cache:
                                self._hybrid_cache.put(key, value)
                        except (json.JSONDecodeError, TypeError):
                            pass
                    
                    self._preloaded = True
                    
        except Exception:
            # Preload failed, continue without it
            pass
    
    def _quote_ident(self, ident: str) -> str:
        """Quote an identifier for safe use in SQL."""
        return f'"{ident.replace("\"", "\"\"")}"'
    
    @asynccontextmanager
    async def _get_connection(self):
        """接続プールから接続を取得"""
        await self._ensure_initialized()
        
        start_time = time.time()
        conn = await self._available_connections.get()
        wait_time = time.time() - start_time
        
        if wait_time > 0.1:  # 100ms以上待った場合
            self._pool_stats['connection_waits'] += 1
            
            # プールのスケールアップを検討
            if self.pool_auto_scale and len(self._connection_pool) < self.pool_max_size:
                async with self._pool_lock:
                    if len(self._connection_pool) < self.pool_max_size:
                        new_conn = await aiosqlite.connect(self.db_name)
                        await new_conn.execute("PRAGMA journal_mode=WAL")
                        await new_conn.execute("PRAGMA synchronous=NORMAL")
                        await new_conn.execute("PRAGMA cache_size=-64000")
                        await new_conn.execute("PRAGMA temp_store=MEMORY")
                        await new_conn.execute("PRAGMA mmap_size=268435456")
                        
                        self._connection_pool.append(new_conn)
                        await self._available_connections.put(new_conn)
                        self._connection_last_used[id(new_conn)] = time.time()
                        
                        self._pool_stats['current_connections'] = len(self._connection_pool)
                        if self._pool_stats['current_connections'] > self._pool_stats['peak_connections']:
                            self._pool_stats['peak_connections'] = self._pool_stats['current_connections']
        
        try:
            self._connection_last_used[id(conn)] = time.time()
            yield conn
        finally:
            await self._available_connections.put(conn)
    
    async def _idle_connection_cleanup(self):
        """アイドル状態の接続をクリーンアップ"""
        while not self._commit_stop_event.is_set():
            try:
                await asyncio.sleep(self.pool_idle_timeout)
                
                current_time = time.time()
                async with self._pool_lock:
                    # 最小接続数より多く、アイドル時間が閾値を超えた接続を削除
                    if len(self._connection_pool) > self.pool_min_size:
                        for conn in list(self._connection_pool):
                            conn_id = id(conn)
                            if conn_id in self._connection_last_used:
                                idle_time = current_time - self._connection_last_used[conn_id]
                                if idle_time > self.pool_idle_timeout and len(self._connection_pool) > self.pool_min_size:
                                    try:
                                        await conn.close()
                                        self._connection_pool.remove(conn)
                                        del self._connection_last_used[conn_id]
                                        self._pool_stats['idle_cleanups'] += 1
                                        self._pool_stats['current_connections'] = len(self._connection_pool)
                                    except Exception:
                                        pass
            except asyncio.CancelledError:
                break
            except Exception:
                continue
    
    async def aget(self, key: str, default: Any = None) -> Any:
        """
        非同期でキーに対応する値を取得（Step 5 最適化版）.
        
        Step 5 optimizations:
        - Ultra-fast cache-only path for preloaded data
        - Direct dict access without overhead
        - Minimal branching in hot path
        """
        await self._ensure_initialized()
        
        # STEP 5 OPTIMIZATION: Ultra-fast path for preloaded data
        # This bypasses ALL overhead for maximum sequential read speed
        if self.enable_sequential_optimization and self._preloaded:
            # Direct dict access - fastest possible path
            try:
                return self._cache[key]
            except KeyError:
                # Record access for stats (minimal overhead)
                if self._external_stats_db:
                    self._external_stats_db.record_operation('get', key)
                return default
        
        # Standard path (for non-preloaded data)
        # Record stats (Step 2)
        self._stats_collector.record_operation('get')
        
        # Check delete buffer
        if key in self._delete_buffer:
            return default
        
        # Check hybrid cache first (Step 3)
        if self._hybrid_cache:
            value = self._hybrid_cache.get(key)
            if value is not None:
                if self._external_stats_db:
                    self._external_stats_db.record_operation('get', key)
                return value
        
        # Check traditional cache
        if key in self._cache:
            if self._external_stats_db:
                self._external_stats_db.record_operation('get', key)
            return self._cache[key]
        
        # Check prefetch cache
        if self.enable_prefetch and key in self._prefetch_cache:
            value = self._prefetch_cache.pop(key)
            self._cache[key] = value
            if self._hybrid_cache:
                self._hybrid_cache.put(key, value)
            if self._external_stats_db:
                self._external_stats_db.record_operation('get', key)
            return value
        
        # Fetch from database
        async with self._get_connection() as conn:
            cursor = await conn.execute(
                f'SELECT value FROM {self._quote_ident(self.table_name)} WHERE key = ?',
                (key,)
            )
            row = await cursor.fetchone()
            
            if row:
                try:
                    value = json.loads(row[0])
                    self._cache[key] = value
                    if self._hybrid_cache:
                        self._hybrid_cache.put(key, value)
                    
                    # Prefetch logic
                    if self.enable_prefetch:
                        await self._try_prefetch(key)
                    
                    if self._external_stats_db:
                        self._external_stats_db.record_operation('get', key)
                    
                    return value
                except (json.JSONDecodeError, TypeError):
                    return default
            
            if self._external_stats_db:
                self._external_stats_db.record_operation('get', key)
            return default
    
    async def _try_prefetch(self, key: str):
        """Try to prefetch next keys based on pattern."""
        # Simple numeric pattern detection
        try:
            # Extract numeric suffix
            parts = key.rsplit('_', 1)
            if len(parts) == 2 and parts[1].isdigit():
                prefix = parts[0]
                num = int(parts[1])
                
                # Prefetch next N keys
                next_keys = [f"{prefix}_{num + i}" for i in range(1, self.prefetch_size + 1)]
                
                async with self._get_connection() as conn:
                    placeholders = ','.join('?' * len(next_keys))
                    cursor = await conn.execute(
                        f'SELECT key, value FROM {self._quote_ident(self.table_name)} WHERE key IN ({placeholders})',
                        next_keys
                    )
                    rows = await cursor.fetchall()
                    
                    for key, value_json in rows:
                        try:
                            value = json.loads(value_json)
                            self._prefetch_cache[key] = value
                        except (json.JSONDecodeError, TypeError):
                            pass
        except Exception:
            pass
    
    async def aset(self, key: str, value: Any) -> None:
        """非同期でキーに値を設定."""
        await self._ensure_initialized()
        
        # Record stats (Step 2)
        self._stats_collector.record_operation('set')
        
        # Update cache immediately
        self._cache[key] = value
        if self._hybrid_cache:
            self._hybrid_cache.put(key, value)
        
        # Remove from delete buffer if present
        if key in self._delete_buffer:
            self._delete_buffer.remove(key)
        
        # Add to write buffer
        async with self._async_buffer_lock:
            self._write_buffer[key] = value
        
        # Record in external stats
        if self._external_stats_db:
            self._external_stats_db.record_operation('set', key, value)
    
    async def adelete(self, key: str) -> None:
        """非同期でキーを削除."""
        await self._ensure_initialized()
        
        # Record stats (Step 2)
        self._stats_collector.record_operation('delete')
        
        # Remove from cache
        if key in self._cache:
            del self._cache[key]
        
        if self._hybrid_cache:
            self._hybrid_cache.evict(key)
        
        # Add to delete buffer
        self._delete_buffer.add(key)
        
        # Remove from write buffer if present
        async with self._async_buffer_lock:
            if key in self._write_buffer:
                del self._write_buffer[key]
        
        # Record in external stats
        if self._external_stats_db:
            self._external_stats_db.record_operation('delete', key)
    
    async def abulk_insert(self, items: Dict[str, Any]) -> None:
        """非同期でバルクインサート."""
        await self._ensure_initialized()
        
        if not items:
            return
        
        # Record stats (Step 2)
        self._stats_collector.record_operation('bulk_insert')
        
        start_time = time.time()
        
        # Update cache
        for key, value in items.items():
            self._cache[key] = value
            if self._hybrid_cache:
                self._hybrid_cache.put(key, value)
            if key in self._delete_buffer:
                self._delete_buffer.remove(key)
        
        # Add to write buffer
        async with self._async_buffer_lock:
            self._write_buffer.update(items)
        
        # Record in external stats
        if self._external_stats_db:
            for key, value in items.items():
                self._external_stats_db.record_operation('bulk_insert', key, value)
        
        # Adaptive batch sizing
        if self.adaptive_batch:
            latency = time.time() - start_time
            self._batch_latency_history.append(latency)
            if len(self._batch_latency_history) > 20:
                self._batch_latency_history.pop(0)
            
            # Adjust batch size based on latency
            if latency > 0.1:  # High latency
                self._current_batch_size = max(
                    self.batch_size_min,
                    int(self._current_batch_size * 0.8)
                )
            elif latency < 0.02:  # Low latency
                self._current_batch_size = min(
                    self.batch_size_max,
                    int(self._current_batch_size * 1.2)
                )
    
    async def _flush_write_buffer(self) -> None:
        """書き込みバッファをフラッシュ（デッドロック防止）."""
        # Get buffer snapshot
        async with self._async_buffer_lock:
            if not self._write_buffer and not self._delete_buffer:
                return
            
            write_items = dict(self._write_buffer)
            delete_keys = set(self._delete_buffer)
            self._write_buffer.clear()
            self._delete_buffer.clear()
        
        # Perform writes
        if write_items or delete_keys:
            async with self._async_write_lock:
                async with self._get_connection() as conn:
                    # Write items
                    if write_items:
                        await conn.execute("BEGIN IMMEDIATE")
                        for key, value in write_items.items():
                            value_json = json.dumps(value)
                            await conn.execute(
                                f'INSERT OR REPLACE INTO {self._quote_ident(self.table_name)} (key, value) VALUES (?, ?)',
                                (key, value_json)
                            )
                        await conn.commit()
                    
                    # Delete items
                    if delete_keys:
                        await conn.execute("BEGIN IMMEDIATE")
                        for key in delete_keys:
                            await conn.execute(
                                f'DELETE FROM {self._quote_ident(self.table_name)} WHERE key = ?',
                                (key,)
                            )
                        await conn.commit()
    
    async def _background_commit_worker(self) -> None:
        """バックグラウンドでコミットを実行するワーカー."""
        while not self._commit_stop_event.is_set():
            try:
                await asyncio.sleep(self._background_commit_interval)
                await self._flush_write_buffer()
            except asyncio.CancelledError:
                break
            except Exception:
                continue
    
    def get_stats(self) -> dict:
        """
        統計情報を取得.
        
        Returns:
            統計情報の辞書
        """
        stats = {
            'pool': self._pool_stats.copy(),
            'cache_size': len(self._cache),
            'write_buffer_size': len(self._write_buffer),
            'delete_buffer_size': len(self._delete_buffer),
            'prefetch_cache_size': len(self._prefetch_cache),
            'background_stats': self._stats_collector.get_stats(),
            'preloaded': self._preloaded,
            'sequential_optimization_enabled': self.enable_sequential_optimization,
        }
        
        # Add hybrid cache stats (Step 3)
        if self._hybrid_cache:
            stats['hybrid_cache'] = self._hybrid_cache.get_stats()
        
        # Add external stats DB info (Step 4)
        if self._external_stats_db:
            stats['external_stats_db'] = self._external_stats_db.get_buffer_stats()
        
        return stats
    
    async def aclose(self) -> None:
        """非同期でデータベースを閉じる."""
        if not self._initialized:
            return
        
        # Stop background tasks
        if self._commit_stop_event:
            self._commit_stop_event.set()
        
        if self._commit_task:
            try:
                await asyncio.wait_for(self._commit_task, timeout=2.0)
            except asyncio.TimeoutError:
                self._commit_task.cancel()
        
        if self._idle_cleanup_task:
            try:
                self._idle_cleanup_task.cancel()
                await self._idle_cleanup_task
            except (asyncio.CancelledError, Exception):
                pass
        
        # Flush remaining data
        try:
            await self._flush_write_buffer()
        except Exception:
            pass
        
        # Close external stats DB (Step 4)
        if self._external_stats_db:
            try:
                await self._external_stats_db.stop()
            except Exception:
                pass
        
        # Close connections
        for conn in self._connection_pool:
            try:
                await conn.close()
            except Exception:
                pass
        
        self._initialized = False
    
    async def __aenter__(self):
        await self._ensure_initialized()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.aclose()


# Backward compatibility alias
AsyncDictSQLiteFastestBeta = AsyncDictSQLiteFastestBetaV4


__all__ = ['AsyncDictSQLiteFastestBetaV4', 'AsyncDictSQLiteFastestBeta']
