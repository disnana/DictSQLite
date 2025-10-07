#!/usr/bin/env python3
"""DictSQLite-Fastest Beta 新機能デモ.

2024年10月の最適化で追加された新機能を実演します。
"""

import sys
from pathlib import Path

# ベータモジュールのパスを追加
sys.path.insert(0, str(Path(__file__).parent))

from dictsqlite_fastest_beta import DictSQLiteFastestBeta


def demo_bulk_operations():
    """バルク操作の最適化デモ."""
    print("\n" + "=" * 70)
    print("  デモ1: バルク操作の最適化")
    print("=" * 70)
    
    with DictSQLiteFastestBeta('demo_bulk.db') as db:
        print("\n1. 大量データのバルク挿入（1000件）...")
        data = {f'item_{i}': {'id': i, 'value': f'data_{i}'} for i in range(1000)}
        
        import time
        start = time.perf_counter()
        db.bulk_insert(data)
        elapsed = time.perf_counter() - start
        
        print(f"   完了: {elapsed:.4f}秒 ({len(data)/elapsed:.0f}件/秒)")
        print("   ✅ 100件以上のバルクは自動的に直接書き込みで高速化")
        
        # 統計確認
        stats = db.get_beta_stats()
        print(f"\n   ディスク書き込み: {stats['operations']['disk_writes']}回")
        print(f"   バッファフラッシュ: {stats['operations']['buffer_flushes']}回")


def demo_pattern_prefetch():
    """パターンマッチング先読みデモ."""
    print("\n" + "=" * 70)
    print("  デモ2: パターンマッチング先読み")
    print("=" * 70)
    
    with DictSQLiteFastestBeta('demo_prefetch.db') as db:
        # テストデータを作成
        print("\n1. テストデータの作成...")
        for i in range(50):
            db[f'user_{i}'] = {'name': f'User {i}', 'score': i * 10}
        for i in range(30):
            db[f'product_{i}'] = {'name': f'Product {i}', 'price': i * 100}
        
        db.flush()
        print("   完了: 合計80件のデータを作成")
        
        # キャッシュをクリア
        db.clear_cache()
        
        # パターンマッチングで先読み
        print("\n2. 'user_'パターンでプリフェッチ...")
        db.bulk_prefetch('user_%', limit=20)
        
        stats = db.get_beta_stats()
        print(f"   キャッシュサイズ: {stats['cache']['size']}件")
        print("   ✅ 関連データが一括でキャッシュにロードされました")
        
        # キャッシュからの高速アクセス
        print("\n3. キャッシュからのアクセス...")
        import time
        start = time.perf_counter()
        for i in range(10):
            _ = db[f'user_{i}']
        elapsed = time.perf_counter() - start
        
        print(f"   10件の読み込み: {elapsed:.6f}秒")
        print(f"   キャッシュヒット率: {stats['cache']['hit_rate']:.2f}%")


def demo_auto_tuning():
    """自動チューニングデモ."""
    print("\n" + "=" * 70)
    print("  デモ3: 自動パラメータチューニング")
    print("=" * 70)
    
    # 小さいキャッシュから始める
    with DictSQLiteFastestBeta('demo_autotune.db', cache_capacity=100) as db:
        print("\n1. 初期設定:")
        stats = db.get_beta_stats()
        print(f"   キャッシュ容量: {stats['cache']['capacity']}件")
        
        # 大量のデータにアクセス（キャッシュミスが多発）
        print("\n2. 1000件のデータを作成して繰り返しアクセス...")
        for i in range(1000):
            db[f'key_{i}'] = f'value_{i}'
        
        # 多数のアクセスでキャッシュミスを発生させる
        for _ in range(5):
            for i in range(200):
                _ = db[f'key_{i}']
        
        stats = db.get_beta_stats()
        print(f"   総操作数: {stats['performance']['total_operations']}")
        print(f"   キャッシュヒット率: {stats['cache']['hit_rate']:.2f}%")
        
        # さらにアクセスして自動チューニングをトリガー
        print("\n3. さらにアクセス（自動チューニングがトリガーされます）...")
        for i in range(10000):
            _ = db.get(f'key_{i % 1000}', None)
        
        stats = db.get_beta_stats()
        print(f"   調整後のキャッシュ容量: {stats['cache']['capacity']}件")
        print(f"   キャッシュヒット率: {stats['cache']['hit_rate']:.2f}%")
        if stats['cache']['capacity'] > 100:
            print("   ✅ キャッシュが自動的に拡大されました！")


def demo_enhanced_stats():
    """拡張統計情報デモ."""
    print("\n" + "=" * 70)
    print("  デモ4: 拡張統計情報")
    print("=" * 70)
    
    with DictSQLiteFastestBeta('demo_stats.db', cache_capacity=500) as db:
        # データ操作
        print("\n1. データ操作を実行...")
        for i in range(200):
            db[f'key_{i}'] = {'data': f'value_{i}', 'index': i}
        
        # いくつかのデータを読み込む
        for i in range(100):
            _ = db[f'key_{i}']
        
        # 統計情報を表示
        stats = db.get_beta_stats()
        
        print("\n2. 詳細統計:")
        print("\n   キャッシュ統計:")
        print(f"   - サイズ: {stats['cache']['size']}/{stats['cache']['capacity']}")
        print(f"   - ヒット数: {stats['cache']['hits']}")
        print(f"   - ミス数: {stats['cache']['misses']}")
        print(f"   - ヒット率: {stats['cache']['hit_rate']:.2f}%")
        
        print("\n   操作統計:")
        print(f"   - キャッシュヒット: {stats['operations']['cache_hits']}")
        print(f"   - キャッシュミス: {stats['operations']['cache_misses']}")
        print(f"   - ディスク読み込み: {stats['operations']['disk_reads']}")
        print(f"   - ディスク書き込み: {stats['operations']['disk_writes']}")
        print(f"   - バッファフラッシュ: {stats['operations']['buffer_flushes']}")
        
        print("\n   パフォーマンス指標 (NEW!):")
        print(f"   - キャッシュ効率: {stats['performance']['cache_effectiveness']:.2%}")
        print(f"   - ディスク削減率: {stats['performance']['disk_savings_rate']:.2%}")
        print(f"   - 総操作数: {stats['performance']['total_operations']}")
        
        print("\n   設定:")
        print(f"   - メモリオンリー: {stats['config']['memory_only']}")
        print(f"   - アグレッシブメモリ: {stats['config']['aggressive_memory']}")
        print(f"   - 自動チューニング間隔: {stats['config']['auto_tune_interval']}操作")


def cleanup():
    """デモ用のデータベースファイルをクリーンアップ."""
    import os
    demo_files = [
        'demo_bulk.db',
        'demo_prefetch.db',
        'demo_autotune.db',
        'demo_stats.db'
    ]
    
    for filename in demo_files:
        if os.path.exists(filename):
            os.remove(filename)
            # WALファイルも削除
            for ext in ['-wal', '-shm']:
                wal_file = filename + ext
                if os.path.exists(wal_file):
                    os.remove(wal_file)


if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("  DictSQLite-Fastest Beta 新機能デモ")
    print("  2024年10月の最適化")
    print("=" * 70)
    
    try:
        demo_bulk_operations()
        demo_pattern_prefetch()
        demo_auto_tuning()
        demo_enhanced_stats()
        
        print("\n" + "=" * 70)
        print("  すべてのデモが完了しました！")
        print("=" * 70)
        
    finally:
        # クリーンアップ
        cleanup()
        print("\n✓ クリーンアップ完了\n")
