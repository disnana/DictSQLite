"""ユーティリティ関数とヘルパー"""

import time
import logging
import functools
from typing import Callable, Any
from pathlib import Path

logger = logging.getLogger(__name__)


def performance_tracker(func: Callable) -> Callable:
    """パフォーマンス追跡デコレータ
    
    関数の実行時間を記録し、ログに出力する。
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            elapsed = time.perf_counter() - start
            logger.debug(f"{func.__name__} executed in {elapsed:.4f}s")
    return wrapper


async def async_performance_tracker(func: Callable) -> Callable:
    """非同期パフォーマンス追跡デコレータ"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            elapsed = time.perf_counter() - start
            logger.debug(f"{func.__name__} executed in {elapsed:.4f}s")
    return wrapper


def setup_logging(log_file: Path = None, level: int = logging.INFO):
    """ロギングの設定
    
    Args:
        log_file: ログファイルのパス（Noneの場合は標準出力のみ）
        level: ログレベル
    """
    handlers = [logging.StreamHandler()]
    
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding='utf-8'))
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )


def format_ops(ops: float) -> str:
    """OPS値を人間に読みやすい形式にフォーマット
    
    Args:
        ops: Operations Per Second
        
    Returns:
        フォーマットされた文字列
    """
    if ops >= 1_000_000:
        return f"{ops/1_000_000:.2f}M ops/s"
    elif ops >= 1_000:
        return f"{ops/1_000:.2f}K ops/s"
    else:
        return f"{ops:.2f} ops/s"
