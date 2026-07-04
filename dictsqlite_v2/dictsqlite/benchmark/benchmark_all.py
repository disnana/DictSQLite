"""
DictSQLite benchmark suite.

The suite intentionally covers correctness-adjacent performance cases:
write buffering, cold reads, table modes, flush/clear/delete, and concurrency.

Usage:
    python benchmark_all.py --profile quick
    python benchmark_all.py --profile full
    python benchmark_all.py --profile stress
"""

import argparse
import csv
import gc
import os
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Callable, Iterable, List, Optional


RESULTS_CSV = "benchmark_results.csv"

PROFILES = {
    "quick": {
        "iterations": 250,
        "table_iterations": 100,
        "mutation_iterations": 100,
        "batch_iterations": 50,
        "data_sizes": [32, 1024, 16384],
        "batch_sizes": [10, 100, 1000],
        "record_counts": [100, 1000],
        "thread_counts": [2, 4],
        "per_thread": 250,
    },
    "full": {
        "iterations": 1000,
        "table_iterations": 500,
        "mutation_iterations": 500,
        "batch_iterations": 200,
        "data_sizes": [32, 256, 1024, 16384, 65536],
        "batch_sizes": [10, 100, 1000, 5000],
        "record_counts": [100, 1000, 10000],
        "thread_counts": [2, 4, 8],
        "per_thread": 1000,
    },
    "stress": {
        "iterations": 2000,
        "table_iterations": 1000,
        "mutation_iterations": 1000,
        "batch_iterations": 300,
        "data_sizes": [32, 256, 1024, 16384, 65536, 262144],
        "batch_sizes": [10, 100, 1000, 5000, 20000],
        "record_counts": [1000, 10000, 50000],
        "thread_counts": [2, 4, 8, 16],
        "per_thread": 2000,
    },
}


@dataclass
class BenchmarkResult:
    category: str
    operation: str
    scenario: str
    persist_mode: str
    storage_mode: str
    table_mode: str
    data_size: int
    batch_size: int
    iterations: int
    total_time_ms: float
    avg_time_ms: float
    median_time_ms: float
    p95_time_ms: float
    ops_per_sec: float
    min_time_ms: float
    max_time_ms: float
    std_dev_ms: float
    notes: str = ""


def percentile(values: List[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, int(round((pct / 100.0) * (len(ordered) - 1)))))
    return ordered[idx]


def benchmark_operation(func: Callable[[], object], iterations: int) -> dict:
    times = []
    gc_was_enabled = gc.isenabled()
    gc.disable()
    try:
        for _ in range(iterations):
            start = time.perf_counter()
            func()
            times.append((time.perf_counter() - start) * 1000.0)
    finally:
        if gc_was_enabled:
            gc.enable()

    total = sum(times)
    return {
        "total_ms": total,
        "avg_ms": total / iterations if iterations else 0.0,
        "median_ms": statistics.median(times) if times else 0.0,
        "p95_ms": percentile(times, 95),
        "ops_per_sec": iterations / (total / 1000.0) if total > 0 else 0.0,
        "min_ms": min(times) if times else 0.0,
        "max_ms": max(times) if times else 0.0,
        "std_dev_ms": statistics.stdev(times) if len(times) > 1 else 0.0,
    }


def add_result(
    results: List[BenchmarkResult],
    *,
    category: str,
    operation: str,
    scenario: str,
    persist_mode: str,
    storage_mode: str,
    table_mode: str = "prefix",
    data_size: int,
    batch_size: int,
    iterations: int,
    metrics: dict,
    notes: str = "",
) -> None:
    results.append(
        BenchmarkResult(
            category=category,
            operation=operation,
            scenario=scenario,
            persist_mode=persist_mode,
            storage_mode=storage_mode,
            table_mode=table_mode,
            data_size=data_size,
            batch_size=batch_size,
            iterations=iterations,
            total_time_ms=metrics["total_ms"],
            avg_time_ms=metrics["avg_ms"],
            median_time_ms=metrics["median_ms"],
            p95_time_ms=metrics["p95_ms"],
            ops_per_sec=metrics["ops_per_sec"],
            min_time_ms=metrics["min_ms"],
            max_time_ms=metrics["max_ms"],
            std_dev_ms=metrics["std_dev_ms"],
            notes=notes,
        )
    )


def clean_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)
    for filename in os.listdir(path):
        try:
            os.remove(os.path.join(path, filename))
        except OSError:
            pass


def value_for(storage_mode: str, size: int):
    if storage_mode == "bytes":
        return b"x" * size
    if storage_mode == "json":
        return {"payload": "x" * max(1, size), "size": size, "flag": True}
    if storage_mode == "jsonb":
        return {"payload": "x" * max(1, size), "values": [1, 2, 3], "size": size}
    return {"payload": "x" * max(1, size), "size": size}


