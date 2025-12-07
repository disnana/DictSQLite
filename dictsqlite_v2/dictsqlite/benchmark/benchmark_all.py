"""
DictSQLite 性能ベンチマーク

全API操作のパフォーマンステストを実行し、結果をCSVに保存します。

実行方法:
    python benchmark_all.py

出力:
    benchmark_results.csv - 性能結果データ
"""

import time
import csv
import os
import sys
from dataclasses import dataclass
from typing import List, Dict
import statistics

# 結果ファイル名（固定）
RESULTS_CSV = "benchmark_results.csv"


@dataclass
class BenchmarkResult:
    """ベンチマーク結果"""
    category: str
    operation: str
    data_size: int
    iterations: int
    total_time_ms: float
    avg_time_ms: float
    ops_per_sec: float
    min_time_ms: float = 0.0
    max_time_ms: float = 0.0
    std_dev_ms: float = 0.0


def benchmark_operation(func, iterations: int = 1000) -> Dict[str, float]:
    """単一操作のベンチマーク"""
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        func()
        elapsed = (time.perf_counter() - start) * 1000  # ms
        times.append(elapsed)
    
    total = sum(times)
    return {
        "total_ms": total,
        "avg_ms": total / iterations,
        "ops_per_sec": iterations / (total / 1000) if total > 0 else 0,
        "min_ms": min(times),
        "max_ms": max(times),
        "std_dev_ms": statistics.stdev(times) if len(times) > 1 else 0,
    }


def run_benchmarks():
    """全ベンチマークを実行"""
    try:
        from dictsqlite import DictSQLiteV4, AsyncDictSQLite
    except ImportError:
        print("dictsqliteがインストールされていません。")
        print("maturin develop を実行してください。")
        sys.exit(1)

    results: List[BenchmarkResult] = []
    
    # Windows対応: 固定ディレクトリを使用
    script_dir = os.path.dirname(os.path.abspath(__file__))
    tmpdir = os.path.join(script_dir, "_bench_data")
    os.makedirs(tmpdir, exist_ok=True)
    
    # 既存のDBファイルを削除（エラーは無視）
    for f in os.listdir(tmpdir):
        try:
            os.remove(os.path.join(tmpdir, f))
        except Exception:
            pass
    
    print("=" * 60)
    print("DictSQLite ベンチマーク開始")
    print("=" * 60)
    
    # ============================================================
    # DictSQLiteV4 ベンチマーク
    # ============================================================
    print("\n### DictSQLiteV4 (同期) ###")
    
    db_path = os.path.join(tmpdir, "sync_bench.db")
    db = DictSQLiteV4(db_path, storage_mode="pickle")
    
    data_sizes = [100, 1000, 10000]
    
    for size in data_sizes:
        value = b"x" * size
        
        # set操作
        print(f"  [set] data_size={size}...")
        res = benchmark_operation(
            lambda v=value: db.__setitem__(f"key_{time.perf_counter_ns()}", v),
            iterations=1000
        )
        results.append(BenchmarkResult(
            category="DictSQLiteV4",
            operation="set",
            data_size=size,
            iterations=1000,
            total_time_ms=res["total_ms"],
            avg_time_ms=res["avg_ms"],
            ops_per_sec=res["ops_per_sec"],
            min_time_ms=res["min_ms"],
            max_time_ms=res["max_ms"],
            std_dev_ms=res["std_dev_ms"],
        ))
        
        # get操作
        db["bench_key"] = value
        print(f"  [get] data_size={size}...")
        res = benchmark_operation(
            lambda: db.__getitem__("bench_key"),
            iterations=1000
        )
        results.append(BenchmarkResult(
            category="DictSQLiteV4",
            operation="get",
            data_size=size,
            iterations=1000,
            total_time_ms=res["total_ms"],
            avg_time_ms=res["avg_ms"],
            ops_per_sec=res["ops_per_sec"],
            min_time_ms=res["min_ms"],
            max_time_ms=res["max_ms"],
            std_dev_ms=res["std_dev_ms"],
        ))
    
    # batch操作
    print("  [batch_set] 100 items...")
    items = [(f"batch_key_{i}", b"value" * 10) for i in range(100)]
    res = benchmark_operation(
        lambda: db.batch_set(items),
        iterations=100
    )
    results.append(BenchmarkResult(
        category="DictSQLiteV4",
        operation="batch_set_100",
        data_size=50,
        iterations=100,
        total_time_ms=res["total_ms"],
        avg_time_ms=res["avg_ms"],
        ops_per_sec=res["ops_per_sec"],
        min_time_ms=res["min_ms"],
        max_time_ms=res["max_ms"],
        std_dev_ms=res["std_dev_ms"],
    ))
    
    print("  [batch_get] 100 keys...")
    keys = [f"batch_key_{i}" for i in range(100)]
    res = benchmark_operation(
        lambda: db.batch_get(keys),
        iterations=100
    )
    results.append(BenchmarkResult(
        category="DictSQLiteV4",
        operation="batch_get_100",
        data_size=50,
        iterations=100,
        total_time_ms=res["total_ms"],
        avg_time_ms=res["avg_ms"],
        ops_per_sec=res["ops_per_sec"],
        min_time_ms=res["min_ms"],
        max_time_ms=res["max_ms"],
        std_dev_ms=res["std_dev_ms"],
    ))
    
    # ============================================================
    # AsyncDictSQLite ベンチマーク
    # ============================================================
    print("\n### AsyncDictSQLite (非同期) ###")
    
    async_db_path = os.path.join(tmpdir, "async_bench.db")
    async_db = AsyncDictSQLite(async_db_path)
    
    for size in data_sizes:
        value = b"x" * size
        
        # set操作
        print(f"  [set] data_size={size}...")
        res = benchmark_operation(
            lambda v=value: async_db.__setitem__(f"key_{time.perf_counter_ns()}", v),
            iterations=1000
        )
        results.append(BenchmarkResult(
            category="AsyncDictSQLite",
            operation="set",
            data_size=size,
            iterations=1000,
            total_time_ms=res["total_ms"],
            avg_time_ms=res["avg_ms"],
            ops_per_sec=res["ops_per_sec"],
            min_time_ms=res["min_ms"],
            max_time_ms=res["max_ms"],
            std_dev_ms=res["std_dev_ms"],
        ))
        
        # get操作
        async_db["bench_key"] = value
        print(f"  [get] data_size={size}...")
        res = benchmark_operation(
            lambda: async_db.__getitem__("bench_key"),
            iterations=1000
        )
        results.append(BenchmarkResult(
            category="AsyncDictSQLite",
            operation="get",
            data_size=size,
            iterations=1000,
            total_time_ms=res["total_ms"],
            avg_time_ms=res["avg_ms"],
            ops_per_sec=res["ops_per_sec"],
            min_time_ms=res["min_ms"],
            max_time_ms=res["max_ms"],
            std_dev_ms=res["std_dev_ms"],
        ))
    
    # batch操作
    print("  [batch_set] 100 items...")
    items = [(f"batch_key_{i}", b"value" * 10) for i in range(100)]
    res = benchmark_operation(
        lambda: async_db.batch_set(items),
        iterations=100
    )
    results.append(BenchmarkResult(
        category="AsyncDictSQLite",
        operation="batch_set_100",
        data_size=50,
        iterations=100,
        total_time_ms=res["total_ms"],
        avg_time_ms=res["avg_ms"],
        ops_per_sec=res["ops_per_sec"],
        min_time_ms=res["min_ms"],
        max_time_ms=res["max_ms"],
        std_dev_ms=res["std_dev_ms"],
    ))
    
    print("  [batch_get] 100 keys...")
    keys = [f"batch_key_{i}" for i in range(100)]
    res = benchmark_operation(
        lambda: async_db.batch_get(keys),
        iterations=100
    )
    results.append(BenchmarkResult(
        category="AsyncDictSQLite",
        operation="batch_get_100",
        data_size=50,
        iterations=100,
        total_time_ms=res["total_ms"],
        avg_time_ms=res["avg_ms"],
        ops_per_sec=res["ops_per_sec"],
        min_time_ms=res["min_ms"],
        max_time_ms=res["max_ms"],
        std_dev_ms=res["std_dev_ms"],
    ))
    
    # ============================================================
    # TableProxy ベンチマーク
    # ============================================================
    print("\n### TableProxy ###")
    
    table = db.table("bench_table")
    table["init"] = b"init"
    
    print("  [table set]...")
    res = benchmark_operation(
        lambda: table.__setitem__(f"key_{time.perf_counter_ns()}", b"value_data"),
        iterations=1000
    )
    results.append(BenchmarkResult(
        category="TableProxy",
        operation="set",
        data_size=10,
        iterations=1000,
        total_time_ms=res["total_ms"],
        avg_time_ms=res["avg_ms"],
        ops_per_sec=res["ops_per_sec"],
        min_time_ms=res["min_ms"],
        max_time_ms=res["max_ms"],
        std_dev_ms=res["std_dev_ms"],
    ))
    
    table["get_key"] = b"value_for_get"
    print("  [table get]...")
    res = benchmark_operation(
        lambda: table.__getitem__("get_key"),
        iterations=1000
    )
    results.append(BenchmarkResult(
        category="TableProxy",
        operation="get",
        data_size=13,
        iterations=1000,
        total_time_ms=res["total_ms"],
        avg_time_ms=res["avg_ms"],
        ops_per_sec=res["ops_per_sec"],
        min_time_ms=res["min_ms"],
        max_time_ms=res["max_ms"],
        std_dev_ms=res["std_dev_ms"],
    ))
    
    # Windows: 明示的にclose（ファイルロック解放）
    db.close()
    async_db.close()
    
    return results


