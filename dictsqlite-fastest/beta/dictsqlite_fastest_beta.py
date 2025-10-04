"""DictSQLite-Fastest Beta - メモリ最優先の高速化実装.

このモジュールは、ディスクアクセスを最小限に抑え、メモリからのアクセスを
最大化することで、最高のパフォーマンスを実現します。

主な機能:
- LRUキャッシュによるホットデータのメモリ保持
- 書き込みバッファリング（バッチ書き込み）
- 先読みキャッシング戦略
- アグレッシブなメモリPRAGMA設定
- オプションの完全メモリモード
- メモリ予算に基づく自動最適化（新機能）
- バックグラウンド自動フラッシュ（新機能）
- 小容量データベースの完全メモリロード（新機能）
- 頻繁に使用されるデータの自動検出と先読み（新機能）
"""

import sys
import os
from pathlib import Path
from collections import OrderedDict
from threading import Lock, RLock, Thread, Event
import time
import weakref
from typing import Optional, Any, Dict, List
import atexit

# 親ディレクトリのdictsqlite_fastestモジュールをインポート
sys.path.insert(0, str(Path(__file__).parent.parent))
from dictsqlite_fastest.main import DictSQLiteFastest


class LRUCache:
    """スレッドセーフなLRUキャッシュ実装.
    
    最も頻繁にアクセスされるデータをメモリに保持し、
    ディスクアクセスを削減します。
    """
    
    def __init__(self, capacity: int = 10000):
        """
        Args:
            capacity: キャッシュの最大容量（アイテム数）
        """
        self.capacity = capacity
        self.cache = OrderedDict()
        self.lock = Lock()
        self.hits = 0
        self.misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """キャッシュから値を取得.
        
        Args:
            key: 取得するキー
            
        Returns:
            キャッシュにある場合は値、ない場合はNone
        """
        with self.lock:
            if key in self.cache:
                # LRU: 最近使用したものを末尾に移動
                self.cache.move_to_end(key)
                self.hits += 1
                return self.cache[key]
            self.misses += 1
            return None
    
    def put(self, key: str, value: Any) -> None:
        """キャッシュに値を追加.
        
        Args:
            key: キー
            value: 値
        """
        with self.lock:
            if key in self.cache:
                # 既存のキーは末尾に移動
                self.cache.move_to_end(key)
            self.cache[key] = value
            
            # 容量超過時は最も古いアイテムを削除
            if len(self.cache) > self.capacity:
                self.cache.popitem(last=False)
    
    def bulk_put(self, items: dict) -> None:
        """複数のアイテムを一括でキャッシュに追加（高速化版）.
        
        Args:
            items: 追加するアイテムの辞書
        """
        with self.lock:
            for key, value in items.items():
                if key in self.cache:
                    self.cache.move_to_end(key)
                self.cache[key] = value
            
            # 容量超過時は古いアイテムを一括削除
            overflow = len(self.cache) - self.capacity
            if overflow > 0:
                for _ in range(overflow):
                    self.cache.popitem(last=False)
    
    def remove(self, key: str) -> None:
        """キャッシュからキーを削除.
        
        Args:
            key: 削除するキー
        """
        with self.lock:
            self.cache.pop(key, None)
    
    def clear(self) -> None:
        """キャッシュをクリア."""
        with self.lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0
    
    def get_stats(self) -> Dict[str, int]:
        """キャッシュ統計を取得.
        
        Returns:
            統計情報の辞書
        """
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


