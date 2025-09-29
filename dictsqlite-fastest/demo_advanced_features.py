#!/usr/bin/env python3
"""
DictSQLite-Fastest 高度機能デモンストレーション
Advanced Features Demonstration for DictSQLite-Fastest
"""

import asyncio
import time
import tempfile
import os
from dictsqlite_fastest.main import DictSQLiteFastest, AsyncDictSQLiteFastest


def demo_basic_optimizations():
    """基本的な最適化機能のデモ"""
    print("🚀 基本最適化機能デモ")
    print("=" * 50)

    # 高性能設定でデータベースを作成
    temp_dir = tempfile.gettempdir()
    with DictSQLiteFastest(
            os.path.join(temp_dir, 'demo_optimized.db'),
            cache_size=-128000,  # 128MBキャッシュ
            mmap_size=536870912,  # 512MBメモリマップド I/O
            enable_memory_optimization=True,
            optimize_on_init=True
    ) as db:
        # 接続ウォームアップ
        db.warmup_connection()

        # パフォーマンス統計を表示
        stats = db.get_performance_stats()
        print(f"パフォーマンス統計: {stats}")

        # 基本操作のテスト
        db['test_key'] = 'test_value'
        print(f"基本操作: {db['test_key']}")

    print("✅ 基本最適化デモ完了\n")


def demo_bulk_operations():
    """バルク操作のデモ"""
    print("📦 バルク操作デモ")
    print("=" * 50)

    temp_dir = tempfile.gettempdir()
    with DictSQLiteFastest(os.path.join(temp_dir, 'demo_bulk.db')) as db:
        # 大量データの準備
        data = {f'bulk_key_{i}': f'bulk_value_{i}' for i in range(1000)}

        # 自動最適化バルク挿入
        start = time.perf_counter()
        db.bulk_insert_optimized(data)
        time_optimized = time.perf_counter() - start
        print(f"自動最適化バルク挿入 (1000件): {time_optimized:.4f}秒")

        # ExecuteMany方式バルク挿入（新しいデータで）
        data_2 = {f'fast_key_{i}': f'fast_value_{i}' for i in range(1000)}
        start = time.perf_counter()
        db.bulk_insert_executemany(data_2)
        time_executemany = time.perf_counter() - start
        print(f"ExecuteManyバルク挿入 (1000件): {time_executemany:.4f}秒")

        # バルク取得
        keys = [f'bulk_key_{i}' for i in range(0, 1000, 10)]
        start = time.perf_counter()
        results = db.bulk_get(keys)
        time_bulk_get = time.perf_counter() - start
        print(f"バルク取得 ({len(keys)}件): {time_bulk_get:.4f}秒")
        print(f"取得成功: {len(results)}件")

        # バルク削除
        start = time.perf_counter()
        db.bulk_delete(keys[:10])
        time_bulk_delete = time.perf_counter() - start
        print(f"バルク削除 (10件): {time_bulk_delete:.4f}秒")

    print("✅ バルク操作デモ完了\n")


def demo_compression():
    """圧縮機能のデモ"""
    print("🗜️  圧縮機能デモ")
    print("=" * 50)

    # 圧縮有効化
    temp_dir = tempfile.gettempdir()
    with DictSQLiteFastest(
            os.path.join(temp_dir, 'demo_compression.db'),
            enable_compression=True,
            compression_threshold=100  # 100バイト以上を圧縮
    ) as db:
        # 小さなデータ（圧縮されない）
        small_data = "小さなデータ"
        db['small'] = small_data

        # 大きなデータ（圧縮される）
        large_data = "これは圧縮される大きなデータです。" * 50
        db['large'] = large_data

        # データの確認
        retrieved_small = db['small']
        retrieved_large = db['large']

        print(f"小さなデータ: {retrieved_small}")
        print(f"大きなデータサイズ: {len(retrieved_large)}文字")
        print(f"大きなデータ一致: {retrieved_large == large_data}")

    print("✅ 圧縮機能デモ完了\n")


def demo_custom_settings():
    """カスタム設定のデモ"""
    print("⚙️  カスタム設定デモ")
    print("=" * 50)

    # カスタムPRAGMA設定
    custom_pragma = {
        'page_size': 65536,
        'auto_vacuum': 'INCREMENTAL',
        'synchronous': 'NORMAL'
    }

    temp_dir = tempfile.gettempdir()
    with DictSQLiteFastest(
            os.path.join(temp_dir, 'demo_custom.db'),
            custom_pragma_settings=custom_pragma,
            enable_memory_optimization=True
    ) as db:
        # データベースを完全最適化
        db.optimize_database(full_optimization=True)

        # テストデータ
        db['config_test'] = {'setting': 'custom', 'value': 12345}

        # 統計情報
        stats = db.get_performance_stats()
        print("カスタム設定適用済み統計:")
        for key, value in stats.items():
            print(f"  {key}: {value}")

    print("✅ カスタム設定デモ完了\n")


async def demo_async_operations():
    """非同期操作のデモ"""
    print("🔄 非同期操作デモ")
    print("=" * 50)

    # 非同期データベースの作成
    temp_dir = tempfile.gettempdir()
    async_db = AsyncDictSQLiteFastest(os.path.join(temp_dir, 'demo_async.db'), max_connections=3)

    try:
        # 非同期で基本操作
        await async_db.aset('async_key', 'async_value')
        value = await async_db.aget('async_key')
        print(f"非同期基本操作: {value}")

        # 並行操作
        async def async_worker(worker_id, count):
            for i in range(count):
                key = f'worker_{worker_id}_item_{i}'
                value = f'data_{worker_id}_{i}'
                await async_db.aset(key, value)
            return f'Worker {worker_id} completed {count} operations'

        # 3つのワーカーで並行処理
        start = time.perf_counter()
        tasks = [async_worker(i, 100) for i in range(3)]
        results = await asyncio.gather(*tasks)
        async_time = time.perf_counter() - start

        print(f"並行処理結果: {results}")
        print(f"非同期並行処理時間 (300操作): {async_time:.4f}秒")

        # 接続プール統計
        pool_stats = async_db._connection_pool.get_stats()
        print(f"接続プール統計: {pool_stats}")

    finally:
        await async_db.aclose()

    print("✅ 非同期操作デモ完了\n")


def main():
    """メインデモ実行"""
    print("🎉 DictSQLite-Fastest 高度機能デモンストレーション")
    print("=" * 60)
    print()

    # 各デモを実行
    demo_basic_optimizations()
    demo_bulk_operations()
    demo_compression()
    demo_custom_settings()

    # 非同期デモ
    asyncio.run(demo_async_operations())

    print("🎊 全てのデモが完了しました！")
    print("\nDictSQLite-Fastestの高度な機能をお楽しみください。")
    print("詳細な情報は PERFORMANCE_IMPROVEMENTS.md をご覧ください。")


if __name__ == "__main__":
    main()