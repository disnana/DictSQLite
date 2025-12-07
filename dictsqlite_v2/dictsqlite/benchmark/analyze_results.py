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
from typing import List, Dict
from dataclasses import dataclass

# 結果ファイル名（固定）
RESULTS_CSV = "benchmark_results.csv"


@dataclass
class BenchmarkResult:
    category: str
    operation: str
    data_size: int
    iterations: int
    total_time_ms: float
    avg_time_ms: float
    ops_per_sec: float
    min_time_ms: float
    max_time_ms: float
    std_dev_ms: float


def load_results(filepath: str) -> List[BenchmarkResult]:
    """CSVから結果を読み込む"""
    results = []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            results.append(BenchmarkResult(
                category=row["category"],
                operation=row["operation"],
                data_size=int(row["data_size"]),
                iterations=int(row["iterations"]),
                total_time_ms=float(row["total_time_ms"]),
                avg_time_ms=float(row["avg_time_ms"]),
                ops_per_sec=float(row["ops_per_sec"]),
                min_time_ms=float(row["min_time_ms"]),
                max_time_ms=float(row["max_time_ms"]),
                std_dev_ms=float(row["std_dev_ms"]),
            ))
    return results


def create_graphs(results: List[BenchmarkResult]):
    """グラフを生成"""
    try:
        import matplotlib.pyplot as plt
        import matplotlib
        matplotlib.use('Agg')  # GUI不要
    except ImportError:
        print("matplotlibがインストールされていません。")
        print("pip install matplotlib を実行してください。")
        print("\n代わりにテキストレポートを生成します。")
        create_text_report(results)
        return
    
    # 日本語フォント設定
    plt.rcParams['font.family'] = ['DejaVu Sans', 'sans-serif']
    
    # 画像保存先フォルダを作成
    script_dir = os.path.dirname(os.path.abspath(__file__))
    images_dir = os.path.join(script_dir, "images")
    os.makedirs(images_dir, exist_ok=True)
    
    # ============================================================
    # 1. 操作/秒比較（棒グラフ）
    # ============================================================
    fig, ax = plt.subplots(figsize=(12, 6))
    
    categories = list(set(r.category for r in results))
    operations = list(set(r.operation for r in results))
    
    x_positions = range(len(operations))
    width = 0.25
    
    for i, category in enumerate(categories):
        ops_per_sec = []
        for op in operations:
            matching = [r for r in results if r.category == category and r.operation == op]
            if matching:
                ops_per_sec.append(matching[0].ops_per_sec)
            else:
                ops_per_sec.append(0)
        
        offset = (i - len(categories) / 2) * width
        ax.bar([x + offset for x in x_positions], ops_per_sec, width, label=category)
    
    ax.set_xlabel("Operation")
    ax.set_ylabel("Operations/Second")
    ax.set_title("DictSQLite Benchmark: Operations per Second")
    ax.set_xticks(x_positions)
    ax.set_xticklabels(operations, rotation=45, ha='right')
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    img_path = os.path.join(images_dir, "benchmark_ops_per_sec.png")
    plt.savefig(img_path, dpi=150)
    plt.close()
    print(f"保存: {img_path}")
    
    # ============================================================
    # 2. 平均レイテンシ比較
    # ============================================================
    fig, ax = plt.subplots(figsize=(12, 6))
    
    for i, category in enumerate(categories):
        avg_times = []
        ops = []
        for op in operations:
            matching = [r for r in results if r.category == category and r.operation == op]
            if matching:
                avg_times.append(matching[0].avg_time_ms)
                ops.append(op)
        
        if avg_times:
            offset = (i - len(categories) / 2) * width
            ax.bar([x + offset for x in range(len(ops))], avg_times, width, label=category)
    
    ax.set_xlabel("Operation")
    ax.set_ylabel("Average Latency (ms)")
    ax.set_title("DictSQLite Benchmark: Average Latency")
    ax.set_xticks(range(len(operations)))
    ax.set_xticklabels(operations, rotation=45, ha='right')
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    img_path = os.path.join(images_dir, "benchmark_avg_latency.png")
    plt.savefig(img_path, dpi=150)
    plt.close()
    print(f"保存: {img_path}")
    
    # ============================================================
    # 3. データサイズ別性能（get/set操作）
    # ============================================================
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    for idx, op in enumerate(["get", "set"]):
        ax = axes[idx]
        
        for category in categories:
            sizes = []
            ops_per_sec = []
            for r in sorted(results, key=lambda x: x.data_size):
                if r.category == category and r.operation == op:
                    sizes.append(r.data_size)
                    ops_per_sec.append(r.ops_per_sec)
            
            if sizes:
                ax.plot(sizes, ops_per_sec, 'o-', label=category, markersize=8)
        
        ax.set_xlabel("Data Size (bytes)")
        ax.set_ylabel("Operations/Second")
        ax.set_title(f"Performance by Data Size: {op.upper()}")
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_xscale('log')
    
    plt.tight_layout()
    img_path = os.path.join(images_dir, "benchmark_by_data_size.png")
    plt.savefig(img_path, dpi=150)
    plt.close()
    print(f"保存: {img_path}")
    
    # ============================================================
    # 4. カテゴリ別総合比較（レーダーチャート風）
    # ============================================================
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # カテゴリ別の平均ops/sec
    category_avg = {}
    for category in categories:
        cat_results = [r.ops_per_sec for r in results if r.category == category]
        if cat_results:
            category_avg[category] = sum(cat_results) / len(cat_results)
    
    cats = list(category_avg.keys())
    avgs = list(category_avg.values())
    
    bars = ax.barh(cats, avgs, color=['#3498db', '#e74c3c', '#2ecc71', '#f1c40f'][:len(cats)])
    ax.set_xlabel("Average Operations/Second")
    ax.set_title("DictSQLite: Category Performance Comparison")
    ax.grid(axis='x', alpha=0.3)
    
    # 値をバーに表示
    for bar, avg in zip(bars, avgs):
        ax.text(bar.get_width() + 100, bar.get_y() + bar.get_height()/2,
                f'{avg:.0f}', va='center')
    
    plt.tight_layout()
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
        
        report.append(f"{'Operation':<20} {'Size':<10} {'Ops/sec':<12} {'Avg(ms)':<10}")
        report.append("-" * 52)
        
        for r in cat_results:
            report.append(f"{r.operation:<20} {r.data_size:<10} {r.ops_per_sec:<12.1f} {r.avg_time_ms:<10.3f}")
    
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
