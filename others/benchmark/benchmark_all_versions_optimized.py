"""Optimized benchmark runner: Original vs dictsqlite_v2 vs dictsqlite-fastest beta v2

This optimized version uses separate test modules for each version to avoid
import conflicts and improve reliability.

Compares performance of three key versions:
- DictSQLite (Original): Standard sqlite3-based implementation (dictsqlite/)
- dictsqlite_v2: High-performance Rust extension version 2.0.6 (dictsqlite_v2/dictsqlite/)
- dictsqlite-fastest beta v2: APSW-based async high-performance version
"""

import os
import sys
import tempfile
import subprocess
import csv
import datetime
import json
from pathlib import Path
from typing import Dict, Tuple, List

# Add paths
REPO_ROOT = Path(__file__).parent.parent.parent
BENCHMARK_DIR = REPO_ROOT / 'others' / 'benchmark'
sys.path.insert(0, str(BENCHMARK_DIR))

# Import graph generation libraries
try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("⚠ matplotlib not available. Graphs will not be generated.")


class BenchmarkResult:
    """Stores benchmark results for a single test."""
    
    def __init__(self, name: str):
        self.name = name
        self.original_time = 0.0
        self.v2_time = 0.0
        self.beta_v2_time = 0.0
        self.original_ops = 0.0
        self.v2_ops = 0.0
        self.beta_v2_ops = 0.0
    
    def set_original(self, elapsed: float, ops_per_sec: float):
        self.original_time = elapsed
        self.original_ops = ops_per_sec
    
    def set_v2(self, elapsed: float, ops_per_sec: float):
        self.v2_time = elapsed
        self.v2_ops = ops_per_sec
    
    def set_beta_v2(self, elapsed: float, ops_per_sec: float):
        self.beta_v2_time = elapsed
        self.beta_v2_ops = ops_per_sec
    
    def print_comparison(self):
        """Print comparison of all versions."""
        print(f"\n📊 {self.name}:")
        if self.original_ops > 0:
            print(f"  Original版:        {self.original_time:.3f}s ({self.original_ops:>8.0f} ops/sec)")
        if self.v2_ops > 0:
            if self.original_ops > 0:
                speedup = self.v2_ops / self.original_ops
                print(f"  dictsqlite_v2版:   {self.v2_time:.3f}s ({self.v2_ops:>8.0f} ops/sec) - {speedup:>5.2f}x 🚀")
            else:
                print(f"  dictsqlite_v2版:   {self.v2_time:.3f}s ({self.v2_ops:>8.0f} ops/sec)")
        if self.beta_v2_ops > 0:
            if self.original_ops > 0:
                speedup = self.beta_v2_ops / self.original_ops
                print(f"  Beta v2版:         {self.beta_v2_time:.3f}s ({self.beta_v2_ops:>8.0f} ops/sec) - {speedup:>5.2f}x 🚀")
            else:
                print(f"  Beta v2版:         {self.beta_v2_time:.3f}s ({self.beta_v2_ops:>8.0f} ops/sec)")


