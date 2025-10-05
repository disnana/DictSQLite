#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最適化版Beta版の性能テスト
初回読み込みオーバーヘッドの削減効果を測定
"""

import sys
import os
import time
import tempfile
from pathlib import Path
import shutil

# モジュールパスの設定
BASE_DIR = Path(__file__).parent
REPO_ROOT = BASE_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / 'dictsqlite-fastest'))
sys.path.insert(0, str(REPO_ROOT / 'dictsqlite-fastest' / 'beta'))

from dictsqlite_fastest.main import DictSQLiteFastest
from dictsqlite_fastest_beta import DictSQLiteFastestBeta


def format_time(seconds: float) -> str:
    """時間を読みやすくフォーマット"""
    if seconds < 0.001:
        return f"{seconds*1_000_000:.2f}μs"
    elif seconds < 1:
        return f"{seconds*1_000:.2f}ms"
    else:
        return f"{seconds:.3f}s"


def measure_performance(name: str, func, iterations: int = 5):
    """性能を測定"""
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        func()
        end = time.perf_counter()
        times.append(end - start)
    
    avg = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)
    
    return {
        'name': name,
        'avg': avg,
        'min': min_time,
        'max': max_time
    }


def test_initial_read_performance():
    """初回読み込み性能のテスト"""
    print("=" * 80)
    print("初回読み込み性能テスト（キャッシュミス時のオーバーヘッド測定）")
    print("=" * 80)
    
    test_sizes = [100, 1000, 5000]
    
    for count in test_sizes:
        print(f"\n--- {count}件の初回読み込みテスト ---")
        
        temp_dir = Path(tempfile.mkdtemp(prefix="perf_test_"))
        
        # データ準備（Fastest版）
        fastest_path = temp_dir / "fastest.db"
        db = DictSQLiteFastest(str(fastest_path))
        for i in range(count):
            db[f'key_{i}'] = f'value_{i}'
        db.close()
        
        # データ準備（Beta版 - デフォルト設定）
        beta_default_path = temp_dir / "beta_default.db"
        db = DictSQLiteFastestBeta(str(beta_default_path), memory_budget_mb=100)
        for i in range(count):
            db[f'key_{i}'] = f'value_{i}'
        db.close()
        
        # データ準備（Beta版 - 最適化設定）
        beta_optimized_path = temp_dir / "beta_optimized.db"
        db = DictSQLiteFastestBeta(
            str(beta_optimized_path),
            memory_budget_mb=100,
            enable_stats_collection=False,  # 統計収集を無効化
            lazy_tracking_threshold=100,  # 最初の100回は追跡しない
        )
        for i in range(count):
            db[f'key_{i}'] = f'value_{i}'
        db.close()
        
        # Fastest版の読み込み測定
        def fastest_read():
            db = DictSQLiteFastest(str(fastest_path))
            for i in range(count):
                _ = db[f'key_{i}']
            db.close()
        
        fastest_result = measure_performance("Fastest", fastest_read)
        
        # Beta版（デフォルト設定）の読み込み測定
        def beta_default_read():
            db = DictSQLiteFastestBeta(str(beta_default_path), memory_budget_mb=100)
            for i in range(count):
                _ = db[f'key_{i}']
            db.close()
        
        beta_default_result = measure_performance("Beta (デフォルト)", beta_default_read)
        
        # Beta版（最適化設定）の読み込み測定
        def beta_optimized_read():
            db = DictSQLiteFastestBeta(
                str(beta_optimized_path),
                memory_budget_mb=100,
                enable_stats_collection=False,
                lazy_tracking_threshold=100,
            )
            for i in range(count):
                _ = db[f'key_{i}']
            db.close()
        
        beta_optimized_result = measure_performance("Beta (最適化)", beta_optimized_read)
        
        # 結果表示
        print(f"\nFastest版:        平均 {format_time(fastest_result['avg'])} (最小: {format_time(fastest_result['min'])}, 最大: {format_time(fastest_result['max'])})")
        print(f"Beta版(デフォルト): 平均 {format_time(beta_default_result['avg'])} (最小: {format_time(beta_default_result['min'])}, 最大: {format_time(beta_default_result['max'])})")
        print(f"Beta版(最適化):    平均 {format_time(beta_optimized_result['avg'])} (最小: {format_time(beta_optimized_result['min'])}, 最大: {format_time(beta_optimized_result['max'])})")
        
        # 比較
        if beta_default_result['avg'] > fastest_result['avg']:
            ratio_default = beta_default_result['avg'] / fastest_result['avg']
            print(f"\n⚠️  Beta版(デフォルト)はFastest版より {ratio_default:.2f}倍遅い")
        else:
            ratio_default = fastest_result['avg'] / beta_default_result['avg']
            print(f"\n✅ Beta版(デフォルト)はFastest版より {ratio_default:.2f}倍速い")
        
        if beta_optimized_result['avg'] > fastest_result['avg']:
            ratio_optimized = beta_optimized_result['avg'] / fastest_result['avg']
            print(f"⚠️  Beta版(最適化)はFastest版より {ratio_optimized:.2f}倍遅い")
        else:
            ratio_optimized = fastest_result['avg'] / beta_optimized_result['avg']
            print(f"✅ Beta版(最適化)はFastest版より {ratio_optimized:.2f}倍速い")
        
        # 改善効果
        if beta_optimized_result['avg'] < beta_default_result['avg']:
            improvement = (beta_default_result['avg'] - beta_optimized_result['avg']) / beta_default_result['avg'] * 100
            print(f"\n🚀 最適化により {improvement:.1f}% 高速化")
        
        # クリーンアップ
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_single_operation_overhead():
    """単一操作のオーバーヘッドテスト"""
    print("\n" + "=" * 80)
    print("単一操作のオーバーヘッド測定（10,000回の同一キー読み込み）")
    print("=" * 80)
    
    temp_dir = Path(tempfile.mkdtemp(prefix="single_test_"))
    
    # Fastest版
    fastest_path = temp_dir / "fastest.db"
    db_f = DictSQLiteFastest(str(fastest_path))
    db_f['test_key'] = 'test_value'
    
    # Beta版（デフォルト）
    beta_default_path = temp_dir / "beta_default.db"
    db_bd = DictSQLiteFastestBeta(str(beta_default_path), memory_budget_mb=100)
    db_bd['test_key'] = 'test_value'
    
    # Beta版（最適化）
    beta_optimized_path = temp_dir / "beta_optimized.db"
    db_bo = DictSQLiteFastestBeta(
        str(beta_optimized_path),
        memory_budget_mb=100,
        enable_stats_collection=False,
        lazy_tracking_threshold=100,
    )
    db_bo['test_key'] = 'test_value'
    
    iterations = 10000
    
    # Fastest版測定
    start = time.perf_counter()
    for _ in range(iterations):
        _ = db_f['test_key']
    end = time.perf_counter()
    fastest_time = end - start
    fastest_per_op = fastest_time / iterations * 1_000_000
    
    # Beta版（デフォルト）測定
    start = time.perf_counter()
    for _ in range(iterations):
        _ = db_bd['test_key']
    end = time.perf_counter()
    beta_default_time = end - start
    beta_default_per_op = beta_default_time / iterations * 1_000_000
    
    # Beta版（最適化）測定
    start = time.perf_counter()
    for _ in range(iterations):
        _ = db_bo['test_key']
    end = time.perf_counter()
    beta_optimized_time = end - start
    beta_optimized_per_op = beta_optimized_time / iterations * 1_000_000
    
    print(f"\nFastest版:        総時間 {format_time(fastest_time)}, 1回あたり {fastest_per_op:.2f}μs")
    print(f"Beta版(デフォルト): 総時間 {format_time(beta_default_time)}, 1回あたり {beta_default_per_op:.2f}μs")
    print(f"Beta版(最適化):    総時間 {format_time(beta_optimized_time)}, 1回あたり {beta_optimized_per_op:.2f}μs")
    
    if beta_default_per_op > fastest_per_op:
        overhead_default = beta_default_per_op - fastest_per_op
        print(f"\n⚠️  Beta版(デフォルト)は1回あたり {overhead_default:.2f}μsのオーバーヘッド")
    
    if beta_optimized_per_op > fastest_per_op:
        overhead_optimized = beta_optimized_per_op - fastest_per_op
        print(f"⚠️  Beta版(最適化)は1回あたり {overhead_optimized:.2f}μsのオーバーヘッド")
    else:
        speedup = fastest_per_op - beta_optimized_per_op
        print(f"✅ Beta版(最適化)は1回あたり {speedup:.2f}μs速い")
    
    if beta_optimized_per_op < beta_default_per_op:
        improvement = (beta_default_per_op - beta_optimized_per_op) / beta_default_per_op * 100
        print(f"\n🚀 最適化により {improvement:.1f}% 高速化")
    
    db_f.close()
    db_bd.close()
    db_bo.close()
    
    # クリーンアップ
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_cache_hit_performance():
    """キャッシュヒット時の性能テスト"""
    print("\n" + "=" * 80)
    print("キャッシュヒット時の性能テスト（2回目の読み込み）")
    print("=" * 80)
    
    count = 1000
    temp_dir = Path(tempfile.mkdtemp(prefix="cache_test_"))
    
    # Beta版（デフォルト）
    beta_default_path = temp_dir / "beta_default.db"
    db_bd = DictSQLiteFastestBeta(str(beta_default_path), memory_budget_mb=100)
    for i in range(count):
        db_bd[f'key_{i}'] = f'value_{i}'
    
    # Beta版（最適化）
    beta_optimized_path = temp_dir / "beta_optimized.db"
    db_bo = DictSQLiteFastestBeta(
        str(beta_optimized_path),
        memory_budget_mb=100,
        enable_stats_collection=False,
        lazy_tracking_threshold=100,
    )
    for i in range(count):
        db_bo[f'key_{i}'] = f'value_{i}'
    
    # 初回読み込み（キャッシュに載せる）
    for i in range(count):
        _ = db_bd[f'key_{i}']
        _ = db_bo[f'key_{i}']
    
    # 2回目の読み込み（キャッシュヒット）測定
    start = time.perf_counter()
    for i in range(count):
        _ = db_bd[f'key_{i}']
    end = time.perf_counter()
    beta_default_time = end - start
    
    start = time.perf_counter()
    for i in range(count):
        _ = db_bo[f'key_{i}']
    end = time.perf_counter()
    beta_optimized_time = end - start
    
    print(f"\nBeta版(デフォルト): {format_time(beta_default_time)}")
    print(f"Beta版(最適化):    {format_time(beta_optimized_time)}")
    
    if beta_optimized_time < beta_default_time:
        improvement = (beta_default_time - beta_optimized_time) / beta_default_time * 100
        print(f"\n✅ 最適化により {improvement:.1f}% 高速化（キャッシュヒット時）")
    
    db_bd.close()
    db_bo.close()
    
    # クリーンアップ
    shutil.rmtree(temp_dir, ignore_errors=True)


def main():
    """メイン実行"""
    print("=" * 80)
    print("Beta版 最適化性能テスト")
    print("=" * 80)
    print("\n最適化内容:")
    print("  1. 統計収集をオプション化（enable_stats_collection=False）")
    print("  2. アクセス頻度追跡の遅延開始（lazy_tracking_threshold=100）")
    print("  3. バッファチェックの最適化（空の場合はスキップ）")
    print("  4. ロック削減（統計更新をアトミック操作に）")
    print("  5. アクセス頻度追跡の間引き（10回に1回）")
    print()
    
    # テスト実行
    test_initial_read_performance()
    test_single_operation_overhead()
    test_cache_hit_performance()
    
    print("\n" + "=" * 80)
    print("テスト完了")
    print("=" * 80)


if __name__ == '__main__':
    main()
