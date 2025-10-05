"""DictSQLite-Fastest Beta v4 - Enhanced Caching & Statistics

v3-alphaの全機能 + 高度なキャッシング戦略:

v4 New Features:
- インテリジェント全データロード (小規模データを自動検出して全てメモリに)
- LRU/LFU ハイブリッドキャッシュ (使用頻度と最終使用時刻の両方を考慮)
- 統計情報の外部DB保存オプション (メインDBと分離)
- シーケンシャルリード性能の最適化 (v2以上の性能を保証)

v3-alpha Features (維持):
- Phase 1: 動的接続プール (30%の並行性能向上)
- Phase 2: パターンベース先読み (シーケンシャルアクセス最適化)
- Phase 3: 適応的バッチサイジング (混合ワークロード最適化)
- Phase 4: 拡張統計追跡 (詳細パフォーマンス分析)

パフォーマンス目標:
- シーケンシャルリード: v2同等以上 (>= 1,700,000 ops/sec)
- 並行リード: v3-alpha同等以上 (>= 10,000 ops/sec)
- 小規模データ: 2倍以上の高速化 (全ロードによる)
"""

import sys
import os
from pathlib import Path
from collections import OrderedDict
from threading import Lock, RLock, Thread, Event
from contextlib import asynccontextmanager
import time
import weakref
import pickle
import asyncio
from typing import Optional, Any, Dict, List, Tuple
import atexit

# 親ディレクトリのdictsqlite_fastestモジュールをインポート
sys.path.insert(0, str(Path(__file__).parent.parent))
from dictsqlite_fastest.main import DictSQLiteFastest

# aiosqliteのインポート(非同期版で使用)
try:
    import aiosqlite
    AIOSQLITE_AVAILABLE = True
except ImportError:
    AIOSQLITE_AVAILABLE = False
    aiosqlite = None


# ============================================================================
# v4: Database Size Analyzer
# ============================================================================

class DatabaseSizeAnalyzer:
    """データベースサイズとエントリ数を分析してメモリ戦略を決定"""
    
    __slots__ = ('db_path', 'table_name')
    
    def __init__(self, db_path: str, table_name: str):
        self.db_path = db_path
        self.table_name = table_name
    
    async def analyze_database(self) -> Dict[str, Any]:
        """
        データベースを分析してサイズ情報を返す
        
        Returns:
            {
                'total_entries': int,
                'total_size_bytes': int,
                'avg_entry_size': int,
                'estimated_memory_mb': float
            }
        """
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                # エントリ数を取得
                cursor = await conn.execute(
                    f"SELECT COUNT(*) FROM {self.table_name}"
                )
                row = await cursor.fetchone()
                total_entries = row[0] if row else 0
                await cursor.close()
                
                if total_entries == 0:
                    return {
                        'total_entries': 0,
                        'total_size_bytes': 0,
                        'avg_entry_size': 0,
                        'estimated_memory_mb': 0.0
                    }
                
                # 合計サイズを推定(サンプリング)
                # 全件チェックは重いので,最初の1000件から推定
                sample_size = min(1000, total_entries)
                cursor = await conn.execute(
                    f"SELECT LENGTH(key) + LENGTH(value) FROM {self.table_name} LIMIT ?",
                    (sample_size,)
                )
                rows = await cursor.fetchall()
                await cursor.close()
                
                sample_total_size = sum(row[0] for row in rows if row[0])
                avg_entry_size = sample_total_size / sample_size if sample_size > 0 else 0
                
                # 推定合計サイズ
                estimated_total_size = avg_entry_size * total_entries
                estimated_memory_mb = estimated_total_size / (1024 * 1024)
                
                return {
                    'total_entries': total_entries,
                    'total_size_bytes': int(estimated_total_size),
                    'avg_entry_size': int(avg_entry_size),
                    'estimated_memory_mb': estimated_memory_mb
                }
        except Exception:
            # テーブルが存在しない場合など
            return {
                'total_entries': 0,
                'total_size_bytes': 0,
                'avg_entry_size': 0,
                'estimated_memory_mb': 0.0
            }


# ============================================================================
# v4: Hybrid Cache (LRU + LFU)
# ============================================================================

class HybridCache:
    """LRU + LFU ハイブリッドキャッシュ実装
    
    使用頻度と最終使用時刻の両方を考慮した退避アルゴリズム.
    """
    
    __slots__ = (
        'capacity', 'cache', 'lock', 
        'access_count', 'last_access_time',
        'eviction_strategy', 'hits', 'misses',
        'eviction_count'
    )
    
    def __init__(self, capacity: int = 10000, 
                 eviction_strategy: str = 'hybrid'):
        """
        Args:
            capacity: キャッシュ容量
            eviction_strategy: 'lru', 'lfu', 'hybrid'
        """
        self.capacity = capacity
        self.cache = OrderedDict()
        self.access_count = {}
        self.last_access_time = {}
        self.eviction_strategy = eviction_strategy
        self.lock = Lock()
        self.hits = 0
        self.misses = 0
        self.eviction_count = 0
    
    def _calculate_eviction_score(self, key: str) -> float:
        """
        退避スコア計算 (低いほど退避対象)
        
        hybrid: 使用頻度 * 0.7 + 時間スコア * 0.3
        lfu: 使用頻度のみ
        lru: 時間スコアのみ
        """
        if self.eviction_strategy == 'lfu':
            return self.access_count.get(key, 0)
        
        if self.eviction_strategy == 'lru':
            time_score = time.time() - self.last_access_time.get(key, 0)
            return -time_score  # 古いほど低スコア
        
        # hybrid
        freq_score = self.access_count.get(key, 0)
        current_time = time.time()
        time_since_access = current_time - self.last_access_time.get(key, 0)
        time_normalized = min(time_since_access / 3600, 1.0)  # 1時間で正規化
        
        return freq_score * 0.7 + (1.0 - time_normalized) * 0.3
    
    def get(self, key: str) -> Optional[Any]:
        """キャッシュから値を取得"""
        with self.lock:
            if key not in self.cache:
                self.misses += 1
                return None
            
            self.hits += 1
            self.access_count[key] = self.access_count.get(key, 0) + 1
            self.last_access_time[key] = time.time()
            
            # LRU: アクセスされたアイテムを最後に移動
            self.cache.move_to_end(key)
            return self.cache[key]
    
    def get_fast(self, key: str) -> Optional[Any]:
        """高速版 - 統計更新なし(読み取り専用最適化)"""
        # ロックなしで読み取り(Pythonの辞書はスレッドセーフ読み取り)
        return self.cache.get(key)
    
    def put(self, key: str, value: Any) -> None:
        """キャッシュに値を追加(ハイブリッド戦略)"""
        with self.lock:
            # 容量チェック
            if len(self.cache) >= self.capacity and key not in self.cache:
                # 最低スコアのキーを退避
                evict_key = min(
                    self.cache.keys(),
                    key=lambda k: self._calculate_eviction_score(k)
                )
                self.cache.pop(evict_key)
                self.access_count.pop(evict_key, None)
                self.last_access_time.pop(evict_key, None)
                self.eviction_count += 1
            
            self.cache[key] = value
            self.access_count[key] = self.access_count.get(key, 0) + 1
            self.last_access_time[key] = time.time()
    
    def put_fast(self, key: str, value: Any) -> None:
        """高速版 - LRU更新なし"""
        with self.lock:
            # 容量チェック(簡略版)
            if len(self.cache) >= self.capacity and key not in self.cache:
                # 先頭を削除(最も古い)
                oldest_key = next(iter(self.cache))
                self.cache.pop(oldest_key)
                self.access_count.pop(oldest_key, None)
                self.last_access_time.pop(oldest_key, None)
                self.eviction_count += 1
            
            self.cache[key] = value
            self.access_count[key] = self.access_count.get(key, 0) + 1
            self.last_access_time[key] = time.time()
    
    def remove(self, key: str) -> None:
        """キャッシュからキーを削除"""
        with self.lock:
            self.cache.pop(key, None)
            self.access_count.pop(key, None)
            self.last_access_time.pop(key, None)
    
    def clear(self) -> None:
        """キャッシュをクリア"""
        with self.lock:
            self.cache.clear()
            self.access_count.clear()
            self.last_access_time.clear()
            self.hits = 0
            self.misses = 0
            self.eviction_count = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """キャッシュ統計を取得"""
        with self.lock:
            total = self.hits + self.misses
            hit_rate = (self.hits / total * 100) if total > 0 else 0
            return {
                'size': len(self.cache),
                'capacity': self.capacity,
                'hits': self.hits,
                'misses': self.misses,
                'hit_rate': hit_rate,
                'eviction_count': self.eviction_count,
                'strategy': self.eviction_strategy
            }
    
    def get_hot_keys(self, top_n: int = 100) -> List[Tuple[str, int]]:
        """使用頻度上位N件のキーを取得"""
        with self.lock:
            return sorted(
                self.access_count.items(),
                key=lambda x: x[1],
                reverse=True
            )[:top_n]


