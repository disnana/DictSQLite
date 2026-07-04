"""
ベンチマーク結果分析・可視化

benchmark_results.csv を読み込み、各種グラフを生成します。

実行方法:
    python analyze_results.py

出力:
    - benchmark_ops_per_sec.png - 操作/秒比較
    - benchmark_avg_latency.png - 平均レイテンシ比較
    - benchmark_by_data_size.png - データサイズ別性能
    - benchmark_category_comparison.png - カテゴリ別比較
"""

import csv
import os
import sys
import textwrap
from typing import List, Dict
from dataclasses import dataclass
from collections import defaultdict

# 結果ファイル名（固定）
RESULTS_CSV = "benchmark_results.csv"


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


def load_results(filepath: str) -> List[BenchmarkResult]:
    """CSVから結果を読み込む"""
    results = []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            results.append(BenchmarkResult(
                category=row["category"],
                operation=row["operation"],
                scenario=row.get("scenario", "legacy"),
                persist_mode=row.get("persist_mode", "unknown"),
                storage_mode=row.get("storage_mode", "unknown"),
                table_mode=row.get("table_mode", "prefix"),
                data_size=int(row["data_size"]),
                batch_size=int(row.get("batch_size", "1") or "1"),
                iterations=int(row["iterations"]),
                total_time_ms=float(row["total_time_ms"]),
                avg_time_ms=float(row["avg_time_ms"]),
                median_time_ms=float(row.get("median_time_ms", row["avg_time_ms"])),
                p95_time_ms=float(row.get("p95_time_ms", row["max_time_ms"])),
                ops_per_sec=float(row["ops_per_sec"]),
                min_time_ms=float(row["min_time_ms"]),
                max_time_ms=float(row["max_time_ms"]),
                std_dev_ms=float(row["std_dev_ms"]),
                notes=row.get("notes", ""),
            ))
    return results


def short_label(*parts: str, width: int = 22) -> str:
    text = " / ".join(str(p) for p in parts if p)
    return "\n".join(textwrap.wrap(text, width=width, break_long_words=False)) or "-"


def compact_category(category: str) -> str:
    return {
        "DictSQLiteV4": "V4",
        "AsyncDictSQLite": "Async",
        "TableProxy": "Table",
        "AsyncTableProxy": "AsyncTable",
    }.get(category, category.replace("DictSQLite", "DS"))


def compact_operation(operation: str) -> str:
    return {
        "batch_get": "batch get",
        "batch_set": "batch set",
        "mixed_get_set": "mixed",
        "table_contains": "contains",
        "table_get": "table get",
        "table_set": "table set",
    }.get(operation, operation.replace("_", " "))


def compact_scenario(scenario: str) -> str:
    return {
        "batch_hot_write": "hot batch",
        "warm_batch_read": "warm batch",
        "cold_storage_read": "cold read",
        "clear_100_items": "clear 100",
        "set_then_delete": "set+del",
        "table_membership": "membership",
        "table_read": "read",
        "table_write": "write",
        "hot_write": "hot",
        "hot_read": "hot",
        "lazy_flush": "flush",
    }.get(scenario, scenario.replace("_", " "))


def compact_mode(mode: str) -> str:
    return {
        "writethrough": "WT",
        "memory": "mem",
        "lazy": "lazy",
    }.get(mode, mode)


def case_label(result: BenchmarkResult, include_size: bool = True) -> str:
    parts = [
        compact_category(result.category),
        compact_operation(result.operation),
        compact_scenario(result.scenario),
        compact_mode(result.persist_mode),
        result.storage_mode,
    ]
    if include_size:
        if result.data_size:
            parts.append(f"{result.data_size}B")
        if result.batch_size > 1:
            parts.append(f"n={result.batch_size}")
    return short_label(*parts, width=26)


def median(values):
    values = sorted(values)
    if not values:
        return 0.0
    mid = len(values) // 2
    if len(values) % 2:
        return values[mid]
    return (values[mid - 1] + values[mid]) / 2.0


def grouped_metric(results: List[BenchmarkResult], key_func, value_func):
    grouped = defaultdict(list)
    for result in results:
        grouped[key_func(result)].append(value_func(result))
    return {key: median(values) for key, values in grouped.items()}


