"""Test v2 optimizations - sync and async versions."""

import sys
import asyncio
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from dictsqlite_fastest_beta_v2 import DictSQLiteFastestBeta, AsyncDictSQLiteFastestBeta


def test_sync_fast_mode():
    """Test sync version with fast_mode."""
    print("\n" + "="*80)
    print("同期版 fast_mode テスト")
    print("="*80)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_sync.db"
        
        # Test with fast_mode=True (default)
        db = DictSQLiteFastestBeta(
            str(db_path),
            fast_mode=True,
            enable_stats_collection=False,
            lazy_tracking_threshold=100
        )
        
        # Write some data
        for i in range(100):
            db[f'key_{i}'] = f'value_{i}'
        
        # Read data (should use fast cache)
        for i in range(100):
            value = db[f'key_{i}']
            assert value == f'value_{i}', f"Expected value_{i}, got {value}"
        
        # Test cache hit
        value = db['key_0']
        assert value == 'value_0'
        
        db.close()
        print("✅ 同期版 fast_mode テスト成功")


async def test_async_fast_mode():
    """Test async version with fast_mode."""
    print("\n" + "="*80)
    print("非同期版 fast_mode テスト")
    print("="*80)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_async.db"
        
        # Test with fast_mode=True (default)
        db = AsyncDictSQLiteFastestBeta(
            str(db_path),
            fast_mode=True,
            enable_stats_collection=False,
            lazy_tracking_threshold=100,
            async_batch_size=50
        )
        
        # Write some data
        for i in range(100):
            await db.aset(f'key_{i}', f'value_{i}')
        
        # Flush buffer
        await db._flush_write_buffer()
        
        # Read data (should use fast cache)
        for i in range(100):
            value = await db.aget(f'key_{i}')
            assert value == f'value_{i}', f"Expected value_{i}, got {value}"
        
        # Test cache hit
        value = await db.aget('key_0')
        assert value == 'value_0'
        
        # Test bulk insert
        bulk_items = {f'bulk_{i}': f'bulk_value_{i}' for i in range(50)}
        await db.abulk_insert(bulk_items)
        
        # Verify bulk items
        for i in range(50):
            value = await db.aget(f'bulk_{i}')
            assert value == f'bulk_value_{i}'
        
        await db.aclose()
        print("✅ 非同期版 fast_mode テスト成功")


async def test_async_performance():
    """Test async version performance."""
    print("\n" + "="*80)
    print("非同期版 性能テスト")
    print("="*80)
    
    import time
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_perf.db"
        
        db = AsyncDictSQLiteFastestBeta(
            str(db_path),
            fast_mode=True,
            async_batch_size=100
        )
        
        # Write test
        count = 1000
        start = time.time()
        for i in range(count):
            await db.aset(f'key_{i}', f'value_{i}')
        await db._flush_write_buffer()
        write_time = time.time() - start
        print(f"書き込み {count}件: {write_time:.3f}秒 ({count/write_time:.0f} ops/s)")
        
        # Read test (cache miss)
        await db.aclose()
        db = AsyncDictSQLiteFastestBeta(
            str(db_path),
            fast_mode=True
        )
        
        start = time.time()
        for i in range(count):
            value = await db.aget(f'key_{i}')
        read_time = time.time() - start
        print(f"読み込み {count}件（初回）: {read_time:.3f}秒 ({count/read_time:.0f} ops/s)")
        
        # Read test (cache hit)
        start = time.time()
        for i in range(count):
            value = await db.aget(f'key_{i}')
        cached_time = time.time() - start
        print(f"読み込み {count}件（キャッシュヒット）: {cached_time:.3f}秒 ({count/cached_time:.0f} ops/s)")
        print(f"キャッシュヒット高速化: {read_time/cached_time:.1f}倍")
        
        await db.aclose()
        print("✅ 性能テスト完了")


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("DictSQLite-Fastest Beta v2 最適化テスト")
    print("="*80)
    
    # Sync tests
    try:
        test_sync_fast_mode()
    except Exception as e:
        print(f"❌ 同期版テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Async tests
    try:
        asyncio.run(test_async_fast_mode())
    except Exception as e:
        print(f"❌ 非同期版テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Performance tests
    try:
        asyncio.run(test_async_performance())
    except Exception as e:
        print(f"❌ 性能テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n" + "="*80)
    print("✅ 全テスト成功")
    print("="*80)


if __name__ == "__main__":
    main()
