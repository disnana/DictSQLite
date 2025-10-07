#!/usr/bin/env python3
"""
Comprehensive performance validation for v4 development.
Ensures ZERO performance regression at each step.
"""
import asyncio
import time
import os
import tempfile
from dictsqlite_fastest_beta_v4_step1 import AsyncDictSQLiteFastestBetaV4 as V4Step1
from dictsqlite_fastest_beta_v4_step2 import AsyncDictSQLiteFastestBetaV4 as V4Step2
from dictsqlite_fastest_beta_v4_step3 import AsyncDictSQLiteFastestBetaV4 as V4Step3
from dictsqlite_fastest_beta_v3_alpha import AsyncDictSQLiteFastestBetaV3


async def benchmark_sequential_reads(db_class, db_path, count=1000):
    """ベンチマーク: シーケンシャルリード"""
    db = db_class(db_path)
    
    async with db:
        # データを準備
        items = {f'key_{i}': f'value_{i}' for i in range(count)}
        await db.abulk_insert(items)
        
        # シーケンシャルリード計測
        start = time.time()
        for i in range(count):
            value = await db.aget(f'key_{i}')
            assert value == f'value_{i}'
        elapsed = time.time() - start
        
        ops_per_sec = count / elapsed if elapsed > 0 else 0
        return ops_per_sec


async def benchmark_concurrent_reads(db_class, db_path, count=1000, concurrent=10):
    """ベンチマーク: 並行リード"""
    db = db_class(db_path)
    
    async with db:
        # データを準備
        items = {f'key_{i}': f'value_{i}' for i in range(count)}
        await db.abulk_insert(items)
        
        # 並行リード計測
        async def read_batch(start_idx, batch_size):
            for i in range(start_idx, start_idx + batch_size):
                value = await db.aget(f'key_{i}')
                assert value == f'value_{i}'
        
        batch_size = count // concurrent
        start = time.time()
        tasks = [read_batch(i * batch_size, batch_size) for i in range(concurrent)]
        await asyncio.gather(*tasks)
        elapsed = time.time() - start
        
        ops_per_sec = count / elapsed if elapsed > 0 else 0
        return ops_per_sec


async def benchmark_writes(db_class, db_path, count=1000):
    """ベンチマーク: 書き込み"""
    db = db_class(db_path)
    
    async with db:
        start = time.time()
        for i in range(count):
            await db.aset(f'key_{i}', f'value_{i}')
        elapsed = time.time() - start
        
        ops_per_sec = count / elapsed if elapsed > 0 else 0
        return ops_per_sec


async def benchmark_bulk_inserts(db_class, db_path, count=1000):
    """ベンチマーク: バルク挿入"""
    db = db_class(db_path)
    
    async with db:
        items = {f'key_{i}': f'value_{i}' for i in range(count)}
        
        start = time.time()
        await db.abulk_insert(items)
        elapsed = time.time() - start
        
        ops_per_sec = count / elapsed if elapsed > 0 else 0
        return ops_per_sec


async def run_all_benchmarks():
    """全ベンチマークを実行"""
    print("=" * 80)
    print("v4 Performance Validation - ZERO Regression Tolerance")
    print("=" * 80)
    print()
    
    versions = [
        ("v3-alpha (baseline)", AsyncDictSQLiteFastestBetaV3),
        ("v4 Step 1", V4Step1),
        ("v4 Step 2", V4Step2),
        ("v4 Step 3", V4Step3),
    ]
    
    benchmarks = [
        ("Sequential Reads (1000 items)", lambda cls, path: benchmark_sequential_reads(cls, path, 1000)),
        ("Concurrent Reads (1000 items, 10 concurrent)", lambda cls, path: benchmark_concurrent_reads(cls, path, 1000, 10)),
        ("Sequential Writes (1000 items)", lambda cls, path: benchmark_writes(cls, path, 1000)),
        ("Bulk Insert (1000 items)", lambda cls, path: benchmark_bulk_inserts(cls, path, 1000)),
    ]
    
    results = {}
    
    for bench_name, bench_func in benchmarks:
        print(f"\n{bench_name}:")
        print("-" * 60)
        
        baseline_ops = None
        
        for version_name, db_class in versions:
            # 一時ファイルを作成
            with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
                db_path = tmp.name
            
            try:
                ops_per_sec = await bench_func(db_class, db_path)
                
                if baseline_ops is None:
                    baseline_ops = ops_per_sec
                    ratio = 1.0
                    status = "baseline"
                else:
                    ratio = ops_per_sec / baseline_ops if baseline_ops > 0 else 0
                    if ratio >= 1.0:
                        status = f"✅ {ratio:.2f}x (FASTER or SAME)"
                    elif ratio >= 0.95:
                        status = f"⚠️  {ratio:.2f}x (within 5% tolerance)"
                    else:
                        status = f"❌ {ratio:.2f}x (REGRESSION > 5%)"
                
                print(f"  {version_name:30s}: {ops_per_sec:>10,.0f} ops/sec  {status}")
                
                results[(bench_name, version_name)] = {
                    'ops_per_sec': ops_per_sec,
                    'ratio': ratio,
                    'status': status
                }
            finally:
                # クリーンアップ
                if os.path.exists(db_path):
                    os.unlink(db_path)
    
    # サマリー
    print("\n" + "=" * 80)
    print("SUMMARY - Performance Validation")
    print("=" * 80)
    
    regression_count = 0
    for (bench_name, version_name), result in results.items():
        if 'Step' in version_name and result['ratio'] < 0.95:
            regression_count += 1
            print(f"❌ REGRESSION: {version_name} - {bench_name}: {result['ratio']:.2f}x")
    
    if regression_count == 0:
        print("✅ NO REGRESSIONS DETECTED - All v4 steps maintain >= 95% of baseline performance")
    else:
        print(f"❌ {regression_count} REGRESSIONS DETECTED")
    
    print()
    
    return regression_count == 0


if __name__ == '__main__':
    success = asyncio.run(run_all_benchmarks())
    exit(0 if success else 1)
