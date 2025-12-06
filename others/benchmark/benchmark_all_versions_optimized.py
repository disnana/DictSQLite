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
from pathlib import Path
from typing import Dict, Tuple

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
    
    # Run the test module as a subprocess
    try:
        # Import the module and run benchmarks
        import importlib.util
        spec = importlib.util.spec_from_file_location(test_module, test_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Run the benchmarks
        results = module.run_benchmarks(db_path)
        return results
        
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