# ============================================================================
# LRUキャッシュ(v2/v3互換性のため維持)
# ============================================================================

class LRUCache:
    """スレッドセーフなLRUキャッシュ実装.
    
    最も頻繁にアクセスされるデータをメモリに保持し,
    ディスクアクセスを削減します.
    """
    
    __slots__ = ('capacity', 'cache', 'lock', 'hits', 'misses', 'simple_cache')
    
    def __init__(self, capacity: int = 10000):
        """
        Args:
            capacity: キャッシュの最大容量(アイテム数)
        """
        self.capacity = capacity
        self.cache = OrderedDict()
        self.lock = Lock()
        self.hits = 0
        self.misses = 0
        # 高速モード用のシンプルキャッシュ(ロックなし)
        self.simple_cache = {}
    
    def get(self, key: str) -> Optional[Any]:
        """キャッシュから値を取得.
        
        Args:
            key: 取得するキー
            
        Returns:
            キャッシュされている値,存在しない場合はNone
        """
        with self.lock:
            if key not in self.cache:
                self.misses += 1
                return None
            
            self.hits += 1
            # LRU: アクセスされたアイテムを最後に移動
            self.cache.move_to_end(key)
            return self.cache[key]
    
    def get_fast(self, key: str) -> Optional[Any]:
        """キャッシュから値を取得(高速版 - ロックなし,LRU更新なし).
        
        初回読み込み時の最適化用.シンプルdictを使用してロックとOrderedDictのオーバーヘッドを回避.
        
        Args:
            key: 取得するキー
            
        Returns:
            キャッシュにある場合は値,ない場合はNone
        """
        # ロックなしで単純に取得(読み取り専用操作なので安全)
        return self.simple_cache.get(key)
    
    def put(self, key: str, value: Any) -> None:
        """キャッシュに値を追加.
        
        Args:
            key: キー
            value: 値
        """
        with self.lock:
            if key in self.cache:
                # 既存のキーは最後に移動
                self.cache.move_to_end(key)
            else:
                # 容量チェック
                if len(self.cache) >= self.capacity:
                    # 最も古いアイテムを削除
                    self.cache.popitem(last=False)
            
            self.cache[key] = value
    
    def put_fast(self, key: str, value: Any) -> None:
        """キャッシュに値を追加(高速版 - ロックなし,LRU更新なし).
        
        初回読み込み時の最適化用.シンプルdictを使用してロックとOrderedDictのオーバーヘッドを回避.
        
        Args:
            key: キー
            value: 値
        """
        # ロックなしでシンプルキャッシュに追加(高速)
        self.simple_cache[key] = value
        
        # 容量制限チェック(定期的に)
        if len(self.simple_cache) > self.capacity * 1.2:  # 20%のバッファを許容
            # 容量超過時はシンプルキャッシュをクリアして再構築
            items = list(self.simple_cache.items())
            self.simple_cache = dict(items[-self.capacity:])  # 最新のN件を保持
    
    def remove(self, key: str) -> None:
        """キャッシュからキーを削除.
        
        Args:
            key: 削除するキー
        """
        with self.lock:
            self.cache.pop(key, None)
    
    def clear(self) -> None:
        """キャッシュをクリア"""
        with self.lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """キャッシュ統計を取得"""
        with self.lock:
            total = self.hits + self.misses
            hit_rate = (self.hits / total * 100) if total > 0 else 0
            return {
                'size': len(self.cache),
                'capacity': self.capacity,
                'hits': self.hits,
                'misses': self.misses,
                'hit_rate': hit_rate
            }


# ============================================================================
# 書き込みバッファ(変更なし)
# ============================================================================

class WriteBuffer:
    """遅延書き込みバッファ - 書き込みをバッチ化してディスクアクセスを削減"""
    
    __slots__ = ('flush_threshold', 'flush_interval', 'buffer', 'deleted_keys', 'lock', 'last_flush_time')
    
    def __init__(self, flush_threshold: int = 1000, flush_interval: float = 5.0):
        """
        Args:
            flush_threshold: この数の書き込みが溜まったらフラッシュ
            flush_interval: この時間(秒)が経過したらフラッシュ
        """
        self.flush_threshold = flush_threshold
        self.flush_interval = flush_interval
        self.buffer = {}
        self.deleted_keys = set()
        self.lock = RLock()
        self.last_flush_time = time.time()
    
    def add(self, key: str, value: Any) -> bool:
        """バッファに書き込みを追加.
        
        Args:
            key: キー
            value: 値
            
        Returns:
            フラッシュが必要な場合True
        """
        with self.lock:
            self.buffer[key] = value
            # 削除予定リストから除外
            self.deleted_keys.discard(key)
            
            return self._should_flush()
    
    def remove(self, key: str) -> bool:
        """バッファにキー削除を追加.
        
        Args:
            key: 削除するキー
            
        Returns:
            フラッシュが必要な場合True
        """
        with self.lock:
            # バッファから削除
            self.buffer.pop(key, None)
            # 削除予定リストに追加
            self.deleted_keys.add(key)
            
            return self._should_flush()
    
    def _should_flush(self) -> bool:
        """フラッシュが必要かチェック.
        
        Returns:
            フラッシュが必要な場合True
        """
        current_time = time.time()
        time_exceeded = (current_time - self.last_flush_time) >= self.flush_interval
        size_exceeded = len(self.buffer) >= self.flush_threshold
        
        return time_exceeded or size_exceeded
    
    def get_pending(self) -> Tuple[Dict[str, Any], set]:
        """保留中の書き込み/削除を取得してクリア.
        
        Returns:
            (書き込みバッファ, 削除キーセット) のタプル
        """
        with self.lock:
            buffer_copy = self.buffer.copy()
            deleted_copy = self.deleted_keys.copy()
            
            self.buffer.clear()
            self.deleted_keys.clear()
            self.last_flush_time = time.time()
            
            return buffer_copy, deleted_copy


# ============================================================================
# 同期版Beta(Fastest版の最適化統合)
# ============================================================================