def run_benchmark_subprocess(test_module: str, db_path: str) -> Dict[str, Tuple[float, float]]:
    """Run benchmark in a separate process to avoid import conflicts.
    
    Args:
        test_module: Name of the test module (e.g., 'test_benchmark_original')
        db_path: Path to the database file
        
    Returns:
        Dictionary mapping test name to (elapsed_time, ops_per_sec)
    """
    test_file = BENCHMARK_DIR / f"{test_module}.py"
    
    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        return {
            'basic_write': (0, 0),
            'basic_read': (0, 0),
            'bulk_insert': (0, 0),
            'mixed_ops': (0, 0)
        }
    
    # Run the test module in a true subprocess to avoid import conflicts
    try:
        # Create a Python script that will run the benchmark and output JSON results
        script = f"""
import sys
import json

# Run the benchmark
sys.path.insert(0, '{BENCHMARK_DIR}')
from {test_module} import run_benchmarks

results = run_benchmarks('{db_path}')
# Convert to JSON-serializable format
json_results = {{k: list(v) for k, v in results.items()}}
print("BENCHMARK_RESULTS_START")
print(json.dumps(json_results))
print("BENCHMARK_RESULTS_END")
"""
        
        # Run in subprocess with clean environment
        result = subprocess.run(
            [sys.executable, '-c', script],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
            cwd=str(BENCHMARK_DIR)
        )
        
        if result.returncode != 0:
            print(f"❌ Subprocess failed with code {result.returncode}")
            print(f"stderr: {result.stderr}")
            print(f"stdout: {result.stdout}")
            return {
                'basic_write': (0, 0),
                'basic_read': (0, 0),
                'bulk_insert': (0, 0),
                'mixed_ops': (0, 0)
            }
        
        # Parse JSON results from stdout
        output = result.stdout
        
        # Extract JSON between markers
        start_marker = "BENCHMARK_RESULTS_START"
        end_marker = "BENCHMARK_RESULTS_END"
        
        if start_marker in output and end_marker in output:
            start_idx = output.index(start_marker) + len(start_marker)
            end_idx = output.index(end_marker)
            json_str = output[start_idx:end_idx].strip()
            json_results = json.loads(json_str)
            
            # Convert back to tuple format
            results = {k: tuple(v) for k, v in json_results.items()}
            return results
        else:
            print(f"⚠️ Could not find result markers in output")
            print(f"stdout: {output}")
            return {
                'basic_write': (0, 0),
                'basic_read': (0, 0),
                'bulk_insert': (0, 0),
                'mixed_ops': (0, 0)
            }
        
    except Exception as e:
        print(f"❌ Error running {test_module}: {e}")
        import traceback
        traceback.print_exc()
        return {
            'basic_write': (0, 0),
            'basic_read': (0, 0),
            'bulk_insert': (0, 0),
            'mixed_ops': (0, 0)
        }


