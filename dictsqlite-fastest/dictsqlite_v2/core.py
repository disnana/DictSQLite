"""コア実装 - DictSQLite-Fastest と Beta の統合版"""

import sys
import os
from pathlib import Path
from typing import Optional, Any, Dict
import pickle
import logging

# 親ディレクトリのモジュールをインポート
sys.path.insert(0, str(Path(__file__).parent.parent))
from dictsqlite_fastest.main import DictSQLiteFastest

# Beta版のインポート
sys.path.insert(0, str(Path(__file__).parent.parent / 'beta'))
from dictsqlite_fastest_beta_v2 import DictSQLiteFastestBeta, AsyncDictSQLiteFastestBeta

try:
    from .optimizations import LRUCache, WriteBuffer
    from .utils import performance_tracker
except ImportError:
    # Fallback for direct script execution
    from optimizations import LRUCache, WriteBuffer
    from utils import performance_tracker

logger = logging.getLogger(__name__)


class DictSQLiteV2(DictSQLiteFastestBeta):
    """DictSQLite v2.0 - 同期版
    
    Fastest版とBeta版の最良の機能を統合した最高性能版。
    継続的な最適化により常にパフォーマンスを向上させる。
    """
    
    def __init__(
        self,
        db_name: str,
        table_name: str = 'main',
        # キャッシュ設定
        cache_capacity: int = 10000,
        # 書き込みバッファ設定
        write_buffer_size: int = 1000,
        write_buffer_interval: float = 5.0,
        # メモリ管理
        memory_only: bool = False,
        aggressive_memory: bool = True,
        memory_budget_mb: Optional[int] = None,
        auto_load_threshold_mb: float = 10.0,
        # 機能フラグ
        enable_background_flush: bool = True,
        enable_hot_data_detection: bool = True,
        fast_mode: bool = True,
        **kwargs
    ):
        """
        Args:
            db_name: データベースファイルパス
            table_name: テーブル名
            cache_capacity: キャッシュ容量
            write_buffer_size: 書き込みバッファサイズ
            write_buffer_interval: 自動フラッシュ間隔（秒）
            memory_only: メモリのみモード
            aggressive_memory: アグレッシブメモリ管理
            memory_budget_mb: メモリ予算（MB）
            auto_load_threshold_mb: 自動ロード閾値（MB）
            enable_background_flush: バックグラウンド自動フラッシュ
            enable_hot_data_detection: ホットデータ検出
            fast_mode: 高速モード
        """
        # Beta版を継承して初期化
        super().__init__(
            db_name=db_name,
            table_name=table_name,
            cache_capacity=cache_capacity,
            write_buffer_size=write_buffer_size,
            write_buffer_interval=write_buffer_interval,
            memory_only=memory_only,
            aggressive_memory=aggressive_memory,
            memory_budget_mb=memory_budget_mb,
            auto_load_threshold_mb=auto_load_threshold_mb,
            enable_background_flush=enable_background_flush,
            enable_hot_data_detection=enable_hot_data_detection,
            fast_mode=fast_mode,
            **kwargs
        )
        
        logger.info(f"DictSQLiteV2 initialized: {db_name}")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """パフォーマンス統計を取得
        
        Returns:
            統計情報の辞書
        """
        # Beta版の統計を取得
        try:
            stats = super().get_performance_stats()
        except AttributeError:
            # Fallback if method doesn't exist
            stats = {
                'cache': {
                    'capacity': self._cache_capacity if hasattr(self, '_cache_capacity') else 0,
                    'size': 0,
                    'hit_rate': 0
                }
            }
        
        # v2独自の情報を追加
        stats['version'] = '2.0.0'
        if 'optimizations' not in stats:
            stats['optimizations'] = {}
        stats['optimizations'].update({
            'cache_enabled': True,
            'write_buffer_enabled': True,
            'background_flush': getattr(self, '_background_flush_enabled', False),
        })
        
        return stats


class AsyncDictSQLiteV2(AsyncDictSQLiteFastestBeta):
    """DictSQLite v2.0 - 非同期版
    
    aiosqlite + 内部バッチ処理による真の非同期実装。
    """
    
    def __init__(
        self,
        db_name: str,
        table_name: str = 'main',
        cache_capacity: int = 10000,
        batch_size: int = 100,
        batch_timeout: float = 0.1,
        **kwargs
    ):
        """
        Args:
            db_name: データベースファイルパス
            table_name: テーブル名
            cache_capacity: キャッシュ容量
            batch_size: バッチサイズ
            batch_timeout: バッチタイムアウト（秒）
        """
        super().__init__(
            db_name=db_name,
            table_name=table_name,
            cache_capacity=cache_capacity,
            batch_size=batch_size,
            batch_timeout=batch_timeout,
            **kwargs
        )
        
        logger.info(f"AsyncDictSQLiteV2 initialized: {db_name}")
    
    async def get_performance_stats(self) -> Dict[str, Any]:
        """パフォーマンス統計を取得（非同期）
        
        Returns:
            統計情報の辞書
        """
        stats = {
            'version': '2.0.0-async',
            'cache_capacity': self._cache_capacity if hasattr(self, '_cache_capacity') else None,
            'batch_size': self._batch_size if hasattr(self, '_batch_size') else None,
        }
        
        return stats
