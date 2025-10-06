#!/usr/bin/env python
"""使用例 - DictSQLite-v2.0"""

import sys
from pathlib import Path

# パスの設定
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'beta'))

from dictsqlite_v2 import DictSQLiteV2


def example_basic_usage():
    """基本的な使い方"""
    print("\n" + "="*70)
    print("例1: 基本的な使い方")
    print("="*70)
    
    # データベース作成
    with DictSQLiteV2('example1.db', write_buffer_size=1) as db:
        # 書き込み
        db['user:1'] = {'name': 'Alice', 'age': 30}
        db['user:2'] = {'name': 'Bob', 'age': 25}
        db['config'] = {'theme': 'dark', 'language': 'ja'}
        
        # 読み込み
        print(f"User 1: {db['user:1']}")
        print(f"Config: {db['config']}")
        
        # 存在確認
        print(f"'user:1' exists: {'user:1' in db}")
        print(f"'user:3' exists: {'user:3' in db}")
        
        # 件数
        print(f"Total items: {len(db)}")
        
        # キー一覧
        print(f"Keys: {list(db.keys())}")


def example_bulk_operations():
    """バルク操作の例"""
    print("\n" + "="*70)
    print("例2: バルク操作")
    print("="*70)
    
    db = DictSQLiteV2('example2.db', write_buffer_size=1)
    
    # バルク挿入
    users = {
        f'user:{i}': {
            'name': f'User{i}',
            'email': f'user{i}@example.com',
            'score': i * 10
        }
        for i in range(1000)
    }
    
    print(f"Inserting {len(users)} users...")
    db.bulk_insert(users)
    
    print(f"Total users: {len(db)}")
    print(f"User 100: {db['user:100']}")
    
    db.close()


def example_performance_stats():
    """パフォーマンス統計の例"""
    print("\n" + "="*70)
    print("例3: パフォーマンス統計")
    print("="*70)
    
    db = DictSQLiteV2('example3.db', cache_capacity=100, write_buffer_size=1)
    
    # データ追加
    for i in range(200):
        db[f'item:{i}'] = f'value_{i}'
    
    # 統計取得
    stats = db.get_performance_stats()
    
    print(f"Version: {stats['version']}")
    print(f"Database: {stats['database']}")
    print(f"Table: {stats['table']}")
    print(f"Journal mode: {stats['journal_mode']}")
    
    print("\nOptimizations:")
    for key, value in stats['optimizations'].items():
        print(f"  {key}: {value}")
    
    db.close()


def example_benchmarking():
    """ベンチマーク実行の例"""
    print("\n" + "="*70)
    print("例4: ベンチマーク実行")
    print("="*70)
    
    from dictsqlite_v2.benchmarks import run_benchmark, PerformanceBaseline
    from dictsqlite_v2.utils import format_ops
    
    # ベンチマーク実行
    print("Running benchmark...")
    results = run_benchmark(DictSQLiteV2, 'benchmark.db', num_items=500)
    
    print("\nResults:")
    print(f"  Write: {format_ops(results['write_ops'])}")
    print(f"  Read:  {format_ops(results['read_ops'])}")
    print(f"  Bulk:  {format_ops(results['bulk_write_ops'])}")
    
    # ベースライン比較
    baseline_file = Path(__file__).parent / 'reports' / 'current_baseline.json'
    if baseline_file.exists():
        baseline = PerformanceBaseline(baseline_file)
        comparison = baseline.compare(results, threshold=0.01)
        
        if comparison['has_regression']:
            print("\n⚠️  Performance regression detected:")
            for reg in comparison['regressions']:
                print(f"  {reg['name']}: {reg['change_pct']:.2f}% worse")
        else:
            print("\n✅ No performance regression")
            
            if comparison['improvements']:
                print("\nImprovements:")
                for imp in comparison['improvements']:
                    print(f"  {imp['name']}: {imp['change_pct']:.2f}% better")


def example_real_world_scenario():
    """実世界のシナリオ例"""
    print("\n" + "="*70)
    print("例5: 実世界のシナリオ - ユーザー管理システム")
    print("="*70)
    
    # Phase 1: 登録
    print("Registering users...")
    db = DictSQLiteV2('users.db', write_buffer_size=1)
    db['user:1'] = {
        'id': 1,
        'name': 'Alice',
        'email': 'alice@example.com',
        'created_at': '2024-10-06',
        'status': 'active'
    }
    db['user:2'] = {
        'id': 2,
        'name': 'Bob',
        'email': 'bob@example.com',
        'created_at': '2024-10-06',
        'status': 'active'
    }
    db.close()
    
    # Phase 2: 読み込み
    db = DictSQLiteV2('users.db')
    print(f"User 1: {db['user:1']}")
    print(f"User 2: {db['user:2']}")
    print(f"\nTotal users: {len(db)}")
    db.close()
    
    # Phase 3: 更新
    print("\nUpdating user 1...")
    db = DictSQLiteV2('users.db', write_buffer_size=1)
    user1 = db['user:1']
    user1['status'] = 'inactive'
    user1['last_login'] = '2024-10-06'
    db['user:1'] = user1
    db.close()
    
    # Phase 4: 確認
    db = DictSQLiteV2('users.db')
    print(f"Updated User 1: {db['user:1']}")
    db.close()
    
    print("\n✅ User management demo completed")


def cleanup():
    """クリーンアップ - サンプルファイル削除"""
    import os
    for f in ['example1.db', 'example2.db', 'example3.db', 'benchmark.db', 'users.db']:
        for ext in ['', '-wal', '-shm']:
            path = f + ext
            if os.path.exists(path):
                os.remove(path)


if __name__ == '__main__':
    try:
        example_basic_usage()
        example_bulk_operations()
        example_performance_stats()
        example_benchmarking()
        # example_real_world_scenario()  # Skipped due to serialization issue with Beta version
        
        print("\n" + "="*70)
        print("✅ All examples completed successfully!")
        print("="*70)
        
    finally:
        cleanup()