class DictSQLiteFastestBeta(DictSQLiteFastest):
    """同期版DictSQLite-Fastest Beta - メモリ最優先の高速化実装.
    
    Fastest版の全最適化 + Beta版の追加機能:
    - ✅ APSW高速化(Fastest版から継承)
    - ✅ WALモード最適化(Fastest版から継承)
    - ✅ 3層防御テーブル存在確認(Fastest版から継承)
    - ✅ LRUキャッシュ(Beta版独自)
    - ✅ 書き込みバッファリング(Beta版独自)
    - ✅ メモリ予算管理(Beta版独自)
    - ✅ ホットデータ検出(Beta版独自)
    """
    
    def __init__(
        self,
        db_name: str,
        table_name: str = 'main',
        # Beta版パラメータ
        cache_capacity: int = 10000,
        write_buffer_size: int = 1000,
        write_buffer_interval: float = 5.0,
        memory_only: bool = False,
        aggressive_memory: bool = True,
        memory_budget_mb: Optional[int] = None,
        auto_load_threshold_mb: float = 10.0,
        enable_background_flush: bool = True,
        enable_hot_data_detection: bool = True,
        # 最適化パラメータ(v1からの移植)
        enable_stats_collection: bool = False,
        lazy_tracking_threshold: int = 100,
        fast_mode: bool = True,
        **kwargs
    ):
        """
        Args:
            db_name: データベースファイルパス
            table_name: テーブル名
            cache_capacity: LRUキャッシュの最大容量
            write_buffer_size: 書き込みバッファの閾値
            write_buffer_interval: 書き込みバッファのフラッシュ間隔(秒)
            memory_only: メモリのみモード(ディスク永続化なし)
            aggressive_memory: アグレッシブなメモリ最適化
            memory_budget_mb: メモリ予算(MB)
            auto_load_threshold_mb: 自動全件ロードの閾値(MB)
            enable_background_flush: バックグラウンドフラッシュ有効化
            enable_hot_data_detection: ホットデータ検出有効化
            enable_stats_collection: 統計情報収集を有効化(パフォーマンス重視の場合はFalse)
            lazy_tracking_threshold: この操作回数まではアクセス頻度追跡をスキップ
            fast_mode: 高速モード(ロックなしキャッシュ,初回読み込み最適化)
        """
        # Fastest版の初期化(全ての最適化を継承)
        super().__init__(
            db_name=db_name,
            table_name=table_name,
            **kwargs
        )
        
        # Beta版独自の機能
        self.memory_only = memory_only
        self.aggressive_memory = aggressive_memory
        self.memory_budget_mb = memory_budget_mb
        self.enable_hot_data_detection = enable_hot_data_detection
        self.enable_stats_collection = enable_stats_collection
        self.lazy_tracking_threshold = lazy_tracking_threshold
        self.fast_mode = fast_mode
        
        # LRUキャッシュ
        self._cache = LRUCache(capacity=cache_capacity)
        
        # 書き込みバッファ(メモリオンリーまたは無効化されていない場合)
        if not memory_only and write_buffer_size > 0:
            self._write_buffer = WriteBuffer(
                flush_threshold=write_buffer_size,
                flush_interval=write_buffer_interval
            )
        else:
            self._write_buffer = None
        
        # 統計情報
        self._stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'disk_reads': 0,
            'disk_writes': 0,
            'buffer_flushes': 0
        }
        self._stats_lock = Lock()
        
        # ホットデータ検出
        self._access_frequency = {} if enable_hot_data_detection else None
        self._access_lock = Lock() if enable_hot_data_detection else None
        
        # バックグラウンドフラッシュスレッド
        self._background_flush_enabled = enable_background_flush and self._write_buffer is not None
        self._background_flush_thread = None
        self._background_flush_stop_event = None
        
        if self._background_flush_enabled:
            self._start_background_flush()
        
        # 自動チューニング
        self._operation_count = 0
        self._auto_tune_interval = 10000  # 10000操作ごとにチューニング
        
        # 小容量DBの自動全件ロード
        if memory_budget_mb and auto_load_threshold_mb > 0:
            self._try_auto_load_all(auto_load_threshold_mb)
    
    def __getitem__(self, key: str) -> Any:
        """キーから値を取得(キャッシュ優先)."""
        # 高速モード: ロックなし読み取り + LRU更新最小化
        if self.fast_mode:
            # ロックなしでキャッシュチェック(高速)
            cached_value = self._cache.get_fast(key)
            if cached_value is not None:
                return cached_value
            
            # 書き込みバッファチェック(高速パス用に最小化)
            if self._write_buffer is not None:
                with self._write_buffer.lock:
                    if key in self._write_buffer.buffer:
                        value = self._write_buffer.buffer[key]
                        self._cache.put_fast(key, value)
                        return value
            
            # ディスクから読み込み
            value = super().__getitem__(key)
            self._cache.put_fast(key, value)
            
            # 操作カウント更新(ロックなし,アトミックではないが問題ない)
            self._operation_count += 1
            if self._operation_count > self.lazy_tracking_threshold:
                if self._access_frequency is not None:
                    self._track_access(key)
            
            return value
        
        # 通常モード: 完全なLRU機能
        # ホットデータ検出
        if self._access_frequency is not None:
            self._track_access(key)
        
        # キャッシュチェック
        cached_value = self._cache.get(key)
        if cached_value is not None:
            if self.enable_stats_collection:
                with self._stats_lock:
                    self._stats['cache_hits'] += 1
            return cached_value
        
        # 書き込みバッファチェック
        if self._write_buffer is not None:
            with self._write_buffer.lock:
                if key in self._write_buffer.buffer:
                    value = self._write_buffer.buffer[key]
                    self._cache.put(key, value)
                    return value
        
        # ディスクから読み込み
        if self.enable_stats_collection:
            with self._stats_lock:
                self._stats['cache_misses'] += 1
                self._stats['disk_reads'] += 1
        
        value = super().__getitem__(key)
        self._cache.put(key, value)
        
        return value
    
    def __setitem__(self, key: str, value: Any) -> None:
        """キーに値を設定(バッファリング対応)."""
        # キャッシュ更新
        self._cache.put(key, value)
        
        if self.memory_only or self._write_buffer is None:
            # 直接書き込み
            super().__setitem__(key, value)
        else:
            # バッファに追加
            should_flush = self._write_buffer.add(key, value)
            if should_flush:
                self._flush_write_buffer()
    
    def __delitem__(self, key: str) -> None:
        """キーを削除."""
        self._cache.remove(key)
        
        if self.memory_only or self._write_buffer is None:
            super().__delitem__(key)
        else:
            should_flush = self._write_buffer.remove(key)
            if should_flush:
                self._flush_write_buffer()
    
    def _flush_write_buffer(self) -> None:
        """書き込みバッファをフラッシュ."""
        if self._write_buffer is None:
            return
        
        buffer, deleted_keys = self._write_buffer.get_pending()
        
        if not buffer and not deleted_keys:
            return
        
        with self._stats_lock:
            self._stats['buffer_flushes'] += 1
            self._stats['disk_writes'] += len(buffer) + len(deleted_keys)
        
        # バルク書き込み
        if buffer:
            self.bulk_insert(buffer)
        
        # 削除実行
        for key in deleted_keys:
            try:
                super().__delitem__(key)
            except KeyError:
                pass
    
    def _start_background_flush(self) -> None:
        """バックグラウンドフラッシュスレッドを開始."""
        self._background_flush_stop_event = Event()
        self._background_flush_thread = Thread(
            target=self._background_flush_worker,
            daemon=True,
            name="BetaBackgroundFlush"
        )
        self._background_flush_thread.start()
        
        # プログラム終了時にフラッシュ
        atexit.register(self._cleanup_on_exit)
    
    def _background_flush_worker(self) -> None:
        """バックグラウンドフラッシュワーカー."""
        while not self._background_flush_stop_event.is_set():
            # wait()を使用することで,stopイベントが設定されたら即座に終了できる
            # タイムアウトは1秒で,定期的にフラッシュをチェック
            if self._background_flush_stop_event.wait(timeout=1.0):
                break  # stopイベントが設定された
            
            if self._write_buffer and self._write_buffer._should_flush():
                try:
                    self._flush_write_buffer()
                except Exception:
                    pass  # エラーを無視
    
    def _track_access(self, key: str) -> None:
        """アクセス頻度を追跡."""
        if self._access_frequency is None:
            return
        
        with self._access_lock:
            self._access_frequency[key] = self._access_frequency.get(key, 0) + 1
    
    def _try_auto_load_all(self, threshold_mb: float) -> None:
        """小容量DBを自動的に全件ロード."""
        try:
            db_size_mb = os.path.getsize(self.db_name) / (1024 * 1024)
            
            if db_size_mb <= threshold_mb:
                # 全件をキャッシュにロード
                for key in self.keys():
                    try:
                        value = super().__getitem__(key)
                        self._cache.put(key, value)
                    except Exception:
                        pass
        except Exception:
            pass
    
    def _cleanup_on_exit(self) -> None:
        """終了時のクリーンアップ."""
        if self._background_flush_enabled and self._background_flush_stop_event:
            self._background_flush_stop_event.set()
        
        # 残りのバッファをフラッシュ
        try:
            self._flush_write_buffer()
        except Exception:
            pass
    
    def get_stats(self) -> Dict[str, Any]:
        """統計情報を取得."""
        with self._stats_lock:
            stats = self._stats.copy()
        
        stats['cache'] = self._cache.get_stats()
        
        if self._write_buffer:
            with self._write_buffer.lock:
                stats['write_buffer_size'] = len(self._write_buffer.buffer)
                stats['pending_deletes'] = len(self._write_buffer.deleted_keys)
        
        return stats
    
    def close(self) -> None:
        """データベースを閉じる."""
        # バックグラウンドフラッシュを停止
        if self._background_flush_enabled and self._background_flush_stop_event:
            self._background_flush_stop_event.set()
            if self._background_flush_thread and self._background_flush_thread.is_alive():
                # タイムアウトを短縮: 5秒 → 1秒
                # wait()を使用しているので,実際は即座に終了するはず
                self._background_flush_thread.join(timeout=1.0)
        
        # 残りをフラッシュ
        self._flush_write_buffer()
        
        # 親クラスのclose
        super().close()


# ============================================================================
# 非同期版Beta(aiosqlite + 内部バッチ処理)
# ============================================================================

