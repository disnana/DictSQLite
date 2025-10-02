"""DictSQLite-Fastest Beta - メモリ最優先の高速化実装.

このモジュールは、ディスクアクセスを最小限に抑え、メモリからのアクセスを
最大化することで、最高のパフォーマンスを実現します。

主な機能:
- LRUキャッシュによるホットデータのメモリ保持
- 書き込みバッファリング（バッチ書き込み）
- 先読みキャッシング戦略
- アグレッシブなメモリPRAGMA設定
- オプションの完全メモリモード
"""

import sys
import os
from pathlib import Path
from collections import OrderedDict
from threading import Lock, RLock
import time
import weakref
from typing import Optional, Any, Dict, List

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
            **kwargs: 親クラスに渡すその他のパラメータ
        """
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
            'buffer_flushes': 0
        }
        self._stats_lock = Lock()
    
    def _ensure_table_exists(self):
        """メモリデータベースでテーブルが存在することを確認（親クラスのバグ回避）."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            # テーブルが存在するか確認
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (self.table_name,))
            if not cursor.fetchone():
                # テーブルが存在しない場合は作成
                schema = f'CREATE TABLE IF NOT EXISTS {self._quote_ident(self.table_name)} (key TEXT PRIMARY KEY, value TEXT)'
                cursor.execute(schema)
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
        
        return value
    
    def __setitem__(self, key: str, value: Any) -> None:
        """キーに値を設定（書き込みバッファ経由）.
        
        Args:
            key: キー
            value: 値
        """
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
        
        # 一括書き込み
        if data:
            super().bulk_insert(data)
        
        # 一括削除
        if deleted_keys:
            for key in deleted_keys:
                try:
                    super().__delitem__(key)
                except KeyError:
                    pass  # 既に削除されている場合は無視
    
    def flush(self) -> None:
        """保留中のすべての変更をディスクに書き込む.
        
        書き込みバッファの内容を強制的にディスクに書き込みます。
        """
        if not self.memory_only:
            self._flush_write_buffer()
    
    def close(self) -> None:
        """データベースを閉じる.
        
        保留中の変更をフラッシュしてから閉じます。
        """
        self.flush()
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
        
        return {
            'cache': cache_stats,
            'operations': operation_stats,
            'buffer': buffer_status,
            'config': {
                'memory_only': self.memory_only,
                'aggressive_memory': self.aggressive_memory,
                'cache_capacity': self.cache_capacity
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
    
    def bulk_insert(self, items: dict) -> None:
        """バルク挿入（最適化版）.
        
        Args:
            items: 挿入するアイテムの辞書
        """
        # すべてキャッシュに追加
        for key, value in items.items():
            self._cache.put(key, value)
        
        if self.memory_only:
            # メモリオンリーモードでは直接書き込み
            super().bulk_insert(items)
        else:
            # バッファに追加
            for key, value in items.items():
                self._write_buffer.add(key, value)
            
            # 必要に応じてフラッシュ
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