def create_graphs(results: List[BenchmarkResult]):
    """グラフを生成"""
    try:
        import matplotlib
        matplotlib.use('Agg')  # GUI不要
        import matplotlib.pyplot as plt
    except (ImportError, OSError, PermissionError) as e:
        print(f"matplotlibを使用できません: {e}")
        print("\n代わりにテキストレポートを生成します。")
        create_text_report(results)
        return
    
    plt.rcParams['font.family'] = ['DejaVu Sans', 'sans-serif']
    plt.rcParams['axes.titlesize'] = 13
    plt.rcParams['axes.labelsize'] = 10
    plt.rcParams['legend.fontsize'] = 9
    
    # 画像保存先フォルダを作成
    script_dir = os.path.dirname(os.path.abspath(__file__))
    images_dir = os.path.join(script_dir, "images")
    os.makedirs(images_dir, exist_ok=True)
    
    categories = sorted(set(r.category for r in results))
    operations = sorted(set(r.operation for r in results))

    # ============================================================
    # 1. 操作/秒比較（横棒・中央値集約）
    # ============================================================
    ops_by_case = grouped_metric(
        results,
        lambda r: (r.category, r.operation),
        lambda r: r.ops_per_sec,
    )
    top_cases = sorted(ops_by_case.items(), key=lambda item: item[1], reverse=True)[:24]
    labels = [
        short_label(compact_category(category), compact_operation(operation), width=20)
        for (category, operation), _ in top_cases
    ]
    values = [value for _, value in top_cases]

    fig, ax = plt.subplots(figsize=(13, max(6, len(top_cases) * 0.34)), constrained_layout=True)
    ax.barh(range(len(values)), values, color="#2f7ebc")
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("Operations/Second (median across scenarios)")
    ax.set_title("DictSQLite Benchmark: Fastest Operation Groups")
    ax.grid(axis="x", alpha=0.25)
    max_value = max(values) if values else 0
    ax.set_xlim(0, max_value * 1.18 if max_value else 1)
    for idx, value in enumerate(values):
        ax.text(value + max_value * 0.015, idx, f"{value:,.0f}", va="center", fontsize=8)

    img_path = os.path.join(images_dir, "benchmark_ops_per_sec.png")
    plt.savefig(img_path, dpi=150)
    plt.close()
    print(f"保存: {img_path}")
    
    # ============================================================
    # 2. 平均レイテンシ比較（遅い上位・横棒）
    # ============================================================
    latency_cases = sorted(results, key=lambda r: r.avg_time_ms, reverse=True)[:14]
    labels = [case_label(r) for r in latency_cases]
    values = [r.avg_time_ms for r in latency_cases]
    fig, ax = plt.subplots(figsize=(12, max(5, len(values) * 0.48)), constrained_layout=True)
    ax.barh(range(len(values)), values, color="#d95f02")
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("Average Latency (ms)")
    ax.set_title("DictSQLite Benchmark: Slowest Average Latency Cases")
    ax.grid(axis="x", alpha=0.25)
    max_value = max(values) if values else 0
    ax.set_xlim(0, max_value * 1.18 if max_value else 1)
    for idx, value in enumerate(values):
        ax.text(value + max_value * 0.015, idx, f"{value:.3f}", va="center", fontsize=8)

    img_path = os.path.join(images_dir, "benchmark_avg_latency.png")
    plt.savefig(img_path, dpi=150)
    plt.close()
    print(f"保存: {img_path}")
    
    # ============================================================
    # 3. データサイズ別性能（get/set操作）
    # ============================================================
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5), constrained_layout=True)
    
    for idx, op in enumerate(["get", "set"]):
        ax = axes[idx]

        points = grouped_metric(
            [r for r in results if r.operation == op],
            lambda r: (r.category, r.storage_mode, r.data_size),
            lambda r: r.ops_per_sec,
        )
        series = defaultdict(list)
        for (category, storage_mode, size), value in points.items():
            series[(category, storage_mode)].append((size, value))

        for (category, storage_mode), values_for_series in sorted(series.items()):
            values_for_series.sort()
            sizes = [size for size, _ in values_for_series]
            ops_per_sec = [value for _, value in values_for_series]
            ax.plot(
                sizes,
                ops_per_sec,
                "o-",
                label=f"{category}/{storage_mode}",
                markersize=5,
                linewidth=1.5,
            )
        
        ax.set_xlabel("Data Size (bytes)")
        ax.set_ylabel("Operations/Second (median)")
        ax.set_title(f"Performance by Data Size: {op.upper()}")
        ax.legend(fontsize=7, ncol=2)
        ax.grid(True, alpha=0.3)
        ax.set_xscale('log')

    img_path = os.path.join(images_dir, "benchmark_by_data_size.png")
    plt.savefig(img_path, dpi=150)
    plt.close()
    print(f"保存: {img_path}")

    # ============================================================
    # 3b. バッチサイズ別性能
    # ============================================================
    batch_results = [
        r for r in results
        if r.batch_size > 1 and r.operation in {"batch_get", "batch_set"}
    ]
    if batch_results:
        fig, ax = plt.subplots(figsize=(12, 6), constrained_layout=True)
        points = grouped_metric(
            batch_results,
            lambda r: (r.category, r.operation, r.scenario, r.batch_size),
            lambda r: r.ops_per_sec,
        )
        series = defaultdict(list)
        for (category, operation, scenario, batch_size), value in points.items():
            series[(category, operation, scenario)].append((batch_size, value))

        for (category, operation, scenario), values_for_series in sorted(series.items()):
            values_for_series.sort()
            sizes = [size for size, _ in values_for_series]
            ops = [value for _, value in values_for_series]
            ax.plot(
                sizes,
                ops,
                "o-",
                label=f"{category}/{operation}/{scenario}",
                markersize=5,
                linewidth=1.5,
            )

        ax.set_xlabel("Batch / Record Count")
        ax.set_ylabel("Operations/Second (median)")
        ax.set_title("DictSQLite Benchmark: Batch and Quantity Scaling")
        ax.set_xscale("log")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=7, ncol=1, loc="best")
        img_path = os.path.join(images_dir, "benchmark_by_batch_size.png")
        plt.savefig(img_path, dpi=150)
        plt.close()
        print(f"保存: {img_path}")

    # ============================================================
    # 3c. p95レイテンシ
    # ============================================================
    p95_cases = sorted(results, key=lambda r: r.p95_time_ms, reverse=True)[:14]
    labels = [case_label(r) for r in p95_cases]
    p95 = [r.p95_time_ms for r in p95_cases]
    fig, ax = plt.subplots(figsize=(12, max(5, len(p95) * 0.5)), constrained_layout=True)
    ax.barh(range(len(labels)), p95, color="#7570b3")
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("p95 Latency (ms)")
    ax.set_title("DictSQLite Benchmark: Slowest p95 Latency Cases")
    ax.grid(axis="x", alpha=0.25)
    max_value = max(p95) if p95 else 0
    ax.set_xlim(0, max_value * 1.18 if max_value else 1)
    for idx, value in enumerate(p95):
        ax.text(value + max_value * 0.015, idx, f"{value:.3f}", va="center", fontsize=8)
    img_path = os.path.join(images_dir, "benchmark_p95_latency.png")
    plt.savefig(img_path, dpi=150)
    plt.close()
    print(f"保存: {img_path}")
    
    # ============================================================
    # 4. カテゴリ別総合比較（レーダーチャート風）
    # ============================================================
    fig, ax = plt.subplots(figsize=(11, 6), constrained_layout=True)
    
    # カテゴリ別の平均ops/sec
    category_avg = {}
    for category in categories:
        cat_results = [r.ops_per_sec for r in results if r.category == category]
        if cat_results:
            category_avg[category] = sum(cat_results) / len(cat_results)
    
    cats = list(category_avg.keys())
    avgs = list(category_avg.values())
    
    bars = ax.barh(cats, avgs, color=['#3498db', '#e74c3c', '#2ecc71', '#f1c40f', '#9b59b6'][:len(cats)])
    ax.set_xlabel("Average Operations/Second")
    ax.set_title("DictSQLite: Category Performance Comparison")
    ax.grid(axis='x', alpha=0.3)
    max_avg = max(avgs) if avgs else 0
    ax.set_xlim(0, max_avg * 1.18 if max_avg else 1)
    
    # 値をバーに表示
    for bar, avg in zip(bars, avgs):
        ax.text(bar.get_width() + max_avg * 0.015, bar.get_y() + bar.get_height()/2,
                f'{avg:,.0f}', va='center', fontsize=9)

    img_path = os.path.join(images_dir, "benchmark_category_comparison.png")
    plt.savefig(img_path, dpi=150)
    plt.close()
    print(f"保存: {img_path}")
    
    print(f"\n全グラフの生成が完了しました。保存先: {images_dir}")