def make_db(DictSQLiteV4, db_path: str, persist_mode: str, storage_mode: str, table_mode: str = "prefix"):
    return DictSQLiteV4(
        db_path,
        hot_capacity=100_000,
        persist_mode=persist_mode,
        storage_mode=storage_mode,
        table_mode=table_mode,
        buffer_size=500,
        pool_size=16,
    )


def make_async_db(AsyncDictSQLite, db_path: str, persist_mode: str, storage_mode: str, table_mode: str = "prefix"):
    return AsyncDictSQLite(
        db_path,
        capacity=100_000,
        persist_mode=persist_mode,
        storage_mode=storage_mode,
        table_mode=table_mode,
        buffer_size=500,
    )


def run_sync_core(results, DictSQLiteV4, tmpdir, profile):
    config = PROFILES[profile]
    iterations = config["iterations"]
    data_sizes = config["data_sizes"]
    persist_modes = ["memory", "lazy", "writethrough"]
    storage_modes = ["bytes", "jsonb", "pickle"] if profile == "quick" else ["bytes", "json", "jsonb", "pickle"]

    print("\n### DictSQLiteV4 core ###")
    for persist_mode in persist_modes:
        for storage_mode in storage_modes:
            db_path = os.path.join(tmpdir, f"sync_{persist_mode}_{storage_mode}.db")
            db = make_db(DictSQLiteV4, db_path, persist_mode, storage_mode)
            try:
                for size in data_sizes:
                    value = value_for(storage_mode, size)
                    print(f"  sync set/get mode={persist_mode}/{storage_mode} size={size}")
                    metrics = benchmark_operation(
                        lambda v=value: db.__setitem__(f"set_{time.perf_counter_ns()}", v),
                        iterations,
                    )
                    add_result(
                        results,
                        category="DictSQLiteV4",
                        operation="set",
                        scenario="hot_write",
                        persist_mode=persist_mode,
                        storage_mode=storage_mode,
                        data_size=size,
                        batch_size=1,
                        iterations=iterations,
                        metrics=metrics,
                    )

                    db["read_key"] = value
                    metrics = benchmark_operation(lambda: db.__getitem__("read_key"), iterations)
                    add_result(
                        results,
                        category="DictSQLiteV4",
                        operation="get",
                        scenario="hot_read",
                        persist_mode=persist_mode,
                        storage_mode=storage_mode,
                        data_size=size,
                        batch_size=1,
                        iterations=iterations,
                        metrics=metrics,
                    )

                db.close()
            finally:
                try:
                    db.close()
                except Exception:
                    pass


def run_batch_and_flush(results, DictSQLiteV4, AsyncDictSQLite, tmpdir, profile):
    config = PROFILES[profile]
    iterations = config["batch_iterations"]
    batch_sizes = config["batch_sizes"]
    print("\n### Batch, flush, cold-read ###")

    for cls_name, factory in [
        ("DictSQLiteV4", lambda path: make_db(DictSQLiteV4, path, "lazy", "bytes")),
        ("AsyncDictSQLite", lambda path: make_async_db(AsyncDictSQLite, path, "lazy", "bytes")),
    ]:
        db_path = os.path.join(tmpdir, f"batch_{cls_name}.db")
        db = factory(db_path)
        try:
            for batch_size in batch_sizes:
                items = [(f"batch_{batch_size}_{i}", b"value" * 16) for i in range(batch_size)]
                keys = [key for key, _ in items]
                print(f"  {cls_name} batch size={batch_size}")

                metrics = benchmark_operation(lambda items=items: db.batch_set(items), iterations)
                add_result(
                    results,
                    category=cls_name,
                    operation="batch_set",
                    scenario="batch_hot_write",
                    persist_mode="lazy",
                    storage_mode="bytes",
                    data_size=80,
                    batch_size=batch_size,
                    iterations=iterations,
                    metrics=metrics,
                )

                db.flush()
                metrics = benchmark_operation(lambda keys=keys: db.batch_get(keys), iterations)
                add_result(
                    results,
                    category=cls_name,
                    operation="batch_get",
                    scenario="warm_batch_read",
                    persist_mode="lazy",
                    storage_mode="bytes",
                    data_size=80,
                    batch_size=batch_size,
                    iterations=iterations,
                    metrics=metrics,
                )

            metrics = benchmark_operation(lambda: db.flush(), iterations)
            add_result(
                results,
                category=cls_name,
                operation="flush",
                scenario="lazy_flush",
                persist_mode="lazy",
                storage_mode="bytes",
                data_size=80,
                batch_size=0,
                iterations=iterations,
                metrics=metrics,
            )
        finally:
            try:
                db.close()
            except Exception:
                pass

    for cold_count in config["record_counts"]:
        db_path = os.path.join(tmpdir, f"cold_read_{cold_count}.db")
        db = make_db(DictSQLiteV4, db_path, "lazy", "bytes")
        items = [(f"cold_{i}", b"cold-value") for i in range(cold_count)]
        keys = [key for key, _ in items]
        db.batch_set(items)
        db.flush()
        db.close()

        db = make_db(DictSQLiteV4, db_path, "lazy", "bytes")
        try:
            cold_iterations = 10 if profile == "quick" else 30 if profile == "full" else 50
            metrics = benchmark_operation(lambda keys=keys: db.batch_get(keys), cold_iterations)
            add_result(
                results,
                category="DictSQLiteV4",
                operation="batch_get",
                scenario="cold_storage_read",
                persist_mode="lazy",
                storage_mode="bytes",
                data_size=10,
                batch_size=cold_count,
                iterations=cold_iterations,
                metrics=metrics,
                notes="new instance, cache cold",
            )
        finally:
            db.close()