def generate_comparison_graphs(original_results: Dict[str, Tuple[float, float]], 
                               v2_results: Dict[str, Tuple[float, float]], 
                               beta_v2_results: Dict[str, Tuple[float, float]],
                               output_dir: Path = None):
    """Generate comparison graphs for all versions."""
    if not MATPLOTLIB_AVAILABLE:
        print("\n⚠ Matplotlib not available. Skipping graph generation.")
        return
    
    if output_dir is None:
        output_dir = BENCHMARK_DIR / "results" / "graphs"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Setup Japanese fonts
    try:
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Noto Sans CJK JP']
    except Exception:
        pass
    
    # Prepare data
    test_names = ['basic_write', 'basic_read', 'bulk_insert', 'mixed_ops']
    short_labels = ['Write', 'Read', 'Bulk\nInsert', 'Mixed\nOps']
    
    # Extract OPS data
    original_ops = [original_results[name][1] for name in test_names]
    v2_ops = [v2_results[name][1] for name in test_names]
    beta_v2_ops = [beta_v2_results[name][1] for name in test_names]
    
    # Graph 1: Bar chart comparison
    fig, ax = plt.subplots(figsize=(12, 6))
    
    x = range(len(test_names))
    width = 0.25
    
    ax.bar([i - width for i in x], original_ops, width, label='Original版', alpha=0.8)
    ax.bar(x, v2_ops, width, label='dictsqlite_v2版', alpha=0.8)
    ax.bar([i + width for i in x], beta_v2_ops, width, label='Beta v2版', alpha=0.8)
    
    ax.set_xlabel('テスト種類 (Test Type)', fontsize=12)
    ax.set_ylabel('操作数/秒 (Operations per Second)', fontsize=12)
    ax.set_title('DictSQLite バージョン比較 / Version Comparison', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(short_labels, fontsize=10)
    ax.legend(fontsize=11)
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    graph_path = output_dir / "version_comparison_bar.png"
    plt.savefig(graph_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  ✓ 棒グラフ保存 (Saved bar chart): {graph_path}")
    
    print(f"\n✅ グラフ保存完了 (Graphs saved to): {output_dir}")


def save_csv_results(original_results: Dict[str, Tuple[float, float]], 
                     v2_results: Dict[str, Tuple[float, float]], 
                     beta_v2_results: Dict[str, Tuple[float, float]],
                     test_labels: List[str],
                     output_dir: Path = None):
    """Save benchmark results to CSV file."""
    if output_dir is None:
        output_dir = BENCHMARK_DIR / "results"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save main CSV file
    csv_path = output_dir / "benchmark.csv"
    test_names = ['basic_write', 'basic_read', 'bulk_insert', 'mixed_ops']
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Version', 'Test', 'OPS', 'Time (s)', 'Result'])
        
        for test_name, label in zip(test_names, test_labels):
            # Original
            elapsed, ops = original_results[test_name]
            writer.writerow(['original', label, f'{ops:.2f}', f'{elapsed:.4f}', '成功' if ops > 0 else 'スキップ'])
            
            # dictsqlite_v2
            elapsed, ops = v2_results[test_name]
            writer.writerow(['dictsqlite_v2', label, f'{ops:.2f}', f'{elapsed:.4f}', '成功' if ops > 0 else 'スキップ'])
            
            # fastest beta v2
            elapsed, ops = beta_v2_results[test_name]
            writer.writerow(['fastest_beta_v2', label, f'{ops:.2f}', f'{elapsed:.4f}', '成功' if ops > 0 else 'スキップ'])
    
    print(f"\n✅ CSV保存完了 (CSV saved to): {csv_path}")
    return csv_path


def generate_summary_markdown(original_results: Dict[str, Tuple[float, float]], 
                               v2_results: Dict[str, Tuple[float, float]], 
                               beta_v2_results: Dict[str, Tuple[float, float]],
                               test_labels: List[str],
                               output_dir: Path = None):
    """Generate summary markdown file."""
    if output_dir is None:
        output_dir = BENCHMARK_DIR / "results"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    summary_path = output_dir / "BENCHMARK_SUMMARY.md"
    test_names = ['basic_write', 'basic_read', 'bulk_insert', 'mixed_ops']
    
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write("# DictSQLite 包括的ベンチマーク結果\n\n")
        f.write(f"**実行日時:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## 概要\n\n")
        f.write("3つのバージョンを徹底比較:\n")
        f.write("- **DictSQLite (Original版)**: sqlite3ベース\n")
        f.write("- **dictsqlite_v2**: Rust拡張版 (v2.0.6)\n")
        f.write("- **dictsqlite-fastest Beta v2**: APSWベース、高速化\n\n")
        
        f.write("## ベンチマーク結果\n\n")
        f.write("| テスト | Original (ops/sec) | dictsqlite_v2 (ops/sec) | fastest Beta v2 (ops/sec) | 最速 |\n")
        f.write("|--------|-------------------|------------------------|---------------------------|------|\n")
        
        for test_name, label in zip(test_names, test_labels):
            orig_ops = original_results[test_name][1]
            v2_ops = v2_results[test_name][1]
            beta_ops = beta_v2_results[test_name][1]
            
            # Determine fastest
            max_ops = max(orig_ops, v2_ops, beta_ops)
            if max_ops == 0:
                fastest = "N/A"
            elif max_ops == orig_ops:
                fastest = "**Original**"
            elif max_ops == v2_ops:
                fastest = "**dictsqlite_v2**"
            else:
                fastest = "**fastest Beta v2**"
            
            f.write(f"| {label} | {orig_ops:,.0f} | {v2_ops:,.0f} | {beta_ops:,.0f} | {fastest} |\n")
        
        # Overall statistics
        f.write("\n## 総合パフォーマンス\n\n")
        
        sync_test_names = ['basic_write', 'basic_read', 'bulk_insert', 'mixed_ops']
        original_avg = sum(original_results[name][1] for name in sync_test_names if original_results[name][1] > 0) / len([1 for name in sync_test_names if original_results[name][1] > 0]) if any(original_results[name][1] > 0 for name in sync_test_names) else 0
        v2_avg = sum(v2_results[name][1] for name in sync_test_names if v2_results[name][1] > 0) / len([1 for name in sync_test_names if v2_results[name][1] > 0]) if any(v2_results[name][1] > 0 for name in sync_test_names) else 0
        beta_v2_avg = sum(beta_v2_results[name][1] for name in sync_test_names if beta_v2_results[name][1] > 0) / len([1 for name in sync_test_names if beta_v2_results[name][1] > 0]) if any(beta_v2_results[name][1] > 0 for name in sync_test_names) else 0
        
        f.write("**平均スループット** (ops/sec):\n\n")
        if original_avg > 0:
            f.write(f"- Original版: {original_avg:,.0f}\n")
        if v2_avg > 0:
            f.write(f"- dictsqlite_v2版: {v2_avg:,.0f}\n")
        if beta_v2_avg > 0:
            f.write(f"- fastest Beta v2版: {beta_v2_avg:,.0f}\n")
        
        # Determine winner
        versions = []
        if original_avg > 0:
            versions.append(('Original版', original_avg))
        if v2_avg > 0:
            versions.append(('dictsqlite_v2版', v2_avg))
        if beta_v2_avg > 0:
            versions.append(('fastest Beta v2版', beta_v2_avg))
        
        if versions:
            sorted_versions = sorted(versions, key=lambda x: x[1], reverse=True)
            winner = sorted_versions[0]
            
            f.write(f"\n## 🏆 総括\n\n")
            f.write(f"**最速: {winner[0]}** ({winner[1]:,.0f} ops/sec)\n\n")
            f.write("### パフォーマンスランキング\n\n")
            for i, (name, ops) in enumerate(sorted_versions, 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
                f.write(f"{medal} {i}位. {name}: {ops:,.0f} ops/sec\n")
    
    print(f"✅ サマリー保存完了 (Summary saved to): {summary_path}")
    return summary_path



def main():
    """Main benchmark execution."""
    print("=" * 80)
    print("DictSQLite 総合ベンチマーク / Comprehensive Benchmark")
    print("Original版 vs dictsqlite_v2版 vs Beta v2版")
    print("=" * 80)
    
    # Version mapping table
    print("\n" + "=" * 80)
    print("📋 バージョンマッピング (Version Mapping)")
    print("=" * 80)
    print("\n以下の3つのバージョンを比較します:")
    print("\n  1️⃣  Original版 (DictSQLite Original)")
    print("     📁 ソースコード: dictsqlite/")
    print("     🔧 実装: 標準sqlite3ベース")
    print("\n  2️⃣  dictsqlite_v2版 (dictsqlite_v2)")
    print("     📁 ソースコード: dictsqlite_v2/dictsqlite/")
    print("     🔧 実装: Rust拡張（バージョン 2.0.6）")
    print("\n  3️⃣  Beta v2版 (dictsqlite-fastest Beta v2)")
    print("     📁 ソースコード: others/beta-versions/dictsqlite-fastest/beta/")
    print("     🔧 実装: APSWベース（非同期高性能版）")
    print("\n" + "=" * 80)
    
    # Create temp files for each version
    with tempfile.NamedTemporaryFile(delete=False, suffix='_original.db') as tmp:
        original_path = tmp.name
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='_v2.db') as tmp:
        v2_path = tmp.name
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='_beta_v2.db') as tmp:
        beta_v2_path = tmp.name
    
    test_names = ['basic_write', 'basic_read', 'bulk_insert', 'mixed_ops']
    test_labels = [
        'Basic Write (300 items)',
        'Basic Read (300 items)',
        'Bulk Insert (500 items)',
        'Mixed Operations (400 items)'
    ]
    
    try:
        # Run benchmarks using separate test modules
        print("\n🚀 Running benchmarks using optimized separate test modules...")
        
        original_results = run_benchmark_subprocess('test_benchmark_original', original_path)
        v2_results = run_benchmark_subprocess('test_benchmark_dictsqlite_v2', v2_path)
        beta_v2_results = run_benchmark_subprocess('test_benchmark_fastest', beta_v2_path)
        
        # Create result objects
        results = []
        for test_name, label in zip(test_names, test_labels):
            result = BenchmarkResult(label)
            result.set_original(*original_results[test_name])
            result.set_v2(*v2_results[test_name])
            result.set_beta_v2(*beta_v2_results[test_name])
            results.append(result)
        
        # Print comparison summary
        print(f"\n{'='*80}")
        print("📊 パフォーマンス比較結果 (Performance Comparison Summary)")
        print(f"{'='*80}")
        
        for result in results:
            result.print_comparison()
        
        # Overall statistics
        print(f"\n{'='*80}")
        print("📈 総合パフォーマンス (Overall Performance)")
        print(f"{'='*80}")
        
        # Calculate averages
        sync_test_names = ['basic_write', 'basic_read', 'bulk_insert', 'mixed_ops']
        
        original_avg = sum(original_results[name][1] for name in sync_test_names if original_results[name][1] > 0) / len([1 for name in sync_test_names if original_results[name][1] > 0]) if any(original_results[name][1] > 0 for name in sync_test_names) else 0
        v2_avg = sum(v2_results[name][1] for name in sync_test_names if v2_results[name][1] > 0) / len([1 for name in sync_test_names if v2_results[name][1] > 0]) if any(v2_results[name][1] > 0 for name in sync_test_names) else 0
        beta_v2_avg = sum(beta_v2_results[name][1] for name in sync_test_names if beta_v2_results[name][1] > 0) / len([1 for name in sync_test_names if beta_v2_results[name][1] > 0]) if any(beta_v2_results[name][1] > 0 for name in sync_test_names) else 0
        
        print(f"\n平均スループット (Average throughput, ops/sec):")
        if original_avg > 0:
            print(f"  Original版:        {original_avg:>10.0f} ops/sec")
        if v2_avg > 0:
            baseline_avg = original_avg if original_avg > 0 else v2_avg
            if baseline_avg > 0 and baseline_avg != v2_avg:
                speedup = v2_avg / baseline_avg
                print(f"  dictsqlite_v2版:   {v2_avg:>10.0f} ops/sec ({speedup:>5.2f}x 🚀)")
            else:
                print(f"  dictsqlite_v2版:   {v2_avg:>10.0f} ops/sec")
        if beta_v2_avg > 0:
            baseline_avg = original_avg if original_avg > 0 else (v2_avg if v2_avg > 0 else beta_v2_avg)
            if baseline_avg > 0:
                speedup = beta_v2_avg / baseline_avg
                print(f"  Beta v2版:         {beta_v2_avg:>10.0f} ops/sec ({speedup:>5.2f}x 🚀)")
            else:
                print(f"  Beta v2版:         {beta_v2_avg:>10.0f} ops/sec")
        
        # Determine winner
        print(f"\n{'='*80}")
        print("🏆 総括 (Summary)")
        print(f"{'='*80}")
        
        versions = []
        if original_avg > 0:
            versions.append(('Original版', original_avg))
        if v2_avg > 0:
            versions.append(('dictsqlite_v2版', v2_avg))
        if beta_v2_avg > 0:
            versions.append(('Beta v2版', beta_v2_avg))
        
        if not versions:
            print("\n⚠ 比較可能なベンチマーク結果がありません (No successful benchmarks to compare)")
        else:
            sorted_versions = sorted(versions, key=lambda x: x[1], reverse=True)
            winner = sorted_versions[0]
            
            print(f"\n🥇 最速: {winner[0]} ({winner[1]:.0f} ops/sec)")
            print(f"\n📊 パフォーマンスランキング (Performance ranking):")
            baseline_for_comparison = sorted_versions[-1][1]
            for i, (name, ops) in enumerate(sorted_versions, 1):
                vs_baseline = ((ops / baseline_for_comparison) - 1) * 100
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
                print(f"  {medal} {i}位. {name}: {ops:>10.0f} ops/sec (ベースライン比 {vs_baseline:+.1f}%)")
        
        # Generate comparison graphs
        print(f"\n{'='*80}")
        print("📈 比較グラフ生成中... (Generating comparison graphs...)")
        print(f"{'='*80}")
        try:
            generate_comparison_graphs(
                original_results, 
                v2_results,
                beta_v2_results
            )
        except Exception as e:
            print(f"\n⚠ Error generating graphs: {e}")
            import traceback
            traceback.print_exc()
        
        # Save CSV results
        print(f"\n{'='*80}")
        print("💾 CSV結果保存中... (Saving CSV results...)")
        print(f"{'='*80}")
        try:
            save_csv_results(
                original_results,
                v2_results,
                beta_v2_results,
                test_labels
            )
        except Exception as e:
            print(f"\n⚠ Error saving CSV: {e}")
            import traceback
            traceback.print_exc()
        
        # Generate summary markdown
        print(f"\n{'='*80}")
        print("📝 サマリー生成中... (Generating summary...)")
        print(f"{'='*80}")
        try:
            generate_summary_markdown(
                original_results,
                v2_results,
                beta_v2_results,
                test_labels
            )
        except Exception as e:
            print(f"\n⚠ Error generating summary: {e}")
            import traceback
            traceback.print_exc()
        
        print(f"\n{'='*80}")
        print("✅ ベンチマーク完了！ (Benchmark completed successfully!)")
        print(f"{'='*80}")
        
    finally:
        # Cleanup
        for path in [original_path, v2_path, beta_v2_path]:
            if os.path.exists(path):
                os.unlink(path)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
