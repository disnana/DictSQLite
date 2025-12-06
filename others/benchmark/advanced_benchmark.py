#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Advanced benchmark with memory profiling and additional scenarios.

追加ベンチマーク機能:
- メモリ使用量の詳細分析
- より多くのベンチマークシナリオ
- より詳細な並行処理テスト
"""

import asyncio
import gc
import os
import sys
import tempfile
import time
import traceback
import tracemalloc
from pathlib import Path
from typing import Dict, Tuple, Any, List
import json

# Add paths
REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))
V2_DIR = REPO_ROOT / 'dictsqlite_v2' / 'dictsqlite' / 'python'
sys.path.insert(0, str(V2_DIR))
BETA_V2_DIR = REPO_ROOT / 'others' / 'beta-versions' / 'dictsqlite-fastest' / 'beta'
sys.path.insert(0, str(BETA_V2_DIR))
BENCHMARK_DIR = REPO_ROOT / 'others' / 'benchmark'
sys.path.insert(0, str(BENCHMARK_DIR))

# Import versions
try:
    from dictsqlite.main import DictSQLite
    ORIGINAL_AVAILABLE = True
except ImportError as e:
    print(f"⚠ DictSQLite (Original) not available: {e}")
    DictSQLite = None
    ORIGINAL_AVAILABLE = False

try:
    from dictsqlite import DictSQLite as DictSQLiteV2_Sync
    from dictsqlite import AsyncDictSQLite as DictSQLiteV2_Async
    V2_AVAILABLE = True
except ImportError as e:
    print(f"⚠ dictsqlite_v2 not available: {e}")
    DictSQLiteV2_Sync = None
    DictSQLiteV2_Async = None
    V2_AVAILABLE = False

try:
    from dictsqlite_fastest_beta_v2 import AsyncDictSQLiteFastestBeta as AsyncBetaV2
    BETA_V2_AVAILABLE = True
except ImportError as e:
    print(f"⚠ dictsqlite-fastest beta v2 not available: {e}")
    AsyncBetaV2 = None
    BETA_V2_AVAILABLE = False


class MemoryProfiler:
    """メモリ使用量をプロファイリングするクラス"""
    
    def __init__(self):
        self.snapshots = []
        self.enabled = False
    
    def start(self):
        """メモリプロファイリング開始"""
        gc.collect()
        tracemalloc.start()
        self.enabled = True
        self.snapshots = []
    
    def snapshot(self, label: str):
        """現在のメモリ状態のスナップショット取得"""
        if not self.enabled:
            return
        
        current, peak = tracemalloc.get_traced_memory()
        self.snapshots.append({
            'label': label,
            'current_mb': current / 1024 / 1024,
            'peak_mb': peak / 1024 / 1024,
            'timestamp': time.time()
        })
    
    def stop(self) -> Dict[str, Any]:
        """メモリプロファイリング停止して結果を返す"""
        if not self.enabled:
            return {}
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        self.enabled = False
        
        return {
            'final_current_mb': current / 1024 / 1024,
            'final_peak_mb': peak / 1024 / 1024,
            'snapshots': self.snapshots
        }
    
    def print_summary(self, results: Dict[str, Any]):
        """メモリプロファイリング結果の表示"""
        if not results:
            return
        
        print(f"\n{'='*80}")
        print("💾 メモリ使用量分析 (Memory Usage Analysis)")
        print(f"{'='*80}")
        print(f"\n最終メモリ使用量:")
        print(f"  現在: {results['final_current_mb']:.2f} MB")
        print(f"  ピーク: {results['final_peak_mb']:.2f} MB")
        
        if results['snapshots']:
            print(f"\nスナップショット履歴:")
            for snap in results['snapshots']:
                print(f"  [{snap['label']}]")
                print(f"    現在: {snap['current_mb']:.2f} MB")
                print(f"    ピーク: {snap['peak_mb']:.2f} MB")


class AdvancedBenchmarkResult:
    """拡張ベンチマーク結果を保存するクラス"""
    
    def __init__(self, name: str):
        self.name = name
        self.results = {}  # version_name -> {'time': float, 'ops': float, 'memory': dict}
    
    def add_result(self, version: str, elapsed: float, ops_per_sec: float, memory_info: Dict = None):
        """結果を追加"""
        self.results[version] = {
            'time': elapsed,
            'ops': ops_per_sec,
            'memory': memory_info or {}
        }
    
    def print_comparison(self):
        """比較結果を表示"""
        print(f"\n📊 {self.name}:")
        
        # Find baseline (slowest)
        baseline_ops = min(r['ops'] for r in self.results.values() if r['ops'] > 0) if self.results else 0
        
        for version, data in self.results.items():
            if data['ops'] > 0:
                speedup = data['ops'] / baseline_ops if baseline_ops > 0 else 1.0
                mem_str = ""
                if data['memory']:
                    mem_str = f" (メモリ: {data['memory'].get('peak_mb', 0):.1f} MB)"
                
                emoji = "🚀" if speedup > 1.1 else ""
                print(f"  {version}: {data['time']:.3f}s ({data['ops']:>8.0f} ops/sec) - {speedup:>5.2f}x {emoji}{mem_str}")


# ===== 追加ベンチマークシナリオ =====

async def benchmark_large_dataset(db, count: int = 5000) -> Tuple[float, float, Dict]:
    """大規模データセットのベンチマーク"""
    profiler = MemoryProfiler()
    profiler.start()
    profiler.snapshot("開始")
    
    # データ作成
    data = {f'large_key_{i}': f'large_value_{i}' * 10 for i in range(count)}
    profiler.snapshot("データ作成完了")
    
    # 書き込み
    start = time.time()
    if hasattr(db, 'abulk_insert'):
        await db.abulk_insert(data)
    elif hasattr(db, 'aset'):
        for k, v in data.items():
            await db.aset(k, v)
    else:
        for k, v in data.items():
            db[k] = v
    
    elapsed = time.time() - start
    profiler.snapshot("書き込み完了")
    
    memory_results = profiler.stop()
    return elapsed, count / elapsed, memory_results


async def benchmark_concurrent_writes(db, count: int = 1000, concurrency: int = 10) -> Tuple[float, float, Dict]:
    """並行書き込みのベンチマーク"""
    profiler = MemoryProfiler()
    profiler.start()
    
    async def write_batch(start_idx: int, batch_size: int):
        for i in range(start_idx, start_idx + batch_size):
            if hasattr(db, 'aset'):
                await db.aset(f'concurrent_w_{i}', f'value_{i}')
            else:
                db[f'concurrent_w_{i}'] = f'value_{i}'
    
    batch_size = count // concurrency
    tasks = [write_batch(i * batch_size, batch_size) for i in range(concurrency)]
    
    profiler.snapshot("タスク準備完了")
    start = time.time()
    await asyncio.gather(*tasks)
    elapsed = time.time() - start
    profiler.snapshot("並行書き込み完了")
    
    memory_results = profiler.stop()
    return elapsed, count / elapsed, memory_results


async def benchmark_update_operations(db, count: int = 500) -> Tuple[float, float, Dict]:
    """更新操作のベンチマーク"""
    profiler = MemoryProfiler()
    profiler.start()
    
    # 初期データ作成
    for i in range(count):
        if hasattr(db, 'aset'):
            await db.aset(f'update_key_{i}', f'initial_value_{i}')
        else:
            db[f'update_key_{i}'] = f'initial_value_{i}'
    
    profiler.snapshot("初期データ作成完了")
    
    # 更新
    start = time.time()
    for i in range(count):
        if hasattr(db, 'aset'):
            await db.aset(f'update_key_{i}', f'updated_value_{i}')
        else:
            db[f'update_key_{i}'] = f'updated_value_{i}'
    
    elapsed = time.time() - start
    profiler.snapshot("更新完了")
    
    memory_results = profiler.stop()
    return elapsed, count / elapsed, memory_results


async def benchmark_deletion_operations(db, count: int = 500) -> Tuple[float, float, Dict]:
    """削除操作のベンチマーク"""
    profiler = MemoryProfiler()
    profiler.start()
    
    # 初期データ作成
    for i in range(count):
        if hasattr(db, 'aset'):
            await db.aset(f'delete_key_{i}', f'value_{i}')
        else:
            db[f'delete_key_{i}'] = f'value_{i}'
    
    profiler.snapshot("初期データ作成完了")
    
    # 削除
    start = time.time()
    for i in range(count):
        if hasattr(db, 'adelete'):
            await db.adelete(f'delete_key_{i}')
        elif hasattr(db, '__delitem__'):
            del db[f'delete_key_{i}']
    
    elapsed = time.time() - start
    profiler.snapshot("削除完了")
    
    memory_results = profiler.stop()
    return elapsed, count / elapsed, memory_results


async def benchmark_mixed_workload(db, count: int = 1000) -> Tuple[float, float, Dict]:
    """混合ワークロード（読み書き削除）のベンチマーク"""
    profiler = MemoryProfiler()
    profiler.start()
    
    start = time.time()
    for i in range(count):
        # 70% write, 20% read, 10% delete
        op = i % 10
        
        if op < 7:  # Write
            if hasattr(db, 'aset'):
                await db.aset(f'mixed_key_{i}', f'value_{i}')
            else:
                db[f'mixed_key_{i}'] = f'value_{i}'
        elif op < 9:  # Read
            try:
                if hasattr(db, 'aget'):
                    await db.aget(f'mixed_key_{i-1}')
                else:
                    _ = db.get(f'mixed_key_{i-1}', None)
            except:
                pass
        else:  # Delete
            try:
                if hasattr(db, 'adelete'):
                    await db.adelete(f'mixed_key_{i-2}')
                elif hasattr(db, '__delitem__'):
                    del db[f'mixed_key_{i-2}']
            except:
                pass
    
    elapsed = time.time() - start
    profiler.snapshot("混合ワークロード完了")
    
    memory_results = profiler.stop()
    return elapsed, count / elapsed, memory_results


async def run_advanced_benchmarks():
    """拡張ベンチマークの実行"""
    print("=" * 80)
    print("🔬 拡張ベンチマーク / Advanced Benchmarks")
    print("=" * 80)
    print("\n追加機能:")
    print("  • メモリ使用量の詳細分析")
    print("  • 大規模データセットのテスト")
    print("  • 並行書き込みのテスト")
    print("  • 更新・削除操作のベンチマーク")
    print("  • 混合ワークロードのテスト")
    print()
    
    results = []
    
    # テスト対象のバージョンを決定
    versions_to_test = []
    
    if V2_AVAILABLE:
        versions_to_test.append(('dictsqlite_v2版', 'async'))
    
    if not versions_to_test:
        print("❌ テスト可能なバージョンがありません")
        return
    
    # 各ベンチマークを実行
    benchmarks = [
        ("大規模データセット (5000 items)", lambda db: benchmark_large_dataset(db, 5000)),
        ("並行書き込み (1000 items, 10 concurrent)", lambda db: benchmark_concurrent_writes(db, 1000, 10)),
        ("更新操作 (500 items)", lambda db: benchmark_update_operations(db, 500)),
        ("削除操作 (500 items)", lambda db: benchmark_deletion_operations(db, 500)),
        ("混合ワークロード (1000 operations)", lambda db: benchmark_mixed_workload(db, 1000)),
    ]
    
    for bench_name, bench_func in benchmarks:
        result = AdvancedBenchmarkResult(bench_name)
        
        for version_name, version_type in versions_to_test:
            print(f"\n{'='*80}")
            print(f"🔬 テスト中: {version_name} - {bench_name}")
            print(f"{'='*80}")
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
                db_path = tmp.name
            
            try:
                if version_type == 'async' and V2_AVAILABLE:
                    db = DictSQLiteV2_Async(db_path)
                    try:
                        elapsed, ops, memory_info = await bench_func(db)
                        result.add_result(version_name, elapsed, ops, memory_info)
                        print(f"  ⏱️  {elapsed:.3f}s, {ops:.0f} ops/sec")
                        if memory_info:
                            print(f"  💾 ピークメモリ: {memory_info.get('final_peak_mb', 0):.2f} MB")
                    finally:
                        if hasattr(db, 'close'):
                            if asyncio.iscoroutinefunction(db.close):
                                await db.close()
                            else:
                                db.close()
                if hasattr(db, 'adelete'):
                    await db.adelete(f'mixed_key_{i-2}')
                elif hasattr(db, '__delitem__'):
                    del db[f'mixed_key_{i-2}']
            except Exception:
                pass
            finally:
                if os.path.exists(db_path):
                    os.unlink(db_path)
        
        results.append(result)
    
    # 結果サマリー
    print(f"\n{'='*80}")
    print("📊 拡張ベンチマーク結果サマリー")
    print(f"{'='*80}")
    
    for result in results:
        result.print_comparison()
    
    # 結果をJSONで保存
    output_dir = BENCHMARK_DIR / "results"
    output_dir.mkdir(exist_ok=True)
    
    output_file = output_dir / "advanced_benchmark_results.json"
    json_results = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'benchmarks': []
    }
    
    for result in results:
        json_results['benchmarks'].append({
            'name': result.name,
            'results': result.results
        })
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(json_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ 結果を保存しました: {output_file}")
    
    print(f"\n{'='*80}")
    print("✅ 拡張ベンチマーク完了！")
    print(f"{'='*80}")


if __name__ == "__main__":
    asyncio.run(run_advanced_benchmarks())