def create_text_report(results: List[BenchmarkResult]):
    """テキストレポートを生成（matplotlib不要）"""
    report = []
    report.append("=" * 60)
    report.append("DictSQLite ベンチマークレポート")
    report.append("=" * 60)
    
    # カテゴリ別集計
    categories = list(set(r.category for r in results))
    
    for category in categories:
        report.append(f"\n### {category} ###")
        cat_results = [r for r in results if r.category == category]
        
        report.append(f"{'Operation':<16} {'Scenario':<18} {'Mode':<12} {'Store':<8} {'Size':<8} {'Batch':<8} {'Ops/sec':<12} {'p95(ms)':<10}")
        report.append("-" * 104)
        
        for r in cat_results:
            report.append(
                f"{r.operation:<16} {r.scenario:<18} {r.persist_mode:<12} {r.storage_mode:<8} "
                f"{r.data_size:<8} {r.batch_size:<8} {r.ops_per_sec:<12.1f} {r.p95_time_ms:<10.3f}"
            )
    
    # ファイル出力
    report_text = "\n".join(report)
    with open("benchmark_report.txt", "w", encoding="utf-8") as f:
        f.write(report_text)
    
    print(report_text)
    print("\n保存: benchmark_report.txt")


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, RESULTS_CSV)
    
    if not os.path.exists(csv_path):
        print(f"エラー: {RESULTS_CSV} が見つかりません。")
        print("先に benchmark_all.py を実行してください。")
        sys.exit(1)
    
    results = load_results(csv_path)
    print(f"{len(results)} 件の結果を読み込みました。")
    
    create_graphs(results)


if __name__ == "__main__":
    main()
