"""DictSQLite-Fastest Beta のベンチマークスクリプト.

標準版とBeta版のパフォーマンスを比較します。
"""

import sys
import time
import os
from pathlib import Path

# ベータモジュールのパスを追加
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from dictsqlite_fastest.main import DictSQLiteFastest
from dictsqlite_fastest_beta import DictSQLiteFastestBeta


def benchmark_write(db, num_items):
    """書き込みベンチマーク."""
    start = time.perf_counter()
    
    for i in range(num_items):
        db[f'key_{i}'] = {'id': i, 'value': f'value_{i}', 'data': 'x' * 100}
    
    end = time.perf_counter()
    return end - start


def benchmark_read(db, num_items):
    """読み込みベンチマーク."""
    start = time.perf_counter()
    
    for i in range(num_items):
        _ = db[f'key_{i}']
    
    end = time.perf_counter()
    return end - start


def benchmark_bulk_write(db, num_items):
    """バルク書き込みベンチマーク."""
    data = {f'bulk_key_{i}': {'id': i, 'value': f'value_{i}'} for i in range(num_items)}
    
    start = time.perf_counter()
    db.bulk_insert(data)
    end = time.perf_counter()
    
    return end - start


def benchmark_bulk_read(db, num_items):
    """バルク読み込みベンチマーク."""
    keys = [f'bulk_key_{i}' for i in range(num_items)]
    
    start = time.perf_counter()
    _ = db.bulk_get(keys)
    end = time.perf_counter()
    
    return end - start


