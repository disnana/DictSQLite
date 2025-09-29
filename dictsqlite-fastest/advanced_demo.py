#!/usr/bin/env python3
"""
DictSQLite-Fastest Advanced APSW & Asyncio Demonstration
高度なAPSWとAsyncio最適化の実演
"""

import asyncio
import time
import sys
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add dictsqlite-fastest to path
sys.path.insert(0, os.path.dirname(__file__))

from dictsqlite_fastest.main import DictSQLiteFastest, AsyncDictSQLiteFastest

async def demo_apsw_advanced_features():
    """APSW高度機能のデモンストレーション"""
    print("🚀 APSW高度機能デモンストレーション")
    print("="*50)
    
    # APSW最適化バルク操作のテスト
    temp_dir = tempfile.gettempdir()
    db = DictSQLiteFastest(os.path.join(temp_dir, 'apsw_advanced_demo.db'), 
                          enable_memory_optimization=True,
                          cache_size=-128000,  # 128MB cache
                          mmap_size=536870912)  # 512MB mmap
    
    # 大量データの準備
    print("📦 大量データでのAPSW最適化バルク操作テスト")
    large_dataset = {f'apsw_key_{i}': f'large_value_{i}_' + 'x' * 100 for i in range(5000)}
    
    # 1. APSW最適化バルク挿入
    start = time.perf_counter()
    db.bulk_insert_apsw_optimized(large_dataset)
    apsw_insert_time = time.perf_counter() - start
    print(f"  APSW最適化バルク挿入 (5000件): {apsw_insert_time:.4f}秒")
    
    # 2. APSW最適化バルク取得
    keys_sample = list(large_dataset.keys())[:1000]
    start = time.perf_counter()
    retrieved_data = db.bulk_get_apsw_optimized(keys_sample)
    apsw_get_time = time.perf_counter() - start
    print(f"  APSW最適化バルク取得 (1000件): {apsw_get_time:.4f}秒")
    print(f"  取得成功率: {len(retrieved_data)}/{len(keys_sample)} ({len(retrieved_data)/len(keys_sample)*100:.1f}%)")
    
    # 3. APSW最適化バルク削除
    keys_to_delete = keys_sample[:500]
    start = time.perf_counter()
    deleted_count = db.bulk_delete_apsw_optimized(keys_to_delete)
    apsw_delete_time = time.perf_counter() - start
    print(f"  APSW最適化バルク削除 (500件): {apsw_delete_time:.4f}秒")
    print(f"  削除件数: {deleted_count}")
    
    # パフォーマンス統計表示
    stats = db.get_performance_stats()
    print(f"\n📊 データベース統計:")
    for key, value in stats.items():
        print(f"    {key}: {value}")
    
    db.close()
    print("✅ APSW高度機能デモ完了\n")

async def demo_asyncio_advanced_features():
    """Asyncio高度機能のデモンストレーション"""
    print("⚡ Asyncio高度機能デモンストレーション")
    print("="*50)
    
    # 高度な非同期接続プール設定
    temp_dir = tempfile.gettempdir()
    async with AsyncDictSQLiteFastest(os.path.join(temp_dir, 'async_advanced_demo.db'), 
                                      max_connections=8,
                                      enable_pipeline=True) as db:
        
        # 1. 非同期並行挿入テスト
        print("🔄 非同期並行操作テスト")
        concurrent_data = {f'async_key_{i}': f'async_value_{i}_' + 'y' * 50 for i in range(2000)}
        
        start = time.perf_counter()
        # 非同期バルク挿入
        await db.abulk_insert(concurrent_data)
        async_bulk_time = time.perf_counter() - start
        print(f"  非同期バルク挿入 (2000件): {async_bulk_time:.4f}秒")
        
        # 2. 並行読み取りテスト
        keys_list = list(concurrent_data.keys())
        chunk_size = 250
        key_chunks = [keys_list[i:i+chunk_size] for i in range(0, len(keys_list), chunk_size)]
        
        start = time.perf_counter()
        # 並行バルク取得
        tasks = [db.abulk_get(chunk) for chunk in key_chunks]
        results = await asyncio.gather(*tasks)
        async_concurrent_time = time.perf_counter() - start
        
        total_retrieved = sum(len(result) for result in results)
        print(f"  非同期並行取得 ({len(key_chunks)}並行, 合計{total_retrieved}件): {async_concurrent_time:.4f}秒")
        
        # 3. パイプライン操作テスト
        print("🔧 パイプライン操作テスト")
        pipeline_operations = []
        
        # 複数の操作を一つのパイプラインに
        for i in range(100):
            pipeline_operations.append(('set', f'pipeline_key_{i}', f'pipeline_value_{i}'))
        
        for i in range(50):
            pipeline_operations.append(('get', f'async_key_{i}', None))
        
        for i in range(25):
            pipeline_operations.append(('delete', f'async_key_{i+1000}', None))
        
        start = time.perf_counter()
        pipeline_results = await db.apipeline_operations(pipeline_operations)
        pipeline_time = time.perf_counter() - start
        print(f"  パイプライン操作 ({len(pipeline_operations)}操作): {pipeline_time:.4f}秒")
        
        # 4. 接続プール統計
        pool_stats = db.get_stats()
        print(f"\n📊 非同期操作統計:")
        print(f"    総操作数: {pool_stats['async_operations']['total_operations']}")
        print(f"    バルク操作数: {pool_stats['async_operations']['bulk_operations']}")
        print(f"    パイプライン操作数: {pool_stats['async_operations']['pipeline_operations']}")
        print(f"    キャッシュヒット数: {pool_stats['async_operations']['cache_hits']}")
        print(f"    接続プール統計: {pool_stats['connection_pool']}")
    
    print("✅ Asyncio高度機能デモ完了\n")

