#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""非同期版に最適化したパフォーマンステスト.

並行実行を活用して非同期版の真の性能を測定します。
"""

import sys
import os
import time
import asyncio
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dictsqlite_fastest_beta import AsyncDictSQLiteFastestBeta


def format_ops(ops):
    """OPS値をフォーマット."""
    if ops >= 1000000:
        return f"{ops/1000000:.2f}M ops/s"
    elif ops >= 1000:
        return f"{ops/1000:.2f}K ops/s"
    else:
        return f"{ops:.2f} ops/s"


async def test_async_concurrent_write(num_items=10000, concurrency=100):
    """非同期版並行書き込みテスト（最適化版）.
    
    Args:
        num_items: 書き込むアイテム数
        concurrency: 同時実行タスク数
    """
    print(f"\n=== 非同期版 並行書き込みテスト ===")
    print(f"アイテム数: {num_items:,}件、並行度: {concurrency}")
    
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, 'async_concurrent_write.db')
    
    try:
        db = AsyncDictSQLiteFastestBeta(db_path, memory_budget_mb=100, enable_background_flush=False)
        
        # 並行書き込みタスクを作成
        async def write_batch(start_idx, batch_size):
            """バッチ書き込み"""
            tasks = []
            for i in range(start_idx, start_idx + batch_size):
                tasks.append(db.aset(f'key_{i}', f'value_{i}_' + 'x' * 50))
            await asyncio.gather(*tasks)
        
        # バッチに分割して並行実行
        batch_size = concurrency
        num_batches = num_items // batch_size
        
        start = time.perf_counter()
        
        # すべてのバッチを並行実行
        batch_tasks = []
        for batch_idx in range(num_batches):
            start_idx = batch_idx * batch_size
            batch_tasks.append(write_batch(start_idx, batch_size))
        
        await asyncio.gather(*batch_tasks)
        
        duration = time.perf_counter() - start
        ops = num_items / duration
        
        print(f"並行書き込み: {duration:.3f}秒, {format_ops(ops)}")
        
        return {'duration': duration, 'ops': ops, 'concurrency': concurrency}
        
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        # クリーンアップ
        await asyncio.sleep(0.2)


async def test_async_concurrent_read(num_items=10000, concurrency=100):
    """非同期版並行読み込みテスト（最適化版）.
    
    Args:
        num_items: 読み込むアイテム数
        concurrency: 同時実行タスク数
    """
    print(f"\n=== 非同期版 並行読み込みテスト ===")
    print(f"アイテム数: {num_items:,}件、並行度: {concurrency}")
    
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, 'async_concurrent_read.db')
    
    try:
        # データ準備（同期的に）
        db = AsyncDictSQLiteFastestBeta(db_path, memory_budget_mb=100, enable_background_flush=False)
        
        print("データ準備中...")
        prep_tasks = []
        for i in range(num_items):
            prep_tasks.append(db.aset(f'key_{i}', f'value_{i}_' + 'x' * 50))
            if len(prep_tasks) >= 1000:
                await asyncio.gather(*prep_tasks)
                prep_tasks = []
        if prep_tasks:
            await asyncio.gather(*prep_tasks)
        
        await asyncio.sleep(0.2)
        
        # 並行読み込みテスト
        async def read_batch(start_idx, batch_size):
            """バッチ読み込み"""
            tasks = []
            for i in range(start_idx, start_idx + batch_size):
                tasks.append(db.aget(f'key_{i}'))
            await asyncio.gather(*tasks)
        
        batch_size = concurrency
        num_batches = num_items // batch_size
        
        start = time.perf_counter()
        
        # すべてのバッチを並行実行
        batch_tasks = []
        for batch_idx in range(num_batches):
            start_idx = batch_idx * batch_size
            batch_tasks.append(read_batch(start_idx, batch_size))
        
        await asyncio.gather(*batch_tasks)
        
        duration = time.perf_counter() - start
        ops = num_items / duration
        
        print(f"並行読み込み: {duration:.3f}秒, {format_ops(ops)}")
        
        return {'duration': duration, 'ops': ops, 'concurrency': concurrency}
        
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        await asyncio.sleep(0.2)


async def test_async_bulk_concurrent(num_items=10000):
    """非同期版バルク操作テスト（最適化版）."""
    print(f"\n=== 非同期版 バルク操作テスト ===")
    print(f"アイテム数: {num_items:,}件")
    
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, 'async_bulk.db')
    
    try:
        data = {f'key_{i}': f'value_{i}_' + 'x' * 50 for i in range(num_items)}
        
        db = AsyncDictSQLiteFastestBeta(db_path, memory_budget_mb=100, enable_background_flush=False)
        
        # バルク書き込み
        start = time.perf_counter()
        await db.abulk_insert(data)
        duration_write = time.perf_counter() - start
        ops_write = num_items / duration_write
        
        await asyncio.sleep(0.2)
        
        # バルク読み込み
        keys = list(data.keys())
        start = time.perf_counter()
        results = await db.abulk_get(keys)
        duration_read = time.perf_counter() - start
        ops_read = num_items / duration_read
        
        print(f"バルク書き込み: {duration_write:.3f}秒, {format_ops(ops_write)}")
        print(f"バルク読み込み: {duration_read:.3f}秒, {format_ops(ops_read)}")
        
        return {
            'write': {'duration': duration_write, 'ops': ops_write},
            'read': {'duration': duration_read, 'ops': ops_read}
        }
        
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        await asyncio.sleep(0.2)


async def test_different_concurrency_levels():
    """異なる並行度でのパフォーマンステスト."""
    print(f"\n=== 並行度別パフォーマンステスト ===")
    
    results = {}
    concurrency_levels = [1, 10, 50, 100]
    num_items = 1000  # 軽量テスト
    
    for concurrency in concurrency_levels:
        print(f"\n--- 並行度: {concurrency} ---")
        
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, f'async_concurrency_{concurrency}.db')
        
        try:
            db = AsyncDictSQLiteFastestBeta(db_path, memory_budget_mb=50, enable_background_flush=False)
            
            # 並行書き込み
            async def write_task(i):
                await db.aset(f'key_{i}', f'value_{i}_' + 'x' * 50)
            
            start = time.perf_counter()
            
            # 指定された並行度で実行
            for batch_start in range(0, num_items, concurrency):
                batch_end = min(batch_start + concurrency, num_items)
                tasks = [write_task(i) for i in range(batch_start, batch_end)]
                await asyncio.gather(*tasks)
            
            duration = time.perf_counter() - start
            ops = num_items / duration
            
            results[concurrency] = {'duration': duration, 'ops': ops}
            print(f"結果: {duration:.3f}秒, {format_ops(ops)}")
            
        except Exception as e:
            print(f"エラー（並行度{concurrency}）: {e}")
            results[concurrency] = None
        
        await asyncio.sleep(0.2)
    
    return results


async def main():
    """メイン処理."""
    print("=" * 70)
    print("DictSQLite-Fastest Beta 非同期版パフォーマンステスト（最適化版）")
    print("=" * 70)
    print("\n非同期処理の並行実行を活用してテストします")
    
    all_results = {}
    
    # 並行書き込みテスト
    result_write = await test_async_concurrent_write(10000, concurrency=100)
    if result_write:
        all_results['concurrent_write'] = result_write
    
    await asyncio.sleep(1)
    
    # 並行読み込みテスト
    result_read = await test_async_concurrent_read(10000, concurrency=100)
    if result_read:
        all_results['concurrent_read'] = result_read
    
    await asyncio.sleep(1)
    
    # バルク操作テスト
    result_bulk = await test_async_bulk_concurrent(10000)
    if result_bulk:
        all_results['bulk'] = result_bulk
    
    await asyncio.sleep(1)
    
    # 並行度別テスト
    print(f"\n" + "=" * 70)
    concurrency_results = await test_different_concurrency_levels()
    if concurrency_results:
        all_results['concurrency_comparison'] = concurrency_results
    
    # 結果サマリー
    print("\n" + "=" * 70)
    print("テスト完了 - 結果サマリー")
    print("=" * 70)
    
    if 'concurrent_write' in all_results:
        r = all_results['concurrent_write']
        print(f"\n📊 並行書き込み（10,000件、並行度{r['concurrency']}）:")
        print(f"   OPS: {format_ops(r['ops'])}")
        print(f"   実行時間: {r['duration']:.3f}秒")
    
    if 'concurrent_read' in all_results:
        r = all_results['concurrent_read']
        print(f"\n📊 並行読み込み（10,000件、並行度{r['concurrency']}）:")
        print(f"   OPS: {format_ops(r['ops'])}")
        print(f"   実行時間: {r['duration']:.3f}秒")
    
    if 'bulk' in all_results:
        r = all_results['bulk']
        print(f"\n📊 バルク操作（10,000件）:")
        print(f"   バルク書き込み: {format_ops(r['write']['ops'])}")
        print(f"   バルク読み込み: {format_ops(r['read']['ops'])}")
    
    if 'concurrency_comparison' in all_results:
        print(f"\n📊 並行度別パフォーマンス（1,000件）:")
        for conc, result in all_results['concurrency_comparison'].items():
            if result:
                print(f"   並行度{conc:3d}: {format_ops(result['ops'])}")
    
    # レポート保存
    with open('ASYNC_OPTIMIZED_RESULTS.md', 'w', encoding='utf-8') as f:
        f.write("# 非同期版パフォーマンステスト結果（最適化版）\n\n")
        f.write("**測定日時**: 2025年02月10日\n\n")
        f.write("## テスト概要\n\n")
        f.write("非同期処理の並行実行を活用し、`asyncio.gather()`で複数操作を同時実行してパフォーマンスを測定しました。\n\n")
        f.write("---\n\n")
        
        if 'concurrent_write' in all_results:
            r = all_results['concurrent_write']
            f.write("## 1. 並行書き込みテスト\n\n")
            f.write(f"- **アイテム数**: 10,000件\n")
            f.write(f"- **並行度**: {r['concurrency']}\n")
            f.write(f"- **実行時間**: {r['duration']:.3f}秒\n")
            f.write(f"- **OPS**: {format_ops(r['ops'])}\n\n")
        
        if 'concurrent_read' in all_results:
            r = all_results['concurrent_read']
            f.write("## 2. 並行読み込みテスト\n\n")
            f.write(f"- **アイテム数**: 10,000件\n")
            f.write(f"- **並行度**: {r['concurrency']}\n")
            f.write(f"- **実行時間**: {r['duration']:.3f}秒\n")
            f.write(f"- **OPS**: {format_ops(r['ops'])}\n\n")
        
        if 'bulk' in all_results:
            r = all_results['bulk']
            f.write("## 3. バルク操作テスト\n\n")
            f.write(f"- **バルク書き込み**: {format_ops(r['write']['ops'])} ({r['write']['duration']:.3f}秒)\n")
            f.write(f"- **バルク読み込み**: {format_ops(r['read']['ops'])} ({r['read']['duration']:.3f}秒)\n\n")
        
        if 'concurrency_comparison' in all_results:
            f.write("## 4. 並行度別パフォーマンス比較\n\n")
            f.write("| 並行度 | OPS | 実行時間 |\n")
            f.write("|--------|-----|----------|\n")
            for conc, result in sorted(all_results['concurrency_comparison'].items()):
                if result:
                    f.write(f"| {conc} | {format_ops(result['ops'])} | {result['duration']:.3f}秒 |\n")
            f.write("\n")
        
        f.write("---\n\n")
        f.write("## まとめ\n\n")
        f.write("非同期処理の並行実行を活用することで、複数の操作を同時に実行し、\n")
        f.write("実際の非同期版の性能を正確に測定できました。\n\n")
        f.write("**測定環境**: Python 3.12.3, DictSQLite-Fastest Beta v2.0\n")
    
    print(f"\n✅ 詳細レポートを ASYNC_OPTIMIZED_RESULTS.md に保存しました")


if __name__ == '__main__':
    asyncio.run(main())
