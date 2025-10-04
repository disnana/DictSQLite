#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""新しいaiosqliteベースのAsyncDictSQLiteFastestのテスト"""

import sys
import asyncio
import tempfile
import time
from pathlib import Path

# パスの設定
sys.path.insert(0, str(Path(__file__).parent / 'dictsqlite-fastest'))
sys.path.insert(0, str(Path(__file__).parent / 'dictsqlite-fastest' / 'beta'))

from dictsqlite_fastest.main import AsyncDictSQLiteFastest
from dictsqlite_fastest_beta_v2 import AsyncDictSQLiteFastestBeta


async def test_fastest():
    """Fastest版の新しい実装をテスト"""
    print("=" * 80)
    print("AsyncDictSQLiteFastest (新aiosqlite実装) テスト")
    print("=" * 80)
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        async with AsyncDictSQLiteFastest(db_path, batch_size=50) as db:
            # 基本操作
            print("\n1. 基本操作テスト")
            await db.aset('key1', 'value1')
            result = await db.aget('key1')
            assert result == 'value1', f"Expected 'value1', got {result}"
            print("  ✓ set/get動作")
            
            # バルク挿入テスト
            print("\n2. バルク挿入テスト (1000件)")
            items = {f'bulk_key_{i}': f'value_{i}' for i in range(1000)}
            
            start = time.perf_counter()
            await db.abulk_insert(items)
            elapsed = time.perf_counter() - start
            
            ops = len(items) / elapsed
            print(f"  時間: {elapsed:.3f}s")
            print(f"  スループット: {ops:,.0f} ops/sec")
            
            # バルク取得テスト
            print("\n3. バルク取得テスト (1000件)")
            keys = list(items.keys())[:100]
            
            start = time.perf_counter()
            results = await db.abulk_get(keys)
            elapsed = time.perf_counter() - start
            
            assert len(results) == len(keys), f"Expected {len(keys)}, got {len(results)}"
            print(f"  時間: {elapsed:.3f}s")
            print(f"  取得数: {len(results)}件")
            
            # 連続書き込みテスト (バッファリング)
            print("\n4. 連続書き込みテスト (5000件)")
            start = time.perf_counter()
            
            for i in range(5000):
                await db.aset(f'write_key_{i}', f'value_{i}')
            
            elapsed = time.perf_counter() - start
            ops = 5000 / elapsed
            
            print(f"  時間: {elapsed:.3f}s")
            print(f"  スループット: {ops:,.0f} ops/sec")
            
            # 統計情報
            print("\n5. 統計情報")
            stats = db.get_stats()
            for key, value in stats.items():
                print(f"  {key}: {value}")
            
            print("\n✅ Fastest版テスト完了")
    
    finally:
        Path(db_path).unlink(missing_ok=True)


async def test_beta():
    """Beta版の修正された実装をテスト"""
    print("\n" + "=" * 80)
    print("AsyncDictSQLiteFastestBeta (修正版) テスト")
    print("=" * 80)
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        async with AsyncDictSQLiteFastestBeta(
            db_path,
            async_batch_size=50
        ) as db:
            # 基本操作
            print("\n1. 基本操作テスト")
            await db.aset('key1', 'value1')
            result = await db.aget('key1')
            assert result == 'value1', f"Expected 'value1', got {result}"
            print("  ✓ set/get動作")
            
            # バルク挿入テスト
            print("\n2. バルク挿入テスト (1000件)")
            items = {f'bulk_key_{i}': f'value_{i}' for i in range(1000)}
            
            start = time.perf_counter()
            await db.abulk_insert(items)
            elapsed = time.perf_counter() - start
            
            ops = len(items) / elapsed
            print(f"  時間: {elapsed:.3f}s")
            print(f"  スループット: {ops:,.0f} ops/sec")
            
            # 連続書き込みテスト (バッファリング)
            print("\n3. 連続書き込みテスト (5000件)")
            start = time.perf_counter()
            
            for i in range(5000):
                await db.aset(f'write_key_{i}', f'value_{i}')
            
            elapsed = time.perf_counter() - start
            ops = 5000 / elapsed
            
            print(f"  時間: {elapsed:.3f}s")
            print(f"  スループット: {ops:,.0f} ops/sec")
            
            # 統計情報
            print("\n4. 統計情報")
            stats = db.get_stats()
            for key, value in stats.items():
                print(f"  {key}: {value}")
            
            print("\n✅ Beta版テスト完了")
    
    finally:
        Path(db_path).unlink(missing_ok=True)


async def compare_performance():
    """Fastest vs Beta パフォーマンス比較"""
    print("\n" + "=" * 80)
    print("パフォーマンス比較: Fastest vs Beta")
    print("=" * 80)
    
    test_size = 5000
    
    # Fastest版
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        async with AsyncDictSQLiteFastest(db_path, batch_size=100) as db:
            start = time.perf_counter()
            for i in range(test_size):
                await db.aset(f'key_{i}', f'value_{i}')
            fastest_time = time.perf_counter() - start
            fastest_ops = test_size / fastest_time
    finally:
        Path(db_path).unlink(missing_ok=True)
    
    # Beta版
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        async with AsyncDictSQLiteFastestBeta(db_path, async_batch_size=100) as db:
            start = time.perf_counter()
            for i in range(test_size):
                await db.aset(f'key_{i}', f'value_{i}')
            beta_time = time.perf_counter() - start
            beta_ops = test_size / beta_time
    finally:
        Path(db_path).unlink(missing_ok=True)
    
    # 結果表示
    print(f"\n連続書き込み ({test_size:,}件):")
    print(f"  Fastest: {fastest_time:.3f}s ({fastest_ops:,.0f} ops/sec)")
    print(f"  Beta:    {beta_time:.3f}s ({beta_ops:,.0f} ops/sec)")
    
    if fastest_time < beta_time:
        ratio = beta_time / fastest_time
        print(f"  → Fastest が {ratio:.2f}x 高速")
    else:
        ratio = fastest_time / beta_time
        print(f"  → Beta が {ratio:.2f}x 高速")


async def main():
    """メインテスト"""
    print("🚀 新しいaiosqlite実装のテスト開始\n")
    
    try:
        await test_fastest()
        await test_beta()
        await compare_performance()
        
        print("\n" + "=" * 80)
        print("✅ すべてのテスト完了！")
        print("=" * 80)
    except Exception as e:
        print(f"\n❌ エラー発生: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    asyncio.run(main())