def benchmark_mixed_operations(db, num_items):
    """混合操作ベンチマーク."""
    start = time.perf_counter()
    
    # 書き込み
    for i in range(num_items // 2):
        db[f'mixed_key_{i}'] = f'mixed_value_{i}'
    
    # 読み込み
    for i in range(num_items // 4):
        _ = db.get(f'mixed_key_{i}', None)
    
    # 削除
    for i in range(num_items // 4):
        if f'mixed_key_{i}' in db:
            del db[f'mixed_key_{i}']
    
    end = time.perf_counter()
    return end - start


def run_benchmark_suite(name, db_factory, num_items=1000):
    """ベンチマークスイートを実行."""
    print(f"\n{'=' * 60}")
    print(f"  {name}")
    print(f"{'=' * 60}")
    
    results = {}
    
    # 個別書き込み
    print(f"\n1. 個別書き込み ({num_items}件)...")
    with db_factory() as db:
        time_taken = benchmark_write(db, num_items)
        results['individual_write'] = time_taken
        print(f"   完了: {time_taken:.4f}秒 ({num_items/time_taken:.0f}件/秒)")
        if hasattr(db, 'flush'):
            db.flush()
    
    # 個別読み込み（最初の読み込み - キャッシュコールド）
    print(f"\n2. 個別読み込み - 初回 ({num_items}件)...")
    with db_factory() as db:
        time_taken = benchmark_read(db, num_items)
        results['individual_read_cold'] = time_taken
        print(f"   完了: {time_taken:.4f}秒 ({num_items/time_taken:.0f}件/秒)")
    
    # 個別読み込み（2回目 - キャッシュホット）
    print(f"\n3. 個別読み込み - 2回目 ({num_items}件)...")
    with db_factory() as db:
        # 最初に読み込んでキャッシュをウォームアップ
        for i in range(num_items):
            _ = db[f'key_{i}']
        
        # ベンチマーク測定
        time_taken = benchmark_read(db, num_items)
        results['individual_read_hot'] = time_taken
        print(f"   完了: {time_taken:.4f}秒 ({num_items/time_taken:.0f}件/秒)")
    
    # バルク書き込み
    print(f"\n4. バルク書き込み ({num_items}件)...")
    with db_factory() as db:
        time_taken = benchmark_bulk_write(db, num_items)
        results['bulk_write'] = time_taken
        print(f"   完了: {time_taken:.4f}秒 ({num_items/time_taken:.0f}件/秒)")
        if hasattr(db, 'flush'):
            db.flush()
    
    # バルク読み込み
    print(f"\n5. バルク読み込み ({num_items}件)...")
    with db_factory() as db:
        time_taken = benchmark_bulk_read(db, num_items)
        results['bulk_read'] = time_taken
        print(f"   完了: {time_taken:.4f}秒 ({num_items/time_taken:.0f}件/秒)")
    
    # 混合操作
    print(f"\n6. 混合操作 ({num_items}件)...")
    with db_factory() as db:
        time_taken = benchmark_mixed_operations(db, num_items)
        results['mixed'] = time_taken
        print(f"   完了: {time_taken:.4f}秒")
    
    # 統計情報（Beta版のみ）
    if 'Beta' in name:
        print(f"\n統計情報:")
        with db_factory() as db:
            # データをロード
            for i in range(100):
                db[f'stat_key_{i}'] = f'stat_value_{i}'
            
            stats = db.get_beta_stats()
            print(f"  キャッシュヒット率: {stats['cache']['hit_rate']:.2f}%")
            print(f"  ディスク読み込み: {stats['operations']['disk_reads']}")
            print(f"  ディスク書き込み: {stats['operations']['disk_writes']}")
            print(f"  バッファフラッシュ: {stats['operations']['buffer_flushes']}")
    
    return results


def compare_results(standard_results, beta_results):
    """結果を比較して表示."""
    print(f"\n{'=' * 60}")
    print("  パフォーマンス比較")
    print(f"{'=' * 60}")
    print(f"\n{'操作':<25} {'標準版':<12} {'Beta版':<12} {'改善率':<10}")
    print("-" * 60)
    
    for key in standard_results:
        std_time = standard_results[key]
        beta_time = beta_results[key]
        improvement = std_time / beta_time if beta_time > 0 else 0
        
        operation_names = {
            'individual_write': '個別書き込み',
            'individual_read_cold': '個別読み込み(初回)',
            'individual_read_hot': '個別読み込み(2回目)',
            'bulk_write': 'バルク書き込み',
            'bulk_read': 'バルク読み込み',
            'mixed': '混合操作'
        }
        
        op_name = operation_names.get(key, key)
        print(f"{op_name:<25} {std_time:>10.4f}s {beta_time:>10.4f}s {improvement:>8.2f}x")
    
    # 平均改善率
    avg_improvement = sum(standard_results[k] / beta_results[k] 
                         for k in standard_results if beta_results[k] > 0) / len(standard_results)
    print("-" * 60)
    print(f"平均改善率: {avg_improvement:.2f}x")


def main():
    """メイン関数."""
    print("DictSQLite-Fastest Beta ベンチマーク")
    print("=" * 60)
    
    # テスト用のデータベースファイルを削除
    for f in ['benchmark_standard.db', 'benchmark_beta.db']:
        if os.path.exists(f):
            os.remove(f)
    
    num_items = 1000  # ベンチマークのアイテム数
    
    # 標準版のベンチマーク
    standard_results = run_benchmark_suite(
        "DictSQLite-Fastest 標準版",
        lambda: DictSQLiteFastest('benchmark_standard.db'),
        num_items
    )
    
    # Beta版のベンチマーク
    beta_results = run_benchmark_suite(
        "DictSQLite-Fastest Beta版",
        lambda: DictSQLiteFastestBeta(
            'benchmark_beta.db',
            cache_capacity=10000,
            write_buffer_size=1000,
            write_buffer_interval=5.0
        ),
        num_items
    )
    
    # 結果の比較
    compare_results(standard_results, beta_results)
    
    # メモリオンリーモードのベンチマーク
    print(f"\n{'=' * 60}")
    print("  メモリオンリーモード（参考）")
    print(f"{'=' * 60}")
    
    memory_results = run_benchmark_suite(
        "DictSQLite-Fastest Beta版 (メモリオンリー)",
        lambda: DictSQLiteFastestBeta(':memory:', memory_only=True),
        num_items
    )
    
    # クリーンアップ
    print(f"\n{'=' * 60}")
    print("ベンチマーク完了")
    print(f"{'=' * 60}")
    
    # データベースファイルを削除
    for f in ['benchmark_standard.db', 'benchmark_beta.db']:
        if os.path.exists(f):
            os.remove(f)
            print(f"削除: {f}")


if __name__ == '__main__':
    main()
