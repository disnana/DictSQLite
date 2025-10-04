#!/usr/bin/env python3
"""
DictSQLite-Fastest Benchmark Tool

This script provides comprehensive performance benchmarks comparing
DictSQLite and DictSQLite-Fastest across various operations and scenarios.
"""

import time
import asyncio
import tempfile
import os
import sys
import statistics
import csv
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add both modules to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.dirname(__file__))

from dictsqlite.main import DictSQLite
from dictsqlite_fastest.main import DictSQLiteFastest, AsyncDictSQLiteFastest


def measure_operation(func, iterations=3):
    """Execute function multiple times and return average time"""
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        result = func()
        end = time.perf_counter()
        times.append(end - start)
    return statistics.mean(times), result


class Benchmark:
    """Main benchmark class"""
    
    def __init__(self, output_file=None, output_dir=None):
        self.results = []
        self.output_file = output_file
        self.output_dir = Path(output_dir) if output_dir else Path("benchmark_results")
        self.output_dir.mkdir(exist_ok=True)
        
        # CSV output file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.csv_file = self.output_dir / f"benchmark_{timestamp}.csv"
    
    def log(self, message):
        """Log message to console and optionally to file"""
        print(message)
        if self.output_file:
            with open(self.output_file, 'a') as f:
                f.write(message + '\n')
    
    def run_sync_benchmark(self, name, original_func, fastest_func, iterations=3, operation_count=None):
        """Run a synchronous benchmark comparison with OPS metrics"""
        self.log(f"\n{'='*60}")
        self.log(f"BENCHMARK: {name}")
        self.log(f"{'='*60}")
        
        # Extract operation count from name if not provided
        if operation_count is None:
            import re
            match = re.search(r'\((\d+)\s+items?\)', name)
            operation_count = int(match.group(1)) if match else 1
        
        # Run original
        try:
            time_orig, _ = measure_operation(original_func, iterations)
            ops_per_sec_orig = operation_count / time_orig if time_orig > 0 else 0
            self.log(f"DictSQLite:        {time_orig:.4f}s ({ops_per_sec_orig:,.0f} ops/sec)")
        except Exception as e:
            self.log(f"DictSQLite:        ERROR - {e}")
            time_orig = float('inf')
            ops_per_sec_orig = 0
        
        # Run fastest
        try:
            time_fast, _ = measure_operation(fastest_func, iterations)
            ops_per_sec_fast = operation_count / time_fast if time_fast > 0 else 0
            self.log(f"DictSQLite-Fastest: {time_fast:.4f}s ({ops_per_sec_fast:,.0f} ops/sec)")
        except Exception as e:
            self.log(f"DictSQLite-Fastest: ERROR - {e}")
            time_fast = float('inf')
            ops_per_sec_fast = 0
        
        # Calculate speedup
        if time_fast != float('inf') and time_orig != float('inf') and time_fast > 0:
            speedup = time_orig / time_fast
            ops_speedup = ops_per_sec_fast / ops_per_sec_orig if ops_per_sec_orig > 0 else 0
            self.log(f"Speedup:           {speedup:.2f}x")
            self.log(f"OPS Improvement:   {ops_speedup:.2f}x ({ops_per_sec_fast - ops_per_sec_orig:+,.0f} ops/sec)")
            
            if speedup > 1:
                self.log(f"✓ DictSQLite-Fastest is {speedup:.1f}x FASTER")
            else:
                self.log(f"⚠ DictSQLite-Fastest is {1/speedup:.1f}x SLOWER")
        else:
            speedup = 1.0
            ops_speedup = 1.0
            self.log("Unable to calculate speedup")
        
        self.results.append({
            'name': name,
            'original_time': time_orig,
            'fastest_time': time_fast,
            'speedup': speedup,
            'operation_count': operation_count,
            'ops_original': ops_per_sec_orig,
            'ops_fastest': ops_per_sec_fast,
            'ops_speedup': ops_speedup
        })
    
    async def run_async_benchmark(self, name, async_func, iterations=3, operation_count=None):
        """Run an async benchmark with OPS metrics"""
        self.log(f"\n{'='*60}")
        self.log(f"ASYNC BENCHMARK: {name}")
        self.log(f"{'='*60}")
        
        # Extract operation count from name if not provided
        if operation_count is None:
            import re
            match = re.search(r'(\d+)', name)
            operation_count = int(match.group(1)) if match else 10  # Default for async operations
        
        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            await async_func()
            end = time.perf_counter()
            times.append(end - start)
        
        avg_time = statistics.mean(times)
        ops_per_sec = operation_count / avg_time if avg_time > 0 else 0
        self.log(f"Average time: {avg_time:.4f}s ({ops_per_sec:,.0f} ops/sec)")
        self.log(f"Operations: {operation_count:,} total, {operation_count/iterations:.1f} per iteration")
    
    def print_summary(self):
        """Print overall benchmark summary with OPS metrics"""
        self.log(f"\n{'='*80}")
        self.log("BENCHMARK SUMMARY")
        self.log(f"{'='*80}")
        
        if not self.results:
            self.log("No benchmark results available")
            return
        
        # Calculate overall statistics
        speedups = [r['speedup'] for r in self.results if r['speedup'] != float('inf')]
        if speedups:
            avg_speedup = statistics.mean(speedups)
            max_speedup = max(speedups)
            min_speedup = min(speedups)
            
            self.log(f"Average Speedup: {avg_speedup:.2f}x")
            self.log(f"Maximum Speedup: {max_speedup:.2f}x")
            self.log(f"Minimum Speedup: {min_speedup:.2f}x")
            
            faster_count = sum(1 for s in speedups if s > 1.0)
            total_count = len(speedups)
            self.log(f"Tests where Fastest is faster: {faster_count}/{total_count} ({100*faster_count/total_count:.1f}%)")
            
            # OPS Summary
            ops_improvements = [r.get('ops_speedup', 1.0) for r in self.results if 'ops_speedup' in r and r['ops_speedup'] != float('inf')]
            if ops_improvements:
                avg_ops_improvement = statistics.mean(ops_improvements)
                max_ops_improvement = max(ops_improvements)
                self.log(f"\nOPS Performance:")
                self.log(f"Average OPS Improvement: {avg_ops_improvement:.2f}x")
                self.log(f"Maximum OPS Improvement: {max_ops_improvement:.2f}x")
        
        # Enhanced table with OPS metrics
        self.log(f"\n{'Test Name':<30} {'Original':<12} {'Fastest':<12} {'Speedup':<10} {'Original OPS':<12} {'Fastest OPS':<12}")
        self.log("-" * 110)
        
        for result in self.results:
            orig = f"{result['original_time']:.4f}s" if result['original_time'] != float('inf') else "ERROR"
            fast = f"{result['fastest_time']:.4f}s" if result['fastest_time'] != float('inf') else "ERROR"
            speedup = f"{result['speedup']:.2f}x" if result['speedup'] != float('inf') else "N/A"
            
            # OPS metrics
            ops_orig = f"{result.get('ops_original', 0):,.0f}" if 'ops_original' in result else "N/A"
            ops_fast = f"{result.get('ops_fastest', 0):,.0f}" if 'ops_fastest' in result else "N/A"
            
            self.log(f"{result['name']:<30} {orig:<12} {fast:<12} {speedup:<10} {ops_orig:<12} {ops_fast:<12}")
        
        # Add OPS comparison section
        self.log(f"\n{'='*80}")
        self.log("OPERATIONS PER SECOND (OPS) ANALYSIS")
        self.log(f"{'='*80}")
        
        for result in self.results:
            if 'ops_original' in result and 'ops_fastest' in result:
                ops_diff = result['ops_fastest'] - result['ops_original']
                ops_speedup = result.get('ops_speedup', 1.0)
                self.log(f"{result['name']:<30}: {ops_diff:+11,.0f} ops/sec improvement ({ops_speedup:.2f}x)")
    
    def save_csv(self):
        """Save results to CSV file for graph generation"""
        with open(self.csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Test', 'Version', 'Time(s)', 'OPS', 'Operations'])
            
            for result in self.results:
                # Original version
                if result['original_time'] != float('inf'):
                    writer.writerow([
                        result['name'],
                        'original',
                        f"{result['original_time']:.4f}",
                        f"{result['ops_original']:.0f}",
                        result['operation_count']
                    ])
                
                # Fastest version
                if result['fastest_time'] != float('inf'):
                    writer.writerow([
                        result['name'],
                        'fastest',
                        f"{result['fastest_time']:.4f}",
                        f"{result['ops_fastest']:.0f}",
                        result['operation_count']
                    ])
        
        self.log(f"\n✓ CSV saved: {self.csv_file}")
    
    def generate_graphs(self):
        """Generate performance graphs"""
        try:
            import matplotlib.pyplot as plt
            import numpy as np
            
            graph_dir = self.output_dir / "graphs"
            graph_dir.mkdir(exist_ok=True)
            
            # 1. OPS Comparison Graph
            fig, ax = plt.subplots(figsize=(12, 6))
            
            test_names = [r['name'] for r in self.results]
            x = np.arange(len(test_names))
            width = 0.35
            
            original_ops = [r['ops_original'] for r in self.results]
            fastest_ops = [r['ops_fastest'] for r in self.results]
            
            ax.bar(x - width/2, original_ops, width, label='Original', color='#FF6B6B')
            ax.bar(x + width/2, fastest_ops, width, label='Fastest', color='#4ECDC4')
            
            ax.set_xlabel('Test', fontweight='bold')
            ax.set_ylabel('Operations Per Second (OPS)', fontweight='bold')
            ax.set_title('DictSQLite vs DictSQLite-Fastest: OPS Comparison', fontweight='bold', fontsize=14)
            ax.set_xticks(x)
            ax.set_xticklabels(test_names, rotation=45, ha='right')
            ax.legend()
            ax.grid(axis='y', alpha=0.3)
            
            plt.tight_layout()
            ops_graph = graph_dir / "ops_comparison.png"
            plt.savefig(ops_graph, dpi=150, bbox_inches='tight')
            plt.close()
            
            self.log(f"✓ Graph saved: {ops_graph}")
            
            # 2. Speedup Graph
            fig, ax = plt.subplots(figsize=(12, 6))
            
            speedups = [r['speedup'] for r in self.results]
            colors = ['#4ECDC4' if s > 1 else '#FF6B6B' for s in speedups]
            
            ax.barh(test_names, speedups, color=colors)
            ax.axvline(x=1.0, color='gray', linestyle='--', linewidth=2, label='Baseline (1x)')
            ax.set_xlabel('Speedup Factor', fontweight='bold')
            ax.set_ylabel('Test', fontweight='bold')
            ax.set_title('DictSQLite-Fastest Performance Improvement', fontweight='bold', fontsize=14)
            ax.legend()
            ax.grid(axis='x', alpha=0.3)
            
            # Add value labels
            for i, (test, speedup) in enumerate(zip(test_names, speedups)):
                ax.text(speedup + 0.1, i, f'{speedup:.2f}x', va='center', fontweight='bold')
            
            plt.tight_layout()
            speedup_graph = graph_dir / "speedup_comparison.png"
            plt.savefig(speedup_graph, dpi=150, bbox_inches='tight')
            plt.close()
            
            self.log(f"✓ Graph saved: {speedup_graph}")
            
            return graph_dir
            
        except ImportError:
            self.log("\n⚠ Graph generation skipped: matplotlib not installed")
            self.log("  To generate graphs, install: pip install matplotlib")
            return None
        except Exception as e:
            self.log(f"\n⚠ Graph generation error: {e}")
            import traceback
            traceback.print_exc()
            return None


def main():
    """Run all benchmarks"""
    
    benchmark = Benchmark()
    benchmark.log("DictSQLite-Fastest Performance Benchmark")
    benchmark.log(f"Starting at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test configurations
    test_sizes = [100, 500, 1000]
    
    for size in test_sizes:
        # Create temporary database files
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp_orig:
            orig_path = tmp_orig.name
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp_fast:
            fast_path = tmp_fast.name
        
        try:
            # Basic operations
            def bulk_insert_original():
                with DictSQLite(orig_path, journal_mode='WAL') as db:
                    for i in range(size):
                        db[f"key_{i}"] = f"value_{i}"
            
            def bulk_insert_fastest():
                with DictSQLiteFastest(fast_path, journal_mode='WAL') as db:
                    for i in range(size):
                        db[f"key_{i}"] = f"value_{i}"
            
            benchmark.run_sync_benchmark(
                f"Bulk Insert ({size} items)",
                bulk_insert_original,
                bulk_insert_fastest
            )
            
            # Setup data for read tests
            with DictSQLite(orig_path, journal_mode='WAL') as db:
                for i in range(size):
                    db[f"key_{i}"] = f"value_{i}"
            
            with DictSQLiteFastest(fast_path, journal_mode='WAL') as db:
                for i in range(size):
                    db[f"key_{i}"] = f"value_{i}"
            
            def bulk_read_original():
                with DictSQLite(orig_path, journal_mode='WAL') as db:
                    return [db[f"key_{i}"] for i in range(size)]
            
            def bulk_read_fastest():
                with DictSQLiteFastest(fast_path, journal_mode='WAL') as db:
                    return [db[f"key_{i}"] for i in range(size)]
            
            benchmark.run_sync_benchmark(
                f"Bulk Read ({size} items)",
                bulk_read_original,
                bulk_read_fastest
            )
            
            # Complex data structures
            def complex_data_original():
                with DictSQLite(orig_path, journal_mode='WAL') as db:
                    for i in range(size // 10):  # Reduce size for complex operations
                        db[f"complex_{i}"] = {
                            "id": i,
                            "data": list(range(i, i+10)),
                            "metadata": {"created": time.time(), "type": "test"}
                        }
            
            def complex_data_fastest():
                with DictSQLiteFastest(fast_path, journal_mode='WAL') as db:
                    for i in range(size // 10):
                        db[f"complex_{i}"] = {
                            "id": i,
                            "data": list(range(i, i+10)),
                            "metadata": {"created": time.time(), "type": "test"}
                        }
            
            benchmark.run_sync_benchmark(
                f"Complex Data ({size//10} items)",
                complex_data_original,
                complex_data_fastest
            )
            
        finally:
            # Cleanup
            for path in [orig_path, fast_path]:
                if os.path.exists(path):
                    os.unlink(path)
                # Also clean up WAL files
                for suffix in ['-wal', '-shm']:
                    wal_path = path + suffix
                    if os.path.exists(wal_path):
                        os.unlink(wal_path)
    
    # Async benchmarks
    async def run_async_benchmarks():
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
            db_path = tmp.name
        
        try:
            async def async_operations():
                db = AsyncDictSQLiteFastest(db_path)
                try:
                    # Concurrent writes
                    write_tasks = [db.aset(f"async_key_{i}", f"async_value_{i}") for i in range(200)]
                    await asyncio.gather(*write_tasks)
                    
                    # Concurrent reads
                    read_tasks = [db.aget(f"async_key_{i}") for i in range(200)]
                    values = await asyncio.gather(*read_tasks)
                    return len(values)
                finally:
                    await db.aclose()
            
            await benchmark.run_async_benchmark("Async Concurrent Operations", async_operations)
            
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)
    
    # Run async benchmarks
    asyncio.run(run_async_benchmarks())
    
    # Print final summary
    benchmark.print_summary()
    
    # Save CSV and generate graphs
    benchmark.save_csv()
    graph_dir = benchmark.generate_graphs()
    
    # Final output summary
    print("\n" + "="*80)
    print("BENCHMARK COMPLETE")
    print("="*80)
    print(f"\nOutput Directory: {benchmark.output_dir}")
    print(f"  - CSV: {benchmark.csv_file.name}")
    if graph_dir:
        graph_files = list(graph_dir.glob('*.png'))
        print(f"  - Graphs: {len(graph_files)} files in {graph_dir.name}/")


if __name__ == "__main__":
    main()