def save_results(results: List[BenchmarkResult], filepath: str):
    """結果をCSVに保存"""
    fieldnames = [
        "category", "operation", "data_size", "iterations",
        "total_time_ms", "avg_time_ms", "ops_per_sec",
        "min_time_ms", "max_time_ms", "std_dev_ms"
    ]
    
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow({
                "category": r.category,
                "operation": r.operation,
                "data_size": r.data_size,
                "iterations": r.iterations,
                "total_time_ms": f"{r.total_time_ms:.3f}",
                "avg_time_ms": f"{r.avg_time_ms:.3f}",
                "ops_per_sec": f"{r.ops_per_sec:.1f}",
                "min_time_ms": f"{r.min_time_ms:.3f}",
                "max_time_ms": f"{r.max_time_ms:.3f}",
                "std_dev_ms": f"{r.std_dev_ms:.3f}",
            })
    
    print(f"\n結果を保存しました: {filepath}")


def print_summary(results: List[BenchmarkResult]):
    """サマリーを表示"""
    print("\n" + "=" * 60)
    print("ベンチマーク結果サマリー")
    print("=" * 60)
    
    print(f"\n{'Category':<20} {'Operation':<15} {'Size':<8} {'Ops/sec':<12} {'Avg(ms)':<10}")
    print("-" * 65)
    
    for r in results:
        print(f"{r.category:<20} {r.operation:<15} {r.data_size:<8} {r.ops_per_sec:<12.1f} {r.avg_time_ms:<10.3f}")


if __name__ == "__main__":
    # スクリプトのディレクトリに移動
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    results = run_benchmarks()
    save_results(results, RESULTS_CSV)
    print_summary(results)
