"""最適化手法の実装

Fastest版とBeta版の最良の最適化技術を統合。
"""

from collections import OrderedDict
from threading import Lock
from typing import Optional, Any


class LRUCache:
    """スレッドセーフなLRUキャッシュ実装
    
    最も頻繁にアクセスされるデータをメモリに保持し、
    ディスクアクセスを削減する。
    """
    
    __slots__ = ('capacity', 'cache', 'lock', 'hits', 'misses')
    
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
        """キャッシュから値を取得
        
        Args:
            key: 取得するキー
            
        Returns:
            キャッシュされている値、存在しない場合はNone
        """
        with self.lock:
            if key not in self.cache:
                self.misses += 1
                return None
            
            self.hits += 1
            # LRU: アクセスされたアイテムを最後に移動
            self.cache.move_to_end(key)
            return self.cache[key]
    
    def put(self, key: str, value: Any) -> None:
        """キャッシュに値を追加
        
        Args:
            key: キー
            value: 値
        """
        with self.lock:
            if key in self.cache:
                # 既存のキーの場合は更新して最後に移動
                self.cache.move_to_end(key)
            else:
                # 新しいキーの場合
                if len(self.cache) >= self.capacity:
                    # 容量オーバーの場合は最も古いアイテムを削除
                    self.cache.popitem(last=False)
            
            self.cache[key] = value
    
    def clear(self) -> None:
        """キャッシュをクリア"""
        with self.lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0
    
    def get_stats(self) -> dict:
        """キャッシュ統計を取得"""
        with self.lock:
            total = self.hits + self.misses
            hit_rate = (self.hits / total * 100) if total > 0 else 0
            return {
                'capacity': self.capacity,
                'size': len(self.cache),
                'hits': self.hits,
                'misses': self.misses,
                'hit_rate': hit_rate
            }


class WriteBuffer:
    """書き込みバッファ
    
    書き込み操作をメモリにバッファリングし、
    一括でディスクに書き込むことで性能を向上させる。
    """
    
    __slots__ = ('buffer', 'lock', 'max_size')
    
    def __init__(self, max_size: int = 1000):
        """
        Args:
            max_size: バッファの最大サイズ
        """
        self.buffer = {}
        self.lock = Lock()
        self.max_size = max_size
    
    def add(self, key: str, value: Any) -> bool:
        """バッファに追加
        
        Args:
            key: キー
            value: 値
            
        Returns:
            バッファがいっぱいになった場合True
        """
        with self.lock:
            self.buffer[key] = value
            return len(self.buffer) >= self.max_size
    
    def get_and_clear(self) -> dict:
        """バッファの内容を取得してクリア"""
        with self.lock:
            data = self.buffer.copy()
            self.buffer.clear()
            return data
    
    def clear(self) -> None:
        """バッファをクリア"""
        with self.lock:
            self.buffer.clear()
    
    def size(self) -> int:
        """バッファのサイズを取得"""
        with self.lock:
            return len(self.buffer)