async def demo_concurrent_performance():
    """並行性能デモンストレーション"""
    print("🚀 並行性能比較デモンストレーション")
    print("="*50)
    
    def sync_worker(worker_id, operations_count):
        """同期ワーカー"""
        temp_dir = tempfile.gettempdir()
        db_path = os.path.join(temp_dir, f'sync_worker_{worker_id}.db')
        with DictSQLiteFastest(db_path) as db:
            for i in range(operations_count):
                key = f'worker_{worker_id}_item_{i}'
                value = f'data_{worker_id}_{i}_' + 'z' * 30
                db[key] = value
                retrieved = db[key]
                assert retrieved == value
        return worker_id
    
    async def async_worker(worker_id, operations_count, async_db):
        """非同期ワーカー"""
        for i in range(operations_count):
            key = f'async_worker_{worker_id}_item_{i}'
            value = f'async_data_{worker_id}_{i}_' + 'a' * 30
            await async_db.aset(key, value)
            retrieved = await async_db.aget(key)
            assert retrieved == value
        return worker_id
    
    operations_per_worker = 200
    worker_counts = [2, 4, 6, 8]
    
    for worker_count in worker_counts:
        print(f"  👥 ワーカー数: {worker_count}")
        
        # 同期バージョンテスト
        start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = [executor.submit(sync_worker, i, operations_per_worker) 
                      for i in range(worker_count)]
            sync_results = [future.result() for future in as_completed(futures)]
        sync_time = time.perf_counter() - start
        
        # 非同期バージョンテスト
        temp_dir = tempfile.gettempdir()
        async with AsyncDictSQLiteFastest(os.path.join(temp_dir, 'async_concurrent_demo.db'), 
                                          max_connections=worker_count) as async_db:
            start = time.perf_counter()
            async_tasks = [async_worker(i, operations_per_worker, async_db) 
                          for i in range(worker_count)]
            async_results = await asyncio.gather(*async_tasks)
            async_time = time.perf_counter() - start
        
        # パフォーマンス比較
        total_operations = worker_count * operations_per_worker * 2  # read + write
        sync_throughput = total_operations / sync_time
        async_throughput = total_operations / async_time
        
        print(f"    同期処理: {sync_time:.4f}秒 ({sync_throughput:.0f} ops/sec)")
        print(f"    非同期処理: {async_time:.4f}秒 ({async_throughput:.0f} ops/sec)")
        print(f"    非同期高速化: {sync_time/async_time:.2f}倍")
        print()
    
    print("✅ 並行性能デモ完了\n")

async def demo_memory_optimization():
    """メモリ最適化デモンストレーション"""
    print("🧠 メモリ最適化デモンストレーション")
    print("="*50)
    
    # メモリ最適化なし
    print("  📊 メモリ最適化なしでのテスト")
    temp_dir = tempfile.gettempdir()
    db_normal = DictSQLiteFastest(os.path.join(temp_dir, 'memory_normal.db'))
    
    large_data = {f'mem_key_{i}': 'x' * 1000 for i in range(1000)}  # 1MB of data
    
    start = time.perf_counter()
    db_normal.bulk_insert_apsw_optimized(large_data)
    normal_time = time.perf_counter() - start
    
    db_normal.close()
    print(f"    通常挿入時間: {normal_time:.4f}秒")
    
    # メモリ最適化あり
    print("  🚀 メモリ最適化ありでのテスト")
    db_optimized = DictSQLiteFastest(os.path.join(temp_dir, 'memory_optimized.db'),
                                   enable_memory_optimization=True,
                                   enable_compression=True,
                                   compression_threshold=500,
                                   cache_size=-256000,  # 256MB cache
                                   custom_pragma_settings={
                                       'page_size': 65536,
                                       'auto_vacuum': 'INCREMENTAL'
                                   })
    
    start = time.perf_counter()
    db_optimized.bulk_insert_apsw_optimized(large_data)
    optimized_time = time.perf_counter() - start
    
    # データベース最適化実行
    db_optimized.optimize_database(full_optimization=True)
    
    db_optimized.close()
    print(f"    最適化挿入時間: {optimized_time:.4f}秒")
    print(f"    メモリ最適化効果: {normal_time/optimized_time:.2f}倍高速化")
    
    print("✅ メモリ最適化デモ完了\n")

async def main():
    """メインデモ実行"""
    print("🎉 DictSQLite-Fastest 高度APSW & Asyncio機能デモンストレーション")
    print("=" * 70)
    print()
    
    # 各デモを順次実行
    await demo_apsw_advanced_features()
    await demo_asyncio_advanced_features()
    await demo_concurrent_performance()
    await demo_memory_optimization()
    
    print("🎊 全ての高度機能デモが完了しました！")
    print("\nDictSQLite-FastestはAPSWとAsyncioの力を最大限に活用し、")
    print("従来のSQLiteライブラリを大幅に上回るパフォーマンスを実現しています。")

if __name__ == "__main__":
    asyncio.run(main())