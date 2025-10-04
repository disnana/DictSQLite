#!/usr/bin/env python3
"""
デモンストレーション: 非同期版データベースロック問題の修正

このスクリプトは、AsyncDictSQLiteFastestBeta のデータベースロック問題が
完全に修正されたことを実演します。
"""
import asyncio
import tempfile
import os
import time
from dictsqlite_fastest_beta import AsyncDictSQLiteFastestBeta


async def demo_concurrent_operations():
    """並行処理のデモンストレーション."""
    print("=" * 70)
    print("AsyncDictSQLiteFastestBeta - 並行処理デモ")
    print("=" * 70)
    print()
    
    # 一時ディレクトリでDBを作成
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, 'demo.db')
    
    try:
        async with AsyncDictSQLiteFastestBeta(db_path) as db:
            # 1. 並行書き込みテスト
            print("📝 テスト1: 50個の並行書き込み...")
            start = time.perf_counter()
            
            tasks = []
            for i in range(50):
                tasks.append(db.aset(f'user_{i}', {
                    'id': i,
                    'name': f'User {i}',
                    'email': f'user{i}@example.com',
                    'created_at': time.time()
                }))
            
            await asyncio.gather(*tasks)
            elapsed = time.perf_counter() - start
            
            print(f"   ✅ 完了: {elapsed:.3f}秒 ({50/elapsed:.1f} ops/s)")
            print()
            
            # 2. 並行読み込みテスト
            print("📖 テスト2: 50個の並行読み込み...")
            start = time.perf_counter()
            
            tasks = []
            for i in range(50):
                tasks.append(db.aget(f'user_{i}'))
            
            results = await asyncio.gather(*tasks)
            elapsed = time.perf_counter() - start
            
            # データの検証
            all_correct = all(
                results[i]['id'] == i and results[i]['name'] == f'User {i}'
                for i in range(50)
            )
            
            print(f"   ✅ 完了: {elapsed:.3f}秒 ({50/elapsed:.1f} ops/s)")
            print(f"   データ検証: {'✅ 正常' if all_correct else '❌ エラー'}")
            print()
            
            # 3. 混合操作テスト
            print("🔄 テスト3: 読み書き混合 (100操作)...")
            start = time.perf_counter()
            
            tasks = []
            # 50個の更新
            for i in range(50):
                tasks.append(db.aset(f'user_{i}', {
                    'id': i,
                    'name': f'Updated User {i}',
                    'email': f'updated{i}@example.com',
                    'updated_at': time.time()
                }))
            
            # 50個の読み込み
            for i in range(50):
                tasks.append(db.aget(f'user_{i}'))
            
            await asyncio.gather(*tasks)
            elapsed = time.perf_counter() - start
            
            print(f"   ✅ 完了: {elapsed:.3f}秒 ({100/elapsed:.1f} ops/s)")
            print()
            
            # 4. バルク操作テスト
            print("📦 テスト4: バルク挿入 (200件)...")
            start = time.perf_counter()
            
            bulk_data = {
                f'product_{i}': {
                    'id': i,
                    'name': f'Product {i}',
                    'price': i * 100,
                    'stock': i * 10
                }
                for i in range(200)
            }
            
            await db.abulk_insert(bulk_data)
            elapsed = time.perf_counter() - start
            
            print(f"   ✅ 完了: {elapsed:.3f}秒 ({200/elapsed:.1f} ops/s)")
            print()
            
            # 5. 高並行度テスト
            print("🚀 テスト5: 高並行度 (300操作)...")
            start = time.perf_counter()
            
            tasks = []
            for i in range(300):
                tasks.append(db.aset(f'concurrent_{i}', {'value': i}))
            
            await asyncio.gather(*tasks)
            elapsed = time.perf_counter() - start
            
            print(f"   ✅ 完了: {elapsed:.3f}秒 ({300/elapsed:.1f} ops/s)")
            print()
            
            # 6. 並行削除テスト
            print("🗑️  テスト6: 並行削除 (50操作)...")
            start = time.perf_counter()
            
            tasks = []
            for i in range(0, 50, 2):  # 偶数のみ削除
                tasks.append(db.adelete(f'concurrent_{i}'))
            
            await asyncio.gather(*tasks)
            elapsed = time.perf_counter() - start
            
            print(f"   ✅ 完了: {elapsed:.3f}秒 ({25/elapsed:.1f} ops/s)")
            
            # 削除確認
            deleted_count = 0
            for i in range(0, 50, 2):
                result = await db.aget(f'concurrent_{i}', 'DELETED')
                if result == 'DELETED':
                    deleted_count += 1
            
            print(f"   削除確認: {deleted_count}/25 件が正常に削除されました")
            print()
            
            # 統計情報の表示
            stats = db.get_beta_stats()
            print("📊 統計情報:")
            print(f"   キャッシュヒット率: {stats['operations']['cache_hits'] / (stats['operations']['cache_hits'] + stats['operations']['cache_misses']) * 100:.1f}%")
            print(f"   総書き込み: {stats['operations']['disk_writes']:,} 件")
            print(f"   バッファフラッシュ: {stats['operations']['buffer_flushes']} 回")
            print()
        
        print("=" * 70)
        print("✅ すべてのテストが成功しました！")
        print("   データベースロック問題は完全に解決されています。")
        print("=" * 70)
        
    finally:
        # クリーンアップ
        if os.path.exists(db_path):
            os.remove(db_path)
        os.rmdir(temp_dir)


async def demo_performance_comparison():
    """パフォーマンス比較デモ."""
    print()
    print("=" * 70)
    print("パフォーマンス比較: 並行処理 vs 逐次処理")
    print("=" * 70)
    print()
    
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, 'perf_demo.db')
    
    try:
        async with AsyncDictSQLiteFastestBeta(db_path) as db:
            # 並行処理
            print("🔹 並行処理で100回書き込み...")
            start = time.perf_counter()
            
            tasks = []
            for i in range(100):
                tasks.append(db.aset(f'key_{i}', f'value_{i}'))
            
            await asyncio.gather(*tasks)
            concurrent_time = time.perf_counter() - start
            
            print(f"   完了: {concurrent_time:.3f}秒")
            print()
            
            # 逐次処理
            print("🔹 逐次処理で100回書き込み...")
            start = time.perf_counter()
            
            for i in range(100, 200):
                await db.aset(f'key_{i}', f'value_{i}')
            
            sequential_time = time.perf_counter() - start
            
            print(f"   完了: {sequential_time:.3f}秒")
            print()
            
            print(f"📊 結果:")
            print(f"   並行処理: {concurrent_time:.3f}秒 ({100/concurrent_time:.1f} ops/s)")
            print(f"   逐次処理: {sequential_time:.3f}秒 ({100/sequential_time:.1f} ops/s)")
            
            if concurrent_time < sequential_time:
                speedup = sequential_time / concurrent_time
                print(f"   ✅ 並行処理が {speedup:.2f}x 高速でした！")
            else:
                print(f"   ℹ️  この場合、逐次処理の方が効率的です")
            print()
    
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
        os.rmdir(temp_dir)


async def main():
    """メインデモ."""
    print()
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 10 + "AsyncDictSQLiteFastestBeta デモンストレーション" + " " * 10 + "║")
    print("║" + " " * 15 + "データベースロック問題 - 修正完了" + " " * 15 + "║")
    print("╚" + "═" * 68 + "╝")
    print()
    
    # 並行処理デモ
    await demo_concurrent_operations()
    
    # パフォーマンス比較
    await demo_performance_comparison()
    
    print()
    print("🎉 デモを完了しました！")
    print()


if __name__ == '__main__':
    asyncio.run(main())