class WriteBuffer:
    """書き込みバッファ - メモリに書き込みを蓄積し、一括でディスクに書き込む.
    
    これにより、小さな書き込みによるディスクI/Oを削減します。
    """
    
    def __init__(self, flush_threshold: int = 1000, flush_interval: float = 5.0):
        """
        Args:
            flush_threshold: フラッシュするアイテム数の閾値
            flush_interval: 自動フラッシュの時間間隔（秒）
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
    
    def get_pending_data(self) -> tuple:
        """保留中のデータを取得してバッファをクリア.
        
        Returns:
            (書き込みデータの辞書, 削除キーのセット)
        """
        with self.lock:
            data = self.buffer.copy()
            deleted = self.deleted_keys.copy()
            self.buffer.clear()
            self.deleted_keys.clear()
            self.last_flush_time = time.time()
            return data, deleted
    
    def has_pending(self) -> bool:
        """保留中のデータがあるかチェック.
        
        Returns:
            保留中のデータがある場合True
        """
        with self.lock:
            return len(self.buffer) > 0 or len(self.deleted_keys) > 0


class DictSQLiteFastestBeta(DictSQLiteFastest):
    """DictSQLite-Fastest Beta版 - メモリ最優先の最適化実装.
    
    既存のDictSQLiteFastestを継承し、以下の追加最適化を提供:
    1. LRUキャッシュによるホットデータのメモリ保持
    2. 書き込みバッファリング（遅延書き込み）
    3. アグレッシブなメモリPRAGMA設定
    4. オプションの完全メモリモード
    5. メモリ予算に基づく自動最適化（新機能）
    6. バックグラウンド自動フラッシュ（新機能）
    7. 小容量データベースの完全メモリロード（新機能）
    8. 頻繁に使用されるデータの自動検出と先読み（新機能）
    
    使用例:
        >>> from dictsqlite_fastest_beta import DictSQLiteFastestBeta
        >>> 
        >>> # 通常モード（ディスクベース + メモリキャッシュ）
        >>> db = DictSQLiteFastestBeta('data.db', cache_capacity=10000)
        >>> db['key1'] = 'value1'
        >>> 
        >>> # メモリオンリーモード（最高速）
        >>> db_mem = DictSQLiteFastestBeta(':memory:', memory_only=True)
        >>> db_mem['key2'] = 'value2'
        >>> 
        >>> # メモリ予算指定モード（自動最適化）
        >>> db_budget = DictSQLiteFastestBeta('data.db', memory_budget_mb=512)
        >>> # 512MBのメモリ予算内で自動的に最適化される
    """
    
    def __init__(
        self,
        db_name: str,
        table_name: str = 'main',
        # ベータ版専用のメモリ最適化パラメータ
        cache_capacity: int = 10000,  # LRUキャッシュの容量
        write_buffer_size: int = 1000,  # 書き込みバッファのサイズ
        write_buffer_interval: float = 5.0,  # 書き込みバッファの自動フラッシュ間隔（秒）
        memory_only: bool = False,  # メモリオンリーモード
        aggressive_memory: bool = True,  # アグレッシブなメモリ設定を使用
        # 新機能のパラメータ
        memory_budget_mb: Optional[int] = None,  # メモリ予算（MB）- 設定すると自動最適化
        auto_load_threshold_mb: float = 10.0,  # この容量以下のDBは完全メモリロード（MB）
        enable_background_flush: bool = True,  # バックグラウンド自動フラッシュを有効化
        enable_hot_data_detection: bool = True,  # ホットデータ検出と自動プリフェッチ
        # 親クラスのパラメータ
        **kwargs
    ):
        """
        Args:
            db_name: データベースファイル名（':memory:'でメモリDB）
            table_name: テーブル名
            cache_capacity: LRUキャッシュの最大容量（アイテム数）
            write_buffer_size: 書き込みバッファのフラッシュ閾値
            write_buffer_interval: 書き込みバッファの自動フラッシュ間隔（秒）
            memory_only: Trueの場合、完全にメモリ内で動作（ディスク書き込みなし）
            aggressive_memory: Trueの場合、アグレッシブなメモリPRAGMA設定を使用
            memory_budget_mb: メモリ予算（MB）。設定すると自動的にキャッシュサイズなどを最適化
            auto_load_threshold_mb: この容量以下のDBは起動時に完全メモリロード（MB）
            enable_background_flush: バックグラウンド自動フラッシュを有効化
            enable_hot_data_detection: ホットデータ検出と自動プリフェッチを有効化
            **kwargs: 親クラスに渡すその他のパラメータ
        """
        # メモリ予算に基づく自動最適化
        if memory_budget_mb is not None:
            # メモリ予算の60%をキャッシュに、30%をバッファに、10%をその他に割り当て
            # 1アイテムあたり平均1KBと仮定
            cache_capacity = int(memory_budget_mb * 1024 * 0.6)  # 60%をキャッシュに
            write_buffer_size = int(memory_budget_mb * 1024 * 0.3)  # 30%をバッファに
        
        # メモリオンリーモードの場合、db_nameを':memory:'に設定
        if memory_only:
            db_name = ':memory:'
        
        # アグレッシブなメモリ設定を適用
        if aggressive_memory and not memory_only:
            # デフォルト値を上書き（メモリオンリーモードでない場合のみ）
            kwargs.setdefault('cache_size', -256000)  # 256MB cache
            kwargs.setdefault('mmap_size', 1073741824)  # 1GB mmap
            kwargs.setdefault('journal_mode', 'WAL')  # WALモード
            
            # カスタムPRAGMA設定
            custom_pragma = kwargs.get('custom_pragma_settings', {})
            custom_pragma.update({
                'temp_store': 'MEMORY',  # 一時ファイルをメモリに
                'locking_mode': 'EXCLUSIVE',  # 排他ロックモード（高速化）
                'synchronous': 'NORMAL',  # WALモードでは安全かつ高速
                'wal_autocheckpoint': 10000,  # WAL自動チェックポイント（10000ページ）
            })
            kwargs['custom_pragma_settings'] = custom_pragma
        elif memory_only:
            # メモリオンリーモードでは軽量な設定（WALをOFFに）
            kwargs.setdefault('cache_size', -64000)  # 64MB cache
            kwargs.setdefault('journal_mode', 'OFF')  # ジャーナルなし（メモリのみなので不要）
            custom_pragma = kwargs.get('custom_pragma_settings', {})
            custom_pragma.update({
                'temp_store': 'MEMORY',
            })
            kwargs['custom_pragma_settings'] = custom_pragma
        
        # 親クラスの初期化
        super().__init__(db_name, table_name=table_name, **kwargs)
        
        # メモリオンリーモードの場合、テーブルが作成されていない可能性があるので確認
        if memory_only or db_name == ':memory:':
            self._ensure_table_exists()
        
        # ベータ版専用の属性
        self.cache_capacity = cache_capacity
        self.write_buffer_size = write_buffer_size
        self.write_buffer_interval = write_buffer_interval
        self.memory_only = memory_only
        self.aggressive_memory = aggressive_memory
        self.memory_budget_mb = memory_budget_mb
        self.auto_load_threshold_mb = auto_load_threshold_mb
        self.enable_background_flush = enable_background_flush
        self.enable_hot_data_detection = enable_hot_data_detection
        
        # LRUキャッシュの初期化
        self._cache = LRUCache(capacity=cache_capacity)
        
        # 書き込みバッファの初期化（メモリオンリーモードでは無効）
        if not memory_only:
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
            'buffer_flushes': 0,
            'auto_preloads': 0,  # 新機能：自動プリロード回数
            'hot_data_promotions': 0,  # 新機能：ホットデータの昇格回数
            'operation_times': {
                'read': [],
                'write': [],
                'bulk_read': [],
                'bulk_write': []
            }
        }
        self._stats_lock = Lock()
        
        # パフォーマンス最適化のための追加設定
        self._operation_count = 0
        self._auto_tune_interval = 10000  # 10000操作ごとに自動チューニング
        
        # ホットデータ検出用の統計（新機能）
        self._access_frequency = {}  # キーごとのアクセス頻度
        self._access_frequency_lock = Lock()
        
        # バックグラウンドフラッシュスレッド（新機能）
        self._background_flush_thread = None
        self._flush_stop_event = None
        if enable_background_flush and not memory_only:
            self._flush_stop_event = Event()
            self._background_flush_thread = Thread(
                target=self._background_flush_worker,
                daemon=True,
                name="DictSQLiteBeta-BgFlush"
            )
            self._background_flush_thread.start()
            # クリーンアップハンドラを登録
            atexit.register(self._cleanup_background_thread)
        
        # データベースサイズのチェックと自動ロード（新機能）
        if not memory_only and db_name != ':memory:':
            self._check_and_auto_load_database(db_name, auto_load_threshold_mb)
    
    def _ensure_table_exists(self):
        """高速テーブル存在確認（親クラスのグローバルフラグ活用）
        
        親クラスのグローバル初期化状態をチェックし、未初期化の場合のみ
        実際のテーブル確認を実行。これにより、不要なSQLクエリを削減。
        
        パフォーマンス:
            - 初期化済み: ~10ns (辞書ルックアップのみ)
            - 未初期化: SQLクエリ実行（初回のみ）
        """
        # 親クラスのグローバル初期化状態をインポート
        from dictsqlite_fastest.main import _db_init_states
        
        init_key = f"{self.db_name}:{self.table_name}"
        
        # 【高速パス】親クラスで既に初期化済みの場合
        if _db_init_states.get(init_key, False):
            return  # 何もしない（最速）
        
        # 【低速パス】未初期化の場合のみ実行
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            # テーブルが存在するか確認
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (self.table_name,))
            if not cursor.fetchone():
                # テーブルが存在しない場合は作成
                schema = f'CREATE TABLE IF NOT EXISTS {self._quote_ident(self.table_name)} (key TEXT PRIMARY KEY, value TEXT)'
                cursor.execute(schema)
                
                # WALモードの場合、チェックポイント実行
                if hasattr(self, 'journal_mode') and self.journal_mode == 'WAL':
                    try:
                        cursor.execute("PRAGMA wal_checkpoint(PASSIVE)")
                    except Exception:
                        pass
            
            # グローバルフラグを更新
            _db_init_states[init_key] = True
        finally:
            pass  # カーソルは閉じない（キャッシュされている）
    
    def __getitem__(self, key: str) -> Any:
        """キーから値を取得（キャッシュ優先）.
        
        Args:
            key: 取得するキー
            
        Returns:
            キーに対応する値
            
        Raises:
            KeyError: キーが存在しない場合
        """
        # アクセス頻度を追跡（ホットデータ検出）
        self._track_access_frequency(key)
        
        # まずキャッシュをチェック
        cached_value = self._cache.get(key)
        if cached_value is not None:
            with self._stats_lock:
                self._stats['cache_hits'] += 1
            return cached_value
        
        # 書き込みバッファをチェック（まだディスクに書き込まれていない可能性）
        if self._write_buffer is not None:
            with self._write_buffer.lock:
                if key in self._write_buffer.buffer:
                    value = self._write_buffer.buffer[key]
                    # キャッシュに追加
                    self._cache.put(key, value)
                    return value
        
        # キャッシュミス - ディスクから読み込み
        with self._stats_lock:
            self._stats['cache_misses'] += 1
            self._stats['disk_reads'] += 1
        
        value = super().__getitem__(key)
        
        # キャッシュに追加
        self._cache.put(key, value)
        
        # 定期的に自動チューニング
        self._operation_count += 1
        if self._operation_count % self._auto_tune_interval == 0:
            self._auto_tune_parameters()
        
        return value
    
    def __setitem__(self, key: str, value: Any) -> None:
        """キーに値を設定（書き込みバッファ経由）.
        
        Args:
            key: キー
            value: 値
        """
        # ゼロコストテーブル存在確認
        self._ensure_table_exists()
        
        # キャッシュを更新
        self._cache.put(key, value)
        
        if self.memory_only:
            # メモリオンリーモードでは直接書き込み
            super().__setitem__(key, value)
        else:
            # 書き込みバッファに追加
            should_flush = self._write_buffer.add(key, value)
            
            if should_flush:
                self._flush_write_buffer()
    
    def __delitem__(self, key: str) -> None:
        """キーを削除.
        
        Args:
            key: 削除するキー
        """
        # キャッシュから削除
        self._cache.remove(key)
        
        if self.memory_only:
            # メモリオンリーモードでは直接削除
            super().__delitem__(key)
        else:
            # 書き込みバッファに削除を追加
            should_flush = self._write_buffer.remove(key)
            
            if should_flush:
                self._flush_write_buffer()
    
    def __contains__(self, key: str) -> bool:
        """キーが存在するかチェック.
        
        Args:
            key: チェックするキー
            
        Returns:
            キーが存在する場合True
        """
        # キャッシュをチェック
        if self._cache.get(key) is not None:
            return True
        
        # 書き込みバッファをチェック
        if self._write_buffer is not None:
            with self._write_buffer.lock:
                if key in self._write_buffer.buffer:
                    return True
                if key in self._write_buffer.deleted_keys:
                    return False
        
        # ディスクをチェック
        return super().__contains__(key)
    
    def get(self, key: str, default: Any = None) -> Any:
        """キーから値を取得（デフォルト値付き）.
        
        Args:
            key: 取得するキー
            default: キーが存在しない場合のデフォルト値
            
        Returns:
            キーに対応する値、または存在しない場合はdefault
        """
        try:
            return self[key]
        except KeyError:
            return default
    
    def _flush_write_buffer(self) -> None:
        """書き込みバッファをディスクにフラッシュ.
        
        バッファに蓄積された書き込みと削除を一括でディスクに反映します。
        """
        if self._write_buffer is None or not self._write_buffer.has_pending():
            return
        
        data, deleted_keys = self._write_buffer.get_pending_data()
        
        with self._stats_lock:
            self._stats['buffer_flushes'] += 1
            self._stats['disk_writes'] += len(data) + len(deleted_keys)
        
        # 一括書き込み（トランザクション内で効率的に処理）
        if data:
            try:
                super().bulk_insert(data)
            except Exception as e:
                # テーブルが存在しない場合などのエラーは無視
                pass
        
        # 一括削除
        if deleted_keys:
            # 削除も効率的にバッチ処理
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                for key in deleted_keys:
                    try:
                        cursor.execute(
                            f"DELETE FROM {self._quote_ident(self.table_name)} WHERE key = ?",
                            (key,)
                        )
                    except Exception:
                        pass  # 既に削除されている場合は無視
            except Exception:
                pass  # コネクションエラーは無視
    
    def flush(self) -> None:
        """保留中のすべての変更をディスクに書き込む.
        
        書き込みバッファの内容を強制的にディスクに書き込みます。
        """
        if not self.memory_only:
            self._flush_write_buffer()
            # WALチェックポイントを実行してメモリを最適化
            if self.aggressive_memory:
                self._optimize_wal_checkpoint()
    
    def _optimize_wal_checkpoint(self) -> None:
        """WALチェックポイントを最適化してメモリ使用を改善.
        
        WALファイルが大きくなりすぎないように定期的にチェックポイントを実行します。
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            # TRUNCATEモードでチェックポイントを実行（メモリ効率が良い）
            cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except Exception:
            pass  # エラーは無視（チェックポイントは必須ではない）
    
    def _auto_tune_parameters(self) -> None:
        """アクセスパターンに基づいて自動的にパラメータを調整.
        
        キャッシュヒット率や操作パターンに基づいて、キャッシュサイズや
        バッファサイズを動的に調整します。
        """
        cache_stats = self._cache.get_stats()
        
        # キャッシュヒット率が低い（<50%）場合、キャッシュを拡大
        if cache_stats['hit_rate'] < 50 and cache_stats['size'] < 50000:
            new_capacity = min(int(self._cache.capacity * 1.5), 50000)
            self._cache.capacity = new_capacity
        
        # キャッシュヒット率が非常に高い（>95%）かつキャッシュが大きい場合、縮小
        elif cache_stats['hit_rate'] > 95 and self._cache.capacity > 5000:
            new_capacity = max(int(self._cache.capacity * 0.8), 5000)
            self._cache.capacity = new_capacity
    
    def close(self) -> None:
        """データベースを閉じる.
        
        保留中の変更をフラッシュしてから閉じます。
        """
        # バックグラウンドスレッドを停止
        self._cleanup_background_thread()
        
        # バッファをフラッシュ
        self.flush()
        
        # 親クラスのclose
        super().close()
    
    def __enter__(self):
        """コンテキストマネージャのenter."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャのexit."""
        self.close()
        return False
    
    def clear_cache(self) -> None:
        """メモリキャッシュをクリア.
        
        注意: これはメモリキャッシュのみをクリアします。
        ディスク上のデータは削除されません。
        """
        self._cache.clear()
    
    def get_beta_stats(self) -> Dict[str, Any]:
        """ベータ版の統計情報を取得.
        
        Returns:
            統計情報を含む辞書:
            - cache: キャッシュ統計
            - operations: 操作統計（読み書き、フラッシュ回数など）
            - buffer: バッファの状態（メモリオンリーモードでは None）
            - config: 設定情報
            - performance: パフォーマンス指標
            - hot_data: ホットデータ検出の統計（新機能）
        """
        cache_stats = self._cache.get_stats()
        
        buffer_status = None
        if self._write_buffer is not None:
            with self._write_buffer.lock:
                buffer_status = {
                    'pending_writes': len(self._write_buffer.buffer),
                    'pending_deletes': len(self._write_buffer.deleted_keys),
                    'threshold': self._write_buffer.flush_threshold,
                    'interval': self._write_buffer.flush_interval
                }
        
        with self._stats_lock:
            operation_stats = self._stats.copy()
            
            # パフォーマンス指標を計算
            total_reads = cache_stats['hits'] + cache_stats['misses']
            cache_effectiveness = (cache_stats['hit_rate'] / 100.0) if total_reads > 0 else 0
            
            # ディスクアクセス削減率
            disk_savings = 1.0 - (operation_stats['disk_reads'] / total_reads) if total_reads > 0 else 0
        
        # ホットデータ統計
        with self._access_frequency_lock:
            hot_keys_count = sum(1 for freq in self._access_frequency.values() if freq >= 10)
        
        return {
            'cache': cache_stats,
            'operations': operation_stats,
            'buffer': buffer_status,
            'config': {
                'memory_only': self.memory_only,
                'aggressive_memory': self.aggressive_memory,
                'cache_capacity': self.cache_capacity,
                'write_buffer_size': self.write_buffer_size,
                'auto_tune_interval': self._auto_tune_interval,
                'memory_budget_mb': self.memory_budget_mb,
                'auto_load_threshold_mb': self.auto_load_threshold_mb,
                'enable_background_flush': self.enable_background_flush,
                'enable_hot_data_detection': self.enable_hot_data_detection,
            },
            'performance': {
                'cache_effectiveness': cache_effectiveness,
                'disk_savings_rate': disk_savings,
                'total_operations': self._operation_count
            },
            'hot_data': {
                'tracked_keys': len(self._access_frequency),
                'hot_keys_count': hot_keys_count,
                'promotions': operation_stats.get('hot_data_promotions', 0)
            }
        }
    
    def prefetch_keys(self, keys: List[str]) -> None:
        """指定したキーのデータを事前にキャッシュに読み込む（先読み）.
        
        Args:
            keys: プリフェッチするキーのリスト
        """
        # まだキャッシュにないキーのみを取得
        keys_to_fetch = [k for k in keys if self._cache.get(k) is None]
        
        if not keys_to_fetch:
            return
        
        # バルク取得を使用して効率的に読み込み
        try:
            values = super().bulk_get(keys_to_fetch)
            # キャッシュに追加
            for key, value in values.items():
                self._cache.put(key, value)
        except Exception:
            # エラーが発生した場合は個別に取得
            for key in keys_to_fetch:
                try:
                    value = super().__getitem__(key)
                    self._cache.put(key, value)
                except KeyError:
                    pass  # 存在しないキーは無視
    
    def bulk_prefetch(self, key_pattern: str = None, limit: int = 1000) -> None:
        """パターンマッチングで複数キーを先読み.
        
        アクセスパターンに基づいて関連するキーを一括でプリフェッチします。
        
        Args:
            key_pattern: SQLのLIKEパターン（例: 'user_%'）
            limit: プリフェッチする最大キー数
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            if key_pattern:
                # パターンマッチングでキーを取得
                query = f"SELECT key FROM {self._quote_ident(self.table_name)} WHERE key LIKE ? LIMIT ?"
                cursor.execute(query, (key_pattern, limit))
            else:
                # すべてのキーを取得（上限付き）
                query = f"SELECT key FROM {self._quote_ident(self.table_name)} LIMIT ?"
                cursor.execute(query, (limit,))
            
            keys = [row[0] for row in cursor.fetchall()]
            
            # 取得したキーをプリフェッチ
            if keys:
                self.prefetch_keys(keys)
                
        except Exception:
            pass  # エラーは無視
    
    def bulk_insert(self, items: dict) -> None:
        """バルク挿入（最適化版）.
        
        大きなバルク操作では直接ディスクに書き込み、小さな操作はバッファリングします。
        
        Args:
            items: 挿入するアイテムの辞書
        """
        if not items:
            return
        
        # ゼロコストテーブル存在確認
        self._ensure_table_exists()
            
        if self.memory_only:
            # メモリオンリーモードでは直接書き込み（バッファなし）
            super().bulk_insert(items)
            # 書き込み後にキャッシュを一括更新（高速化）
            self._cache.bulk_put(items)
        else:
            # 大きなバルク操作（100件以上）の場合は直接書き込み
            # これによりバルク処理の速度を維持
            if len(items) >= 100:
                # 既存のバッファが空でない場合のみフラッシュ（高速化）
                with self._write_buffer.lock:
                    has_pending = len(self._write_buffer.buffer) > 0 or len(self._write_buffer.deleted_keys) > 0
                
                if has_pending:
                    self._flush_write_buffer()
                
                # 大きなバルクは親クラスに委譲（最適化されたトランザクション処理）
                # 統計は軽量に更新
                super().bulk_insert(items)
                with self._stats_lock:
                    self._stats['disk_writes'] += len(items)
                
                # 書き込み後にキャッシュを一括更新（高速化）
                self._cache.bulk_put(items)
            else:
                # 小さいバルク操作（<100件）はバッファに追加して遅延書き込み
                self._cache.bulk_put(items)
                for key, value in items.items():
                    self._write_buffer.add(key, value)
                
                # バッファが閾値に達したらフラッシュ
                if self._write_buffer._should_flush():
                    self._flush_write_buffer()
    
    def bulk_get(self, keys: List[str]) -> dict:
        """バルク取得（キャッシュ優先）.
        
        Args:
            keys: 取得するキーのリスト
            
        Returns:
            キーと値の辞書
        """
        result = {}
        missing_keys = []
        
        # まずキャッシュから取得
        for key in keys:
            cached_value = self._cache.get(key)
            if cached_value is not None:
                result[key] = cached_value
            else:
                missing_keys.append(key)
        
        # キャッシュにないキーはディスクから取得
        if missing_keys:
            with self._stats_lock:
                self._stats['disk_reads'] += len(missing_keys)
            
            disk_values = super().bulk_get(missing_keys)
            result.update(disk_values)
            
            # 取得した値をキャッシュに追加
            for key, value in disk_values.items():
                self._cache.put(key, value)
        
        return result
    
    def _check_and_auto_load_database(self, db_path: str, threshold_mb: float) -> None:
        """小容量データベースを自動的にメモリにロード（新機能）.
        
        データベースファイルサイズが閾値以下の場合、
        すべてのデータをキャッシュにプリロードします。
        
        Args:
            db_path: データベースファイルパス
            threshold_mb: 自動ロードの閾値（MB）
        """
        try:
            if not os.path.exists(db_path):
                return
            
            # ファイルサイズをチェック
            file_size_mb = os.path.getsize(db_path) / (1024 * 1024)
            
            if file_size_mb <= threshold_mb:
                # 小容量なので全データをメモリにロード
                try:
                    conn = self._get_connection()
                    cursor = conn.cursor()
                    
                    # テーブルが存在するか確認
                    cursor.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                        (self.table_name,)
                    )
                    if not cursor.fetchone():
                        # テーブルが存在しない場合はスキップ
                        return
                    
                    query = f"SELECT key, value FROM {self._quote_ident(self.table_name)}"
                    cursor.execute(query)
                    
                    count = 0
                    items = {}
                    for row in cursor.fetchall():
                        key, value_str = row
                        try:
                            value = self._deserialize(value_str)
                            items[key] = value
                            count += 1
                            
                            # 1000件ごとにバッチでキャッシュに追加（効率化）
                            if count % 1000 == 0:
                                self._cache.bulk_put(items)
                                items = {}
                        except Exception:
                            pass  # デシリアライズエラーは無視
                    
                    # 残りをキャッシュに追加
                    if items:
                        self._cache.bulk_put(items)
                    
                    with self._stats_lock:
                        self._stats['auto_preloads'] += count
                        
                except Exception:
                    pass  # エラーは無視（自動ロードは必須ではない）
        except Exception:
            pass  # ファイルサイズチェックエラーも無視
    
    def _background_flush_worker(self) -> None:
        """バックグラウンドで定期的にバッファをフラッシュ（新機能）.
        
        別スレッドで動作し、設定された間隔でバッファを自動フラッシュします。
        """
        while not self._flush_stop_event.is_set():
            # フラッシュ間隔待機
            if self._flush_stop_event.wait(timeout=self.write_buffer_interval):
                # stopイベントが設定された場合は終了
                break
            
            # バッファをフラッシュ
            try:
                if self._write_buffer and self._write_buffer.has_pending():
                    self._flush_write_buffer()
            except Exception:
                pass  # エラーは無視（バックグラウンドスレッド）
    
    def _cleanup_background_thread(self) -> None:
        """バックグラウンドスレッドのクリーンアップ."""
        if self._flush_stop_event:
            self._flush_stop_event.set()
        if self._background_flush_thread and self._background_flush_thread.is_alive():
            self._background_flush_thread.join(timeout=2.0)
    
    def _track_access_frequency(self, key: str) -> None:
        """キーのアクセス頻度を追跡（ホットデータ検出用）（新機能）.
        
        Args:
            key: 追跡するキー
        """
        if not self.enable_hot_data_detection:
            return
        
        with self._access_frequency_lock:
            self._access_frequency[key] = self._access_frequency.get(key, 0) + 1
            
            # 頻度が高いキー（10回以上アクセス）を検出
            if self._access_frequency[key] == 10:
                # ホットデータとして認識し、関連データを先読み
                self._preload_related_keys(key)
                with self._stats_lock:
                    self._stats['hot_data_promotions'] += 1
            
            # 定期的にアクセス頻度をリセット（メモリ節約）
            if len(self._access_frequency) > 10000:
                # 頻度の低いキーを削除
                sorted_items = sorted(
                    self._access_frequency.items(),
                    key=lambda x: x[1],
                    reverse=True
                )
                self._access_frequency = dict(sorted_items[:5000])
    
    def _preload_related_keys(self, hot_key: str) -> None:
        """ホットキーに関連するキーを先読み（新機能）.
        
        ホットキーと似たパターンのキーを先読みしてパフォーマンスを向上させます。
        
        Args:
            hot_key: ホットキー
        """
        try:
            # キーのパターンを抽出（例: "user_123" -> "user_%"）
            if '_' in hot_key:
                prefix = hot_key.rsplit('_', 1)[0] + '_%'
            elif '-' in hot_key:
                prefix = hot_key.rsplit('-', 1)[0] + '-%'
            else:
                # パターンが明確でない場合はスキップ
                return
            
            # 関連キーを先読み（最大100件）
            self.bulk_prefetch(prefix, limit=100)
        except Exception:
            pass  # エラーは無視


# 非同期版のインポート
try:
    import asyncio
    from dictsqlite_fastest.main import AsyncDictSQLiteFastest
    
    class AsyncDictSQLiteFastestBeta:
        """非同期版DictSQLite-Fastest Beta - 非同期操作の高速化.
        
        同期版の全機能に加えて、非同期操作に最適化されています:
        - 非同期バルク操作の最適化
        - 共有キャッシュによる高速化
        - セマフォベースの並行制御で高速かつ安全な並行処理
        
        使用例:
            >>> async def main():
            ...     db = AsyncDictSQLiteFastestBeta('data.db', memory_budget_mb=256)
            ...     await db.aset('key1', 'value1')
            ...     value = await db.aget('key1')
            ...     await db.aclose()
        """
        
        def __init__(
            self,
            db_name: str,
            table_name: str = 'main',
            # Beta版のパラメータ
            cache_capacity: int = 10000,
            write_buffer_size: int = 1000,
            write_buffer_interval: float = 5.0,
            memory_only: bool = False,
            aggressive_memory: bool = True,
            memory_budget_mb: Optional[int] = None,
            auto_load_threshold_mb: float = 10.0,
            enable_background_flush: bool = True,
            enable_hot_data_detection: bool = True,
            # 非同期専用パラメータ
            max_connections: int = 10,
            enable_pipeline: bool = True,
            **kwargs
        ):
            """
            Args:
                max_connections: 非同期並行操作の最大数
                enable_pipeline: パイプライン操作を有効化
                その他のパラメータは同期版と同じ
            """
            # 非同期モードではバックグラウンドフラッシュを無効化（ロック競合を防ぐ）
            if enable_background_flush:
                enable_background_flush = False
            
            # 非同期モードでは排他ロックを無効化（並行アクセスを許可）
            original_aggressive = aggressive_memory
            aggressive_memory = False
            
            # 手動でメモリ最適化設定を適用（EXCLUSIVEロック以外）
            if original_aggressive and not memory_only:
                kwargs.setdefault('cache_size', -256000)  # 256MB cache
                kwargs.setdefault('mmap_size', 1073741824)  # 1GB mmap
                kwargs.setdefault('journal_mode', 'WAL')  # WALモード
                
                # カスタムPRAGMA設定（NORMALロックで並行アクセス許可）
                custom_pragma = kwargs.get('custom_pragma_settings', {})
                custom_pragma.update({
                    'temp_store': 'MEMORY',
                    'locking_mode': 'NORMAL',  # 並行アクセス許可
                    'synchronous': 'NORMAL',
                    'wal_autocheckpoint': 10000,
                })
                kwargs['custom_pragma_settings'] = custom_pragma
            
            # 同期版のベータインスタンスを内部で使用
            self._sync_db = DictSQLiteFastestBeta(
                db_name=db_name,
                table_name=table_name,
                cache_capacity=cache_capacity,
                write_buffer_size=write_buffer_size if not memory_only else 0,
                write_buffer_interval=write_buffer_interval,
                memory_only=memory_only,
                aggressive_memory=aggressive_memory,
                memory_budget_mb=memory_budget_mb,
                auto_load_threshold_mb=auto_load_threshold_mb,
                enable_background_flush=False,
                enable_hot_data_detection=enable_hot_data_detection,
                **kwargs
            )
            
            # 永続的なエグゼキュータ（複数ワーカーで並行処理）
            from concurrent.futures import ThreadPoolExecutor
            self._executor = ThreadPoolExecutor(
                max_workers=max_connections,
                thread_name_prefix="AsyncDB"
            )
            
            # セマフォで並行度を制御（データベースロック回避）
            self._semaphore = None
            self._write_semaphore = None
            
            # 設定を保存
            self.max_connections = max_connections
            self.enable_pipeline = enable_pipeline
            
            # 初期化フラグ
            self._initialized = False
        
        async def _ensure_initialized(self) -> None:
            """非同期コンポーネントの遅延初期化."""
            if self._initialized:
                return
            
            # セマフォを初期化（読み込みは並行度高め、書き込みは控えめ）
            self._semaphore = asyncio.Semaphore(self.max_connections)
            self._write_semaphore = asyncio.Semaphore(max(1, self.max_connections // 2))
            
            self._initialized = True
        
        async def aget(self, key: str, default: Any = None) -> Any:
            """非同期でキーから値を取得.
            
            Args:
                key: 取得するキー
                default: キーが存在しない場合のデフォルト値
                
            Returns:
                キーに対応する値、または存在しない場合はdefault
            """
            # キャッシュヒットは同期的に即座に返す（最速）
            cached_value = self._sync_db._cache.get(key)
            if cached_value is not None:
                with self._sync_db._stats_lock:
                    self._sync_db._stats['cache_hits'] += 1
                self._sync_db._track_access_frequency(key)
                return cached_value
            
            # 初期化確認（初回のみ）
            if not self._initialized:
                await self._ensure_initialized()
            
            # キャッシュミスの場合は非同期で読み込み（セマフォで並行度制御）
            async with self._semaphore:
                loop = asyncio.get_event_loop()
                try:
                    value = await loop.run_in_executor(
                        self._executor,
                        self._sync_db.__getitem__,
                        key
                    )
                    return value
                except KeyError:
                    return default
        
        async def aset(self, key: str, value: Any) -> None:
            """非同期でキーに値を設定.
            
            Args:
                key: キー
                value: 値
            """
            await self._ensure_initialized()
            
            # キャッシュは即座に更新（同期的に高速）
            self._sync_db._cache.put(key, value)
            
            # 書き込みはセマフォで並行度を制御
            async with self._write_semaphore:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    self._executor,
                    self._sync_db.__setitem__,
                    key,
                    value
                )
        
        async def adelete(self, key: str) -> None:
            """非同期でキーを削除.
            
            Args:
                key: 削除するキー
            """
            await self._ensure_initialized()
            
            async with self._write_semaphore:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    self._executor,
                    self._sync_db.__delitem__,
                    key
                )
        
        async def abulk_get(self, keys: List[str]) -> dict:
            """非同期でバルク取得.
            
            Args:
                keys: 取得するキーのリスト
                
            Returns:
                キーと値の辞書
            """
            await self._ensure_initialized()
            
            # まずキャッシュから取得
            result = {}
            missing_keys = []
            
            for key in keys:
                cached_value = self._sync_db._cache.get(key)
                if cached_value is not None:
                    result[key] = cached_value
                else:
                    missing_keys.append(key)
            
            # キャッシュミスは非同期で読み込み
            if missing_keys:
                async with self._semaphore:
                    loop = asyncio.get_event_loop()
                    disk_values = await loop.run_in_executor(
                        self._executor,
                        self._sync_db.bulk_get,
                        missing_keys
                    )
                    result.update(disk_values)
            
            return result
        
        async def abulk_insert(self, items: dict) -> None:
            """非同期でバルク挿入.
            
            Args:
                items: 挿入するアイテムの辞書
            """
            await self._ensure_initialized()
            
            # キャッシュは即座に更新
            self._sync_db._cache.bulk_put(items)
            
            # バルク操作は書き込みセマフォで制御
            async with self._write_semaphore:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    self._executor,
                    self._sync_db.bulk_insert,
                    items
                )
        
        async def aflush(self) -> None:
            """非同期でバッファをフラッシュ."""
            await self._ensure_initialized()
            
            async with self._write_semaphore:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    self._executor,
                    self._sync_db.flush
                )
        
        async def aclose(self) -> None:
            """非同期でデータベースを閉じる."""
            await self.aflush()
            
            # エグゼキュータをシャットダウン
            if self._executor:
                self._executor.shutdown(wait=True)
            
            # 同期DBをクローズ
            self._sync_db.close()
        
        def get_beta_stats(self) -> Dict[str, Any]:
            """ベータ版の統計情報を取得（同期メソッド）."""
            return self._sync_db.get_beta_stats()
        
        async def aprefetch_keys(self, keys: List[str]) -> None:
            """非同期で指定したキーを先読み.
            
            Args:
                keys: プリフェッチするキーのリスト
            """
            await self._ensure_initialized()
            
            async with self._semaphore:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    self._executor,
                    self._sync_db.prefetch_keys,
                    keys
                )
        
        async def abulk_prefetch(self, key_pattern: str = None, limit: int = 1000) -> None:
            """非同期でパターンマッチング先読み.
            
            Args:
                key_pattern: SQLのLIKEパターン
                limit: プリフェッチする最大キー数
            """
            await self._ensure_initialized()
            
            async with self._semaphore:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    self._executor,
                    self._sync_db.bulk_prefetch,
                    key_pattern,
                    limit
                )
        
        async def __aenter__(self):
            """非同期コンテキストマネージャのenter."""
            await self._ensure_initialized()
            return self
        
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            """非同期コンテキストマネージャのexit."""
            await self.aclose()
            return False

except ImportError:
    # asyncioが利用できない場合はスキップ
    AsyncDictSQLiteFastestBeta = None