def run_table_benchmarks(results, DictSQLiteV4, AsyncDictSQLite, tmpdir, profile):
    iterations = PROFILES[profile]["table_iterations"]
    print("\n### TableProxy modes ###")
    for cls_name, factory in [
        ("TableProxy", lambda path, mode: make_db(DictSQLiteV4, path, "lazy", "bytes", mode)),
        ("AsyncTableProxy", lambda path, mode: make_async_db(AsyncDictSQLite, path, "lazy", "bytes", mode)),
    ]:
        for table_mode in ["prefix", "separate"]:
            db_path = os.path.join(tmpdir, f"table_{cls_name}_{table_mode}.db")
            db = factory(db_path, table_mode)
            table = db.table("bench_table")
            try:
                print(f"  {cls_name} table_mode={table_mode}")
                metrics = benchmark_operation(
                    lambda: table.__setitem__(f"key_{time.perf_counter_ns()}", b"table-value"),
                    iterations,
                )
                add_result(
                    results,
                    category=cls_name,
                    operation="table_set",
                    scenario="table_write",
                    persist_mode="lazy",
                    storage_mode="bytes",
                    table_mode=table_mode,
                    data_size=11,
                    batch_size=1,
                    iterations=iterations,
                    metrics=metrics,
                )

                table["read_key"] = b"table-value"
                metrics = benchmark_operation(lambda: table.__getitem__("read_key"), iterations)
                add_result(
                    results,
                    category=cls_name,
                    operation="table_get",
                    scenario="table_read",
                    persist_mode="lazy",
                    storage_mode="bytes",
                    table_mode=table_mode,
                    data_size=11,
                    batch_size=1,
                    iterations=iterations,
                    metrics=metrics,
                )

                metrics = benchmark_operation(lambda: table.__contains__("read_key"), iterations)
                add_result(
                    results,
                    category=cls_name,
                    operation="table_contains",
                    scenario="table_membership",
                    persist_mode="lazy",
                    storage_mode="bytes",
                    table_mode=table_mode,
                    data_size=11,
                    batch_size=1,
                    iterations=iterations,
                    metrics=metrics,
                )
            finally:
                try:
                    db.close()
                except Exception:
                    pass