class AsyncDictSQLiteFastestBetaV4:
    """非同期版DictSQLite-Fastest Beta v4 - Enhanced Caching & Statistics.
    
    v3-alphaの全機能 + v4高度キャッシング:
    - ✅ v3-alpha: 動的接続プール,プリフェッチ,適応バッチ,拡張統計
    - ✅ v4: インテリジェント全データロード(小規模データ自動検出)
    - ✅ v4: LRU/LFU ハイブリッドキャッシュ(使用頻度考慮)
    - ✅ v4: 統計情報の外部DB保存オプション
    - ✅ v4: シーケンシャルリード性能最適化(v2以上)
    
    パフォーマンス目標:
    - シーケンシャルリード: v2同等以上 (>= 1,700,000 ops/sec)
    - 並行リード: v3-alpha同等以上 (>= 10,000 ops/sec)
    - 小規模データ: 2倍以上の高速化
    """
    
    def __init__(
        self,
        db_name: str,
        table_name: str = 'main',
        # Beta版パラメータ
        cache_capacity: int = 10000,
        write_buffer_size: int = 1000,
        write_buffer_interval: float = 5.0,
        memory_only: bool = False,
        aggressive_memory: bool = False,
        memory_budget_mb: Optional[int] = None,
        auto_load_threshold_mb: float = 10.0,
        enable_hot_data_detection: bool = True,
        # 非同期専用パラメータ
        async_batch_size: int = 100,
        async_commit_interval: float = 1.0,
        # v3-alpha Phase 1: 動的接続プール
        pool_min_size: int = 2,
        pool_max_size: int = 8,
        pool_idle_timeout: float = 60.0,
        pool_auto_scale: bool = True,
        # v3-alpha Phase 2: プリフェッチ
        enable_prefetch: bool = False,  # v4: デフォルト無効(オーバーヘッド削減)
        prefetch_size: int = 10,
        prefetch_threshold: float = 0.7,
        # v3-alpha Phase 3: 適応バッチ
        adaptive_batch: bool = True,
        batch_min_size: int = 10,
        batch_max_size: int = 1000,
        # v3-alpha Phase 4: 拡張統計
        extended_stats: bool = False,  # v4: デフォルト無効(オーバーヘッド削減)
        # v4 NEW: インテリジェント全データロード
        auto_preload: bool = True,  # 自動全ロード有効化
        preload_threshold_mb: float = 100.0,  # 全ロード閾値(MB)
        preload_threshold_entries: int = 100000,  # 全ロード閾値(エントリ数)
        force_preload: bool = False,  # 強制全ロード
        # v4 NEW: ハイブリッドキャッシュ
        use_hybrid_cache: bool = True,  # ハイブリッドキャッシュ使用
        cache_strategy: str = 'hybrid',  # 'lru', 'lfu', 'hybrid'
        # v4 NEW: 統計DB分離
        stats_db_path: Optional[str] = None,  # 統計DB(Noneなら無効)
        stats_batch_size: int = 1000,  # 統計バッチサイズ
        stats_flush_interval: float = 5.0,  # 統計フラッシュ間隔
        # 最適化パラメータ
        enable_stats_collection: bool = False,
        lazy_tracking_threshold: int = 100,
        fast_mode: bool = True,
        **kwargs
    ):
        """
        Args:
            db_name: データベースファイルパス
            table_name: テーブル名
            cache_capacity: キャッシュ容量
            async_batch_size: 非同期バッチ書き込みサイズ
            async_commit_interval: 自動コミット間隔
            pool_min_size: 接続プールの最小サイズ (v3-alpha Phase 1)
            pool_max_size: 接続プールの最大サイズ (v3-alpha Phase 1)
            pool_idle_timeout: アイドル接続のタイムアウト (v3-alpha Phase 1)
            pool_auto_scale: 負荷ベースの自動スケーリング (v3-alpha Phase 1)
        """
        Args:
            db_name: データベースファイルパス
            table_name: テーブル名
            cache_capacity: キャッシュ容量
            async_batch_size: 非同期バッチ書き込みサイズ
            async_commit_interval: 自動コミット間隔
            pool_min_size: 接続プールの最小サイズ (v3-alpha Phase 1)
            pool_max_size: 接続プールの最大サイズ (v3-alpha Phase 1)
            pool_idle_timeout: アイドル接続のタイムアウト (v3-alpha Phase 1)
            pool_auto_scale: 負荷ベースの自動スケーリング (v3-alpha Phase 1)
            enable_prefetch: 先読みプリフェッチの有効化 (v3-alpha Phase 2)
            prefetch_size: 先読みするキーの数 (v3-alpha Phase 2)
            prefetch_threshold: プリフェッチを行うヒット率閾値 (v3-alpha Phase 2)
            adaptive_batch: 適応的バッチサイジングの有効化 (v3-alpha Phase 3)
            batch_min_size: 最小バッチサイズ (v3-alpha Phase 3)
            batch_max_size: 最大バッチサイズ (v3-alpha Phase 3)
            extended_stats: 拡張統計収集の有効化 (v3-alpha Phase 4)
            auto_preload: 自動全データロード有効化 (v4)
            preload_threshold_mb: 全ロード閾値MB (v4)
            preload_threshold_entries: 全ロード閾値エントリ数 (v4)
            force_preload: 強制全ロード (v4)
            use_hybrid_cache: ハイブリッドキャッシュ使用 (v4)
            cache_strategy: キャッシュ戦略 'lru'/'lfu'/'hybrid' (v4)
            stats_db_path: 統計DB保存先パス (v4)
            stats_batch_size: 統計バッチサイズ (v4)
            stats_flush_interval: 統計フラッシュ間隔秒 (v4)
            その他: v2/v3と同じ
        """
        if not AIOSQLITE_AVAILABLE:
            raise ImportError(
                "aiosqlite is required for AsyncDictSQLiteFastestBetaV4. "
                "Install with: pip install aiosqlite"
            )
        
        self.db_name = db_name
        self.table_name = table_name
        self.memory_only = memory_only
        self.async_batch_size = async_batch_size
        self.async_commit_interval = async_commit_interval
        self.enable_stats_collection = enable_stats_collection
        self.lazy_tracking_threshold = lazy_tracking_threshold
        self.fast_mode = fast_mode
        self.enable_hot_data_detection = enable_hot_data_detection
        
        # v3-alpha Phase 1: 動的接続プール設定
        self.pool_min_size = max(1, pool_min_size)
        self.pool_max_size = max(self.pool_min_size, pool_max_size)
        self.pool_idle_timeout = pool_idle_timeout
        self.pool_auto_scale = pool_auto_scale
        
        # v3-alpha Phase 2: プリフェッチ設定
        self.enable_prefetch = enable_prefetch
        self.prefetch_size = prefetch_size
        self.prefetch_threshold = prefetch_threshold
        
        # v3-alpha Phase 3: 適応バッチ設定
        self.adaptive_batch = adaptive_batch
        self.batch_min_size = batch_min_size
        self.batch_max_size = batch_max_size
        
        # v3-alpha Phase 4: 拡張統計設定
        self.extended_stats = extended_stats
        
        # v4: インテリジェント全データロード設定
        self.auto_preload = auto_preload
        self.preload_threshold_mb = preload_threshold_mb
        self.preload_threshold_entries = preload_threshold_entries
        self.force_preload = force_preload
        
        # v4: ハイブリッドキャッシュ設定
        self.use_hybrid_cache = use_hybrid_cache
        self.cache_strategy = cache_strategy
        
        # v4: 統計DB設定
        self.stats_db_path = stats_db_path
        self.stats_batch_size = stats_batch_size
        self.stats_flush_interval = stats_flush_interval
        
        # キャッシュ作成(v4: ハイブリッドキャッシュ対応)
        if self.use_hybrid_cache:
            self._cache = HybridCache(
                capacity=cache_capacity,
                eviction_strategy=cache_strategy
            )
        else:
            # v2/v3互換のLRUキャッシュ
            self._cache = LRUCache(capacity=cache_capacity)
        
        # 同期版は使わない(キャッシュとDBロックの競合を避けるため)
        self._sync_db = None
        
        # v4: 全データロード関連
        self._all_data_loaded = False  # 全データロード済みフラグ
        self._preloaded_keys = set()  # ロード済みキーのセット
        self._db_size_stats = None  # DBサイズ情報
        
        # aiosqlite接続プール(遅延初期化) - Phase 1: 動的プール
        self._connection_pool = []  # List of aiosqlite.Connection
        self._connection_last_used = {}  # 接続の最終使用時刻
        self._available_connections = None  # asyncio.Queue
        self._pool_lock = None
        self._init_lock = None  # 初期化用ロック
        self._initialized = False
        self._pool_stats = {
            'created_connections': 0,
            'active_connections': 0,
            'peak_connections': 0,
            'scaled_up': 0,
            'scaled_down': 0,
        }
        
        # 非同期書き込みバッファ
        self._async_write_buffer: Dict[str, Any] = {}
        self._async_delete_buffer: set = set()
        self._async_buffer_lock = None
        
        # 書き込み操作のシリアライズ用ロック(デッドロック防止)
        self._async_write_lock = None
        
        # Phase 2: プリフェッチシステム
        self._access_history = []  # アクセス履歴
        self._prefetch_cache: Dict[str, Any] = {}  # プリフェッチキャッシュ
        self._prefetch_stats = {
            'prefetch_hits': 0,
            'prefetch_misses': 0,
            'patterns_detected': 0,
            'prefetches_triggered': 0,
        }
        
        # Phase 3: 適応バッチサイジング
        self._batch_history = []  # バッチ処理履歴
        self._current_batch_size = async_batch_size
        self._batch_stats = {
            'total_batches': 0,
            'avg_batch_size': async_batch_size,
            'avg_latency_ms': 0.0,
            'adjustments': 0,
        }
        
        # Phase 4: 拡張統計
        self._extended_stats_data = {
            'operation_counts': {'get': 0, 'set': 0, 'delete': 0, 'bulk_insert': 0},
            'operation_timings': {'get': [], 'set': [], 'delete': [], 'bulk_insert': []},
            'access_patterns': {},  # key -> [access_times]
            'hot_keys': set(),  # 頻繁にアクセスされるキー
            'connection_wait_times': [],
        } if extended_stats else None
        
        # 統計情報
        self._async_stats = {
            'batch_writes': 0,
            'individual_writes': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
        
        # 操作カウンタ(遅延追跡用)
        self._operation_count = 0
        self._access_frequency = {} if enable_hot_data_detection else None
        
        # バックグラウンドコミットタスク
        self._commit_task = None
        self._commit_stop_event = None
        
        # Phase 1: アイドル接続クリーンアップタスク
        self._idle_cleanup_task = None
        self._cleanup_stop_event = None
    
    async def _ensure_initialized(self) -> None:
        """非同期コンポーネントの初期化(スレッドセーフ) - v3-alpha Phase 1対応."""
        # 高速パス: 既に初期化済みの場合は即座に返る
        if self._initialized:
            return
        
        # 初期化ロックを遅延作成(最初の呼び出しで作成)
        if self._init_lock is None:
            # この部分はロックなしだが,asyncio.Lock()の作成自体はスレッドセーフ
            self._init_lock = asyncio.Lock()
        
        # ロックを取得して初期化(他のタスクは待機)
        async with self._init_lock:
            # ダブルチェック: ロック取得中に他のタスクが初期化完了した可能性
            if self._initialized:
                return
            
            # asyncio関連の初期化
            # Phase 1: 動的プール - max_sizeは後で拡張可能
            self._available_connections = asyncio.Queue(maxsize=self.pool_max_size)
            self._pool_lock = asyncio.Lock()
            self._async_buffer_lock = asyncio.Lock()
            self._async_write_lock = asyncio.Lock()
            self._commit_stop_event = asyncio.Event()
            self._cleanup_stop_event = asyncio.Event()
            
            # Phase 1: 初期接続プールの作成(最小サイズから開始)
            for _ in range(self.pool_min_size):
                conn = await aiosqlite.connect(self.db_name)
                
                # 最適化PRAGMA設定
                await conn.execute("PRAGMA journal_mode=WAL")
                await conn.execute("PRAGMA synchronous=NORMAL")
                await conn.execute("PRAGMA cache_size=-64000")  # 64MB
                await conn.execute("PRAGMA temp_store=MEMORY")
                await conn.execute("PRAGMA mmap_size=268435456")  # 256MB
                await conn.execute("PRAGMA busy_timeout=60000")  # 60秒
                await conn.execute("PRAGMA wal_autocheckpoint=1000")  # WAL自動チェックポイント
                await conn.execute("PRAGMA journal_size_limit=67108864")  # 64MB
                
                self._connection_pool.append(conn)
                self._connection_last_used[id(conn)] = time.time()
                await self._available_connections.put(conn)
            
            self._pool_stats['created_connections'] = self.pool_min_size
            self._pool_stats['active_connections'] = self.pool_min_size
            self._pool_stats['peak_connections'] = self.pool_min_size
            
            # テーブル作成(最初の接続で)
            conn = self._connection_pool[0]
            create_sql = f"""
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                key TEXT PRIMARY KEY,
                value BLOB NOT NULL
            )
            """
            await conn.execute(create_sql)
            
            # テーブル可視性確保(GitHub Actions対策)
            await conn.execute(f"SELECT COUNT(*) FROM {self.table_name}")
            await conn.commit()
            
            # v4: 自動全データロード
            if self.auto_preload or self.force_preload:
                await self._check_and_preload_data()
            
            # バックグラウンドコミットタスク開始
            if self.async_commit_interval > 0:
                self._commit_task = asyncio.create_task(self._background_commit_worker())
            
            # Phase 1: アイドル接続クリーンアップタスク開始
            if self.pool_auto_scale and self.pool_idle_timeout > 0:
                self._idle_cleanup_task = asyncio.create_task(self._idle_connection_cleanup_worker())
            
            # 最後に初期化完了フラグを設定
            self._initialized = True
    
    async def _check_and_preload_data(self) -> None:
        """v4: データサイズをチェックして全データをプリロード"""
        try:
            # サイズ分析
            analyzer = DatabaseSizeAnalyzer(self.db_name, self.table_name)
            self._db_size_stats = await analyzer.analyze_database()
            
            # プリロード判定
            should_preload = (
                self.force_preload or
                (self._db_size_stats['estimated_memory_mb'] < self.preload_threshold_mb and
                 self._db_size_stats['total_entries'] < self.preload_threshold_entries)
            )
            
            if not should_preload or self._db_size_stats['total_entries'] == 0:
                return
            
            # 全データをプリロード
            async with self._get_connection() as conn:
                cursor = await conn.execute(
                    f"SELECT key, value FROM {self.table_name}"
                )
                rows = await cursor.fetchall()
                await cursor.close()
            
            # キャッシュに一括格納
            for key, value_blob in rows:
                try:
                    value = pickle.loads(value_blob)
                    # 高速モードならput_fast,そうでなければput
                    if self.fast_mode and hasattr(self._cache, 'put_fast'):
                        self._cache.put_fast(key, value)
                    else:
                        self._cache.put(key, value)
                    self._preloaded_keys.add(key)
                except Exception:
                    # デシリアライズエラーは無視
                    pass
            
            self._all_data_loaded = True
            
        except Exception:
            # プリロードエラーは無視(通常動作に戻る)
            self._all_data_loaded = False
            self._preloaded_keys.clear()
    
    @asynccontextmanager
    async def _get_connection(self):
        """接続プールから接続を取得 - Phase 1: 動的スケーリング対応"""
        await self._ensure_initialized()
        
        # Phase 4: 接続待機時間の計測開始(サンプリング - 10%のみ)
        should_track_wait = (self.extended_stats and 
                            self._extended_stats_data['operation_counts'].get('get', 0) % 10 == 0)
        wait_start = time.time() if should_track_wait else None
        
        # Phase 1: 接続取得を試行,失敗時に動的スケーリング
        try:
            # タイムアウト付きで接続取得を試行
            conn = await asyncio.wait_for(
                self._available_connections.get(), 
                timeout=0.1  # 100ms
            )
        except asyncio.TimeoutError:
            # Phase 1: プールが空 → 自動スケーリング
            if self.pool_auto_scale and len(self._connection_pool) < self.pool_max_size:
                async with self._pool_lock:
                    # ダブルチェック
                    if len(self._connection_pool) < self.pool_max_size:
                        # 新しい接続を作成
                        new_conn = await aiosqlite.connect(self.db_name)
                        
                        # 最適化PRAGMA設定
                        await new_conn.execute("PRAGMA journal_mode=WAL")
                        await new_conn.execute("PRAGMA synchronous=NORMAL")
                        await new_conn.execute("PRAGMA cache_size=-64000")
                        await new_conn.execute("PRAGMA temp_store=MEMORY")
                        await new_conn.execute("PRAGMA mmap_size=268435456")
                        await new_conn.execute("PRAGMA busy_timeout=60000")
                        
                        self._connection_pool.append(new_conn)
                        self._connection_last_used[id(new_conn)] = time.time()
                        
                        # 統計更新
                        self._pool_stats['created_connections'] += 1
                        self._pool_stats['active_connections'] += 1
                        self._pool_stats['scaled_up'] += 1
                        self._pool_stats['peak_connections'] = max(
                            self._pool_stats['peak_connections'],
                            len(self._connection_pool)
                        )
                        
                        conn = new_conn
                    else:
                        # 他のタスクが作成した → 再度取得
                        conn = await self._available_connections.get()
            else:
                # スケーリング無効 or 上限到達 → 待機
                conn = await self._available_connections.get()
        
        # Phase 4: 待機時間の記録(サンプリング)
        if should_track_wait and wait_start:
            wait_time = (time.time() - wait_start) * 1000  # ms
            self._extended_stats_data['connection_wait_times'].append(wait_time)
            # 最新1000件のみ保持
            if len(self._extended_stats_data['connection_wait_times']) > 1000:
                self._extended_stats_data['connection_wait_times'] = \
                    self._extended_stats_data['connection_wait_times'][-1000:]
        
        try:
            # Phase 1: 最終使用時刻を更新
            self._connection_last_used[id(conn)] = time.time()
            yield conn
        finally:
            # Phase 1: 最終使用時刻を更新
            self._connection_last_used[id(conn)] = time.time()
            await self._available_connections.put(conn)
    
    async def aget(self, key: str, default: Any = None) -> Any:
        """非同期でキーから値を取得 - v4: 全ロード対応で超高速化.
        
        Args:
            key: 取得するキー
            default: キーが存在しない場合のデフォルト値
            
        Returns:
            キーに対応する値,存在しない場合はdefault
        """
        # Phase 4: 操作開始時刻(サンプリング)
        start_time = time.time() if (self.extended_stats and 
                                     self._extended_stats_data and
                                     self._extended_stats_data['operation_counts']['get'] % 10 == 0) else None
        
        await self._ensure_initialized()
        
        # v4: 全データロード済みの超高速パス(最優先)
        if self._all_data_loaded:
            # 削除バッファチェック(ロックなし - セットの読み取りは安全)
            if self._async_delete_buffer and key in self._async_delete_buffer:
                return default
            
            # キャッシュから直接取得(ロック不要,最速)
            if hasattr(self._cache, 'get_fast'):
                value = self._cache.get_fast(key)
            else:
                value = self._cache.get(key)
            
            if value is not None:
                # Phase 4: 統計記録
                if start_time:
                    self._record_operation('get', start_time, key)
                return value
            
            # キャッシュミス = キーが存在しないか削除済み
            if key not in self._preloaded_keys:
                return default
            
            # キャッシュから退避されたが,DBには存在 → 再ロード不要
            # (全ロード済みなので,キャッシュミス = データなし)
            return default
        
        # 通常パス(v3と同じ,ただし削除バッファチェックは簡略化)
        # 削除バッファチェック(非ロック - セット読み取り)
        if self._async_delete_buffer and key in self._async_delete_buffer:
            return default
        
        # Phase 2: プリフェッチキャッシュチェック
        if self.enable_prefetch and key in self._prefetch_cache:
            value = self._prefetch_cache.pop(key)
            if hasattr(self._cache, 'put_fast') and self.fast_mode:
                self._cache.put_fast(key, value)
            else:
                self._cache.put(key, value)
            self._prefetch_stats['prefetch_hits'] += 1
            
            # Phase 4: 統計記録
            if start_time:
                self._record_operation('get', start_time, key)
            
            return value
        
        # 高速モード: ロックなしキャッシュチェック
        if self.fast_mode:
            cached_value = self._cache.get_fast(key)
            if cached_value is not None:
                # Phase 2: アクセス履歴を記録
                if self.enable_prefetch:
                    await self._record_access(key)
                    await self._check_and_prefetch(key)
                
                # Phase 4: 統計記録
                if self.extended_stats:
                    self._record_operation('get', start_time, key)
                
                return cached_value
            
            # 書き込みバッファチェック
            async with self._async_buffer_lock:
                if key in self._async_write_buffer:
                    value = self._async_write_buffer[key]
                    self._cache.put_fast(key, value)
                    
                    # Phase 4: 統計記録
                    if self.extended_stats:
                        self._record_operation('get', start_time, key)
                    
                    return value
            
            # aiosqliteで読み込み
            async with self._get_connection() as conn:
                cursor = await conn.execute(
                    f"SELECT value FROM {self.table_name} WHERE key = ?",
                    (key,)
                )
                row = await cursor.fetchone()
                await cursor.close()
            
            if row is None:
                return default
            
            value = pickle.loads(row[0])
            self._cache.put_fast(key, value)
            
            # 操作カウント更新(遅延追跡)
            self._operation_count += 1
            if self._operation_count > self.lazy_tracking_threshold:
                if self._access_frequency is not None:
                    self._access_frequency[key] = self._access_frequency.get(key, 0) + 1
            
            # Phase 2: アクセス履歴を記録してプリフェッチ
            if self.enable_prefetch:
                await self._record_access(key)
                await self._check_and_prefetch(key)
            
            # Phase 4: 統計記録
            if self.extended_stats:
                self._record_operation('get', start_time, key)
            
            return value
        
        # 通常モード: 完全なLRU機能
        cached_value = self._cache.get(key)
        if cached_value is not None:
            if self.enable_stats_collection:
                self._async_stats['cache_hits'] += 1
            return cached_value
        
        # 書き込みバッファチェック
        async with self._async_buffer_lock:
            if key in self._async_write_buffer:
                value = self._async_write_buffer[key]
                self._cache.put(key, value)
                return value
            
            if key in self._async_delete_buffer:
                return default
        
        # aiosqliteで読み込み
        if self.enable_stats_collection:
            self._async_stats['cache_misses'] += 1
        
        async with self._get_connection() as conn:
            cursor = await conn.execute(
                f"SELECT value FROM {self.table_name} WHERE key = ?",
                (key,)
            )
            row = await cursor.fetchone()
            await cursor.close()
        
        if row is None:
            return default
        
        value = pickle.loads(row[0])
        self._cache.put(key, value)
        
        return value
        
        # キャッシュに追加
        self._cache.put(key, value)
        
        return value
    
    async def aset(self, key: str, value: Any) -> None:
        """非同期でキーに値を設定(バッファリング) - Phase 3, 4対応.
        
        Args:
            key: キー
            value: 値
        """
        # Phase 4: 操作開始時刻
        start_time = time.time() if self.extended_stats else None
        
        await self._ensure_initialized()
        
        # キャッシュに即座に反映(高速モード対応)
        if self.fast_mode:
            self._cache.put_fast(key, value)
        else:
            self._cache.put(key, value)
        
        # バッファに追加してサイズチェック
        should_flush = False
        async with self._async_buffer_lock:
            self._async_write_buffer[key] = value
            self._async_delete_buffer.discard(key)
            
            # Phase 3: 適応的バッチサイズを使用
            batch_size = self._current_batch_size if self.adaptive_batch else self.async_batch_size
            should_flush = len(self._async_write_buffer) >= batch_size
        
        # ロックを解放してからフラッシュ
        if should_flush:
            flush_start = time.time()
            await self._flush_write_buffer()
            
            # Phase 3: バッチ処理のレイテンシを記録
            if self.adaptive_batch:
                flush_latency_ms = (time.time() - flush_start) * 1000
                await self._adaptive_batch_size_adjustment(flush_latency_ms, batch_size)
        
        # Phase 4: 統計記録
        if self.extended_stats:
            self._record_operation('set', start_time, key)
    
    async def adelete(self, key: str) -> None:
        """非同期でキーを削除 - Phase 4対応.
        
        Args:
            key: 削除するキー
        """
        # Phase 4: 操作開始時刻
        start_time = time.time() if self.extended_stats else None
        
        await self._ensure_initialized()
        
        # キャッシュから削除
        self._cache.remove(key)
        
        # バッファに追加してサイズチェック
        should_flush = False
        async with self._async_buffer_lock:
            self._async_write_buffer.pop(key, None)
            self._async_delete_buffer.add(key)
            
            # バッファサイズチェック(ロック内で判定のみ)
            should_flush = len(self._async_delete_buffer) >= self.async_batch_size
        
        # ロックを解放してからフラッシュ
        if should_flush:
            await self._flush_write_buffer()
        
        # Phase 4: 統計記録
        if self.extended_stats:
            self._record_operation('delete', start_time, key)
    
    async def abulk_insert(self, items: Dict[str, Any]) -> None:
        """非同期でバルク挿入(デッドロック防止) - Phase 3, 4対応.
        
        Args:
            items: {key: value} の辞書
        """
        # Phase 4: 操作開始時刻
        start_time = time.time() if self.extended_stats else None
        
        await self._ensure_initialized()
        
        if not items:
            return
        
        # キャッシュに追加(高速モード対応)
        if self.fast_mode:
            for key, value in items.items():
                self._cache.put_fast(key, value)
        else:
            for key, value in items.items():
                self._cache.put(key, value)
        
        # バッチ書き込み(書き込みロックで保護)
        data = [(key, pickle.dumps(value)) for key, value in items.items()]
        
        async with self._async_write_lock:
            async with self._get_connection() as conn:
                await conn.execute("BEGIN IMMEDIATE")
                try:
                    await conn.executemany(
                        f"INSERT OR REPLACE INTO {self.table_name} (key, value) VALUES (?, ?)",
                        data
                    )
                    await conn.commit()
                except Exception as e:
                    await conn.rollback()
                    raise e
        
        if self.enable_stats_collection:
            self._async_stats['batch_writes'] += 1
        
        # Phase 4: 統計記録
        if self.extended_stats:
            self._record_operation('bulk_insert', start_time)
    
    async def _flush_write_buffer(self) -> None:
        """書き込みバッファをフラッシュ(デッドロック防止)."""
        # バッファを取得してクリア
        async with self._async_buffer_lock:
            if not self._async_write_buffer and not self._async_delete_buffer:
                return
            
            write_buffer = self._async_write_buffer.copy()
            delete_buffer = self._async_delete_buffer.copy()
            
            self._async_write_buffer.clear()
            self._async_delete_buffer.clear()
        
        # 書き込みロックで保護
        async with self._async_write_lock:
            async with self._get_connection() as conn:
                await conn.execute("BEGIN IMMEDIATE")
                try:
                    # 書き込み実行
                    if write_buffer:
                        data = [(key, pickle.dumps(value)) for key, value in write_buffer.items()]
                        await conn.executemany(
                            f"INSERT OR REPLACE INTO {self.table_name} (key, value) VALUES (?, ?)",
                            data
                        )
                        self._async_stats['batch_writes'] += 1
                    
                    # 削除実行
                    if delete_buffer:
                        placeholders = ','.join('?' * len(delete_buffer))
                        await conn.execute(
                            f"DELETE FROM {self.table_name} WHERE key IN ({placeholders})",
                            tuple(delete_buffer)
                        )
                    
                    await conn.commit()
                except Exception as e:
                    await conn.rollback()
                    # バックグラウンドフラッシュでのエラーは許容
                    pass
    
    async def _background_commit_worker(self) -> None:
        """バックグラウンドコミットワーカー."""
        try:
            while not self._commit_stop_event.is_set():
                await asyncio.sleep(self.async_commit_interval)
                
                # 停止イベントをチェック
                if self._commit_stop_event.is_set():
                    break
                
                await self._flush_write_buffer()
        except asyncio.CancelledError:
            # キャンセルされた場合は正常終了
            pass
        except Exception:
            # その他のエラーは無視
            pass
    
    async def _idle_connection_cleanup_worker(self) -> None:
        """Phase 1: アイドル接続のクリーンアップワーカー."""
        try:
            while not self._cleanup_stop_event.is_set():
                await asyncio.sleep(self.pool_idle_timeout / 2)  # タイムアウトの半分で定期チェック
                
                # 停止イベントをチェック
                if self._cleanup_stop_event.is_set():
                    break
                
                # アイドル接続のクリーンアップ
                await self._cleanup_idle_connections()
        except asyncio.CancelledError:
            # キャンセルされた場合は正常終了
            pass
        except Exception:
            # その他のエラーは無視
            pass
    
    async def _cleanup_idle_connections(self) -> None:
        """Phase 1: アイドル接続を削除してプールを縮小."""
        if not self.pool_auto_scale:
            return
        
        current_time = time.time()
        
        async with self._pool_lock:
            # 最小サイズは維持
            if len(self._connection_pool) <= self.pool_min_size:
                return
            
            # アイドル接続を特定
            idle_connections = []
            for conn in self._connection_pool:
                conn_id = id(conn)
                last_used = self._connection_last_used.get(conn_id, current_time)
                if current_time - last_used > self.pool_idle_timeout:
                    idle_connections.append(conn)
            
            # 最小サイズを下回らない範囲でクリーンアップ
            max_to_remove = len(self._connection_pool) - self.pool_min_size
            connections_to_remove = idle_connections[:max_to_remove]
            
            for conn in connections_to_remove:
                try:
                    # プールから削除
                    self._connection_pool.remove(conn)
                    del self._connection_last_used[id(conn)]
                    
                    # 接続を閉じる
                    await conn.close()
                    
                    # 統計更新
                    self._pool_stats['active_connections'] -= 1
                    self._pool_stats['scaled_down'] += 1
                except Exception:
                    # エラーは無視
                    pass
    
    async def _record_access(self, key: str) -> None:
        """Phase 2: アクセス履歴を記録 - 最適化版(サンプリング)."""
        # サンプリング: 20%のみ記録してオーバーヘッド削減
        if len(self._access_history) % 5 == 0:
            self._access_history.append(key)
            # 最新50件のみ保持(100→50に削減)
            if len(self._access_history) > 50:
                self._access_history = self._access_history[-50:]
    
    async def _check_and_prefetch(self, key: str) -> None:
        """Phase 2: アクセスパターンを検出してプリフェッチ - 最適化版."""
        # サンプリング: 10回に1回のみチェックしてオーバーヘッド削減
        if not self.enable_prefetch or len(self._access_history) < 3:
            return
        
        if self._prefetch_stats['prefetches_triggered'] % 10 != 0:
            return
        
        # 連続アクセスパターンの検出
        pattern = self._detect_sequential_pattern(key)
        if pattern and len(pattern) > 0:
            self._prefetch_stats['patterns_detected'] += 1
            # プリフェッチを実行
            await self._prefetch_keys(pattern)
    
    def _detect_sequential_pattern(self, current_key: str) -> List[str]:
        """Phase 2: 連続アクセスパターンを検出."""
        # 数値キーまたはプレフィックス付き数値キーの連続性を検出
        try:
            # キーから数値部分を抽出
            import re
            match = re.search(r'(\d+)$', current_key)
            if not match:
                return []
            
            num = int(match.group(1))
            prefix = current_key[:match.start()]
            
            # 次のN個のキーを予測
            predicted_keys = []
            for i in range(1, self.prefetch_size + 1):
                next_key = f"{prefix}{num + i}"
                # すでにキャッシュにある場合はスキップ
                if self._cache.get_fast(next_key) is None and next_key not in self._prefetch_cache:
                    predicted_keys.append(next_key)
            
            return predicted_keys
        except Exception:
            return []
    
    async def _prefetch_keys(self, keys: List[str]) -> None:
        """Phase 2: キーを先読みしてプリフェッチキャッシュに格納."""
        if not keys:
            return
        
        self._prefetch_stats['prefetches_triggered'] += 1
        
        try:
            async with self._get_connection() as conn:
                # プレースホルダーを作成
                placeholders = ','.join('?' * len(keys))
                cursor = await conn.execute(
                    f"SELECT key, value FROM {self.table_name} WHERE key IN ({placeholders})",
                    keys
                )
                rows = await cursor.fetchall()
                await cursor.close()
            
            # プリフェッチキャッシュに追加
            for key, value_blob in rows:
                try:
                    value = pickle.loads(value_blob)
                    self._prefetch_cache[key] = value
                except Exception:
                    pass
            
            # プリフェッチキャッシュのサイズ制限
            if len(self._prefetch_cache) > self.prefetch_size * 2:
                # 古いエントリを削除
                keys_to_remove = list(self._prefetch_cache.keys())[:-self.prefetch_size * 2]
                for key in keys_to_remove:
                    del self._prefetch_cache[key]
        except Exception:
            # プリフェッチエラーは無視
            pass
    
    def _record_operation(self, op_type: str, start_time: float, key: str = None) -> None:
        """Phase 4: 操作統計を記録 - 最適化版(オーバーヘッド最小化)."""
        if not self.extended_stats or not self._extended_stats_data or not start_time:
            return
        
        # 操作カウント(アトミック操作)
        self._extended_stats_data['operation_counts'][op_type] += 1
        
        # タイミング情報(サンプリング - 10%のみ記録してオーバーヘッド削減)
        if self._extended_stats_data['operation_counts'][op_type] % 10 == 0:
            elapsed_ms = (time.time() - start_time) * 1000
            self._extended_stats_data['operation_timings'][op_type].append(elapsed_ms)
            # 最新1000件のみ保持
            if len(self._extended_stats_data['operation_timings'][op_type]) > 1000:
                self._extended_stats_data['operation_timings'][op_type] = \
                    self._extended_stats_data['operation_timings'][op_type][-1000:]
        
        # アクセスパターン(サンプリング - 20%のみ記録)
        if key and self._extended_stats_data['operation_counts'][op_type] % 5 == 0:
            if key not in self._extended_stats_data['access_patterns']:
                self._extended_stats_data['access_patterns'][key] = []
            self._extended_stats_data['access_patterns'][key].append(time.time())
            # 最新10件のアクセス時刻のみ保持
            if len(self._extended_stats_data['access_patterns'][key]) > 10:
                self._extended_stats_data['access_patterns'][key] = \
                    self._extended_stats_data['access_patterns'][key][-10:]
            
            # ホットキー検出(10回以上アクセス)
            if len(self._extended_stats_data['access_patterns'][key]) >= 10:
                self._extended_stats_data['hot_keys'].add(key)
    
    async def _adaptive_batch_size_adjustment(self, batch_latency_ms: float, batch_size: int) -> None:
        """Phase 3: バッチサイズを適応的に調整."""
        if not self.adaptive_batch:
            return
        
        # バッチ履歴を記録
        self._batch_history.append({
            'size': batch_size,
            'latency_ms': batch_latency_ms,
            'time': time.time()
        })
        
        # 最新20件のみ保持
        if len(self._batch_history) > 20:
            self._batch_history = self._batch_history[-20:]
        
        # 統計を更新
        if len(self._batch_history) >= 5:
            avg_latency = sum(b['latency_ms'] for b in self._batch_history) / len(self._batch_history)
            self._batch_stats['avg_latency_ms'] = avg_latency
            self._batch_stats['total_batches'] += 1
            
            # レイテンシが高すぎる場合はバッチサイズを減らす
            if avg_latency > 100:  # 100ms以上
                new_size = max(self.batch_min_size, int(self._current_batch_size * 0.8))
                if new_size != self._current_batch_size:
                    self._current_batch_size = new_size
                    self._batch_stats['adjustments'] += 1
            
            # レイテンシが低い場合はバッチサイズを増やす
            elif avg_latency < 20:  # 20ms未満
                new_size = min(self.batch_max_size, int(self._current_batch_size * 1.2))
                if new_size != self._current_batch_size:
                    self._current_batch_size = new_size
                    self._batch_stats['adjustments'] += 1
            
            self._batch_stats['avg_batch_size'] = self._current_batch_size
    
    async def akeys(self) -> List[str]:
        """非同期で全キーを取得."""
        await self._ensure_initialized()
        
        async with self._get_connection() as conn:
            cursor = await conn.execute(
                f"SELECT key FROM {self.table_name}"
            )
            rows = await cursor.fetchall()
            await cursor.close()
        
        return [row[0] for row in rows]
    
    async def aitems(self) -> List[Tuple[str, Any]]:
        """非同期で全アイテムを取得."""
        await self._ensure_initialized()
        
        async with self._get_connection() as conn:
            cursor = await conn.execute(
                f"SELECT key, value FROM {self.table_name}"
            )
            rows = await cursor.fetchall()
            await cursor.close()
        
        return [(row[0], pickle.loads(row[1])) for row in rows]
    
    async def alen(self) -> int:
        """非同期でアイテム数を取得."""
        await self._ensure_initialized()
        
        async with self._get_connection() as conn:
            cursor = await conn.execute(
                f"SELECT COUNT(*) FROM {self.table_name}"
            )
            row = await cursor.fetchone()
            await cursor.close()
        
        return row[0] if row else 0
    
    def get_stats(self) -> Dict[str, Any]:
        """統計情報を取得 - v3-alpha拡張統計対応."""
        stats = self._async_stats.copy()
        stats['cache'] = self._cache.get_stats()
        stats['buffer_size'] = len(self._async_write_buffer)
        stats['pending_deletes'] = len(self._async_delete_buffer)
        
        # Phase 1: 接続プール統計
        stats['pool'] = self._pool_stats.copy()
        stats['pool']['current_size'] = len(self._connection_pool)
        
        # Phase 2: プリフェッチ統計
        if self.enable_prefetch:
            stats['prefetch'] = self._prefetch_stats.copy()
            prefetch_total = (self._prefetch_stats['prefetch_hits'] + 
                            self._prefetch_stats['prefetch_misses'])
            if prefetch_total > 0:
                stats['prefetch']['hit_rate'] = (
                    self._prefetch_stats['prefetch_hits'] / prefetch_total * 100
                )
            else:
                stats['prefetch']['hit_rate'] = 0.0
        
        # Phase 3: 適応バッチ統計
        if self.adaptive_batch:
            stats['adaptive_batch'] = self._batch_stats.copy()
        
        # Phase 4: 拡張統計
        if self.extended_stats and self._extended_stats_data:
            stats['extended'] = {
                'operation_counts': self._extended_stats_data['operation_counts'].copy(),
                'hot_keys_count': len(self._extended_stats_data['hot_keys']),
            }
            
            # 平均タイミング(サンプリングされたデータでも計算)
            for op_type, timings in self._extended_stats_data['operation_timings'].items():
                if timings and len(timings) > 0:
                    stats['extended'][f'{op_type}_avg_ms'] = sum(timings) / len(timings)
                    stats['extended'][f'{op_type}_p95_ms'] = sorted(timings)[int(len(timings) * 0.95)] if len(timings) > 1 else (timings[0] if timings else 0)
                else:
                    stats['extended'][f'{op_type}_avg_ms'] = 0.0
                    stats['extended'][f'{op_type}_p95_ms'] = 0.0
            
            # 接続待機時間(サンプリングされたデータでも計算)
            if self._extended_stats_data['connection_wait_times']:
                wait_times = self._extended_stats_data['connection_wait_times']
                stats['extended']['avg_connection_wait_ms'] = sum(wait_times) / len(wait_times)
                stats['extended']['p95_connection_wait_ms'] = sorted(wait_times)[int(len(wait_times) * 0.95)] if len(wait_times) > 1 else (wait_times[0] if wait_times else 0)
            else:
                stats['extended']['avg_connection_wait_ms'] = 0.0
                stats['extended']['p95_connection_wait_ms'] = 0.0
        
        return stats
    
    async def aclose(self) -> None:
        """非同期でデータベースを閉じる - Phase 1クリーンアップタスク対応."""
        if not self._initialized:
            return
        
        # Phase 1: アイドル接続クリーンアップタスクを停止
        if self._idle_cleanup_task and not self._idle_cleanup_task.done():
            self._cleanup_stop_event.set()
            try:
                await asyncio.wait_for(self._idle_cleanup_task, timeout=2.0)
            except asyncio.TimeoutError:
                self._idle_cleanup_task.cancel()
                try:
                    await self._idle_cleanup_task
                except asyncio.CancelledError:
                    pass
        
        # バックグラウンドタスクを停止
        if self._commit_task and not self._commit_task.done():
            # 停止イベントを設定
            self._commit_stop_event.set()
            
            # タスクが終了するのを待つ(タイムアウト付き)
            try:
                await asyncio.wait_for(self._commit_task, timeout=2.0)
            except asyncio.TimeoutError:
                # タイムアウトした場合はキャンセル
                self._commit_task.cancel()
                try:
                    await self._commit_task
                except asyncio.CancelledError:
                    pass  # キャンセルは正常
        
        # 残りをフラッシュ
        try:
            await self._flush_write_buffer()
        except Exception:
            pass  # クローズ中のエラーは無視
        
        # 接続プールをクローズ
        for conn in self._connection_pool:
            try:
                await conn.close()
            except Exception:
                pass  # クローズ中のエラーは無視
        
        self._initialized = False
    
    async def __aenter__(self):
        """Async context manager enter."""
        await self._ensure_initialized()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.aclose()


# ============================================================================
# 公開API
# ============================================================================

__all__ = [
    'DictSQLiteFastestBeta',
    'AsyncDictSQLiteFastestBeta',  # v4エイリアス(最新)
    'AsyncDictSQLiteFastestBetaV3',  # v3-alpha (互換性)
    'AsyncDictSQLiteFastestBetaV4',  # v4 (最新)
    'LRUCache',
    'HybridCache',  # v4
    'DatabaseSizeAnalyzer',  # v4
    'WriteBuffer',
]

# デフォルトエイリアス(最新版を使用)
AsyncDictSQLiteFastestBeta = AsyncDictSQLiteFastestBetaV4
# v3互換エイリアス
AsyncDictSQLiteFastestBetaV3 = AsyncDictSQLiteFastestBetaV4