def run_mutation_benchmarks(results, DictSQLiteV4, tmpdir, profile):
    iterations = PROFILES[profile]["mutation_iterations"]
    print("\n### Delete and clear ###")
    db_path = os.path.join(tmpdir, "mutation.db")
    db = make_db(DictSQLiteV4, db_path, "writethrough", "bytes")
    try:
        def set_then_delete():
            key = f"delete_{time.perf_counter_ns()}"
            db[key] = b"value"
            del db[key]

        metrics = benchmark_operation(set_then_delete, iterations)
        add_result(
            results,
            category="DictSQLiteV4",
            operation="delete",
            scenario="set_then_delete",
            persist_mode="writethrough",
            storage_mode="bytes",
            data_size=5,
            batch_size=1,
            iterations=iterations,
            metrics=metrics,
        )

        def fill_then_clear():
            db.batch_set([(f"clear_{time.perf_counter_ns()}_{i}", b"value") for i in range(100)])
            db.clear()

        metrics = benchmark_operation(fill_then_clear, max(10, iterations // 10))
        add_result(
            results,
            category="DictSQLiteV4",
            operation="clear",
            scenario="clear_100_items",
            persist_mode="writethrough",
            storage_mode="bytes",
            data_size=5,
            batch_size=100,
            iterations=max(10, iterations // 10),
            metrics=metrics,
        )
    finally:
        db.close()


def run_concurrency_benchmarks(results, DictSQLiteV4, tmpdir, profile):
    config = PROFILES[profile]
    threads = config["thread_counts"]
    per_thread = config["per_thread"]
    print("\n### Threaded access ###")
    for thread_count in threads:
        db_path = os.path.join(tmpdir, f"threads_{thread_count}.db")
        db = make_db(DictSQLiteV4, db_path, "memory", "bytes")
        try:
            def worker(worker_id: int):
                for i in range(per_thread):
                    key = f"t{worker_id}_{i}"
                    db[key] = b"value"
                    _ = db[key]

            print(f"  threads={thread_count} ops/thread={per_thread}")
            start = time.perf_counter()
            with ThreadPoolExecutor(max_workers=thread_count) as executor:
                list(executor.map(worker, range(thread_count)))
            total_ms = (time.perf_counter() - start) * 1000.0
            total_ops = thread_count * per_thread * 2
            metrics = {
                "total_ms": total_ms,
                "avg_ms": total_ms / total_ops,
                "median_ms": total_ms / total_ops,
                "p95_ms": 0.0,
                "ops_per_sec": total_ops / (total_ms / 1000.0),
                "min_ms": 0.0,
                "max_ms": 0.0,
                "std_dev_ms": 0.0,
            }
            add_result(
                results,
                category="DictSQLiteV4",
                operation="mixed_get_set",
                scenario=f"threaded_{thread_count}",
                persist_mode="memory",
                storage_mode="bytes",
                data_size=5,
                batch_size=thread_count,
                iterations=total_ops,
                metrics=metrics,
            )
        finally:
            db.close()


def run_benchmarks(profile: str):
    try:
        from dictsqlite import AsyncDictSQLite, DictSQLiteV4
    except ImportError:
        print("dictsqlite is not installed.")
        print("Run: maturin develop --release")
        sys.exit(1)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    tmpdir = os.path.join(script_dir, "_bench_data")
    clean_dir(tmpdir)

    print("=" * 72)
    print(f"DictSQLite benchmark start ({profile})")
    print("=" * 72)

    results: List[BenchmarkResult] = []
    run_sync_core(results, DictSQLiteV4, tmpdir, profile)
    run_batch_and_flush(results, DictSQLiteV4, AsyncDictSQLite, tmpdir, profile)
    run_table_benchmarks(results, DictSQLiteV4, AsyncDictSQLite, tmpdir, profile)
    run_mutation_benchmarks(results, DictSQLiteV4, tmpdir, profile)
    run_concurrency_benchmarks(results, DictSQLiteV4, tmpdir, profile)
    return results


def save_results(results: List[BenchmarkResult], filepath: str):
    fieldnames = [
        "category",
        "operation",
        "scenario",
        "persist_mode",
        "storage_mode",
        "table_mode",
        "data_size",
        "batch_size",
        "iterations",
        "total_time_ms",
        "avg_time_ms",
        "median_time_ms",
        "p95_time_ms",
        "ops_per_sec",
        "min_time_ms",
        "max_time_ms",
        "std_dev_ms",
        "notes",
    ]

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            row = r.__dict__.copy()
            for key in [
                "total_time_ms",
                "avg_time_ms",
                "median_time_ms",
                "p95_time_ms",
                "ops_per_sec",
                "min_time_ms",
                "max_time_ms",
                "std_dev_ms",
            ]:
                row[key] = f"{row[key]:.6f}"
            writer.writerow(row)

    print(f"\nSaved: {filepath}")


def print_summary(results: List[BenchmarkResult]):
    print("\n" + "=" * 72)
    print("Benchmark summary")
    print("=" * 72)
    print(
        f"{'Category':<16} {'Operation':<16} {'Scenario':<18} "
        f"{'Mode':<12} {'Store':<8} {'Ops/sec':>12} {'p95(ms)':>10}"
    )
    print("-" * 96)
    for r in sorted(results, key=lambda item: (item.category, item.operation, item.scenario)):
        print(
            f"{r.category:<16} {r.operation:<16} {r.scenario:<18} "
            f"{r.persist_mode:<12} {r.storage_mode:<8} {r.ops_per_sec:>12.1f} {r.p95_time_ms:>10.4f}"
        )


def parse_args(argv: Optional[Iterable[str]] = None):
    parser = argparse.ArgumentParser(description="Run DictSQLite benchmark suite.")
    parser.add_argument(
        "--profile",
        choices=sorted(PROFILES.keys()),
        default="quick",
        help="quick is for smoke checks, full is broad, stress uses large sizes and quantities.",
    )
    parser.add_argument(
        "--output",
        default=RESULTS_CSV,
        help="CSV output path, relative to benchmark directory by default.",
    )
    return parser.parse_args(argv)


def main():
    args = parse_args()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    results = run_benchmarks(args.profile)
    save_results(results, args.output)
    print_summary(results)


if __name__ == "__main__":
    main()
