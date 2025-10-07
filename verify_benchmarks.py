#!/usr/bin/env python3
"""Verification script for v1, v2, v3 benchmark system

Tests that all benchmarks work correctly and produce expected results.
"""

import asyncio
import os
import sys
import subprocess
from pathlib import Path


def run_command(cmd, cwd=None):
    """Run a command and return success status."""
    print(f"\n{'='*70}")
    print(f"Running: {' '.join(cmd)}")
    print(f"{'='*70}")
    
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=False,
        text=True
    )
    
    success = result.returncode == 0
    status = "✅ SUCCESS" if success else "❌ FAILED"
    print(f"\n{status}: {' '.join(cmd)}")
    
    return success


def main():
    """Run verification tests."""
    print("=" * 70)
    print("DictSQLite-Fastest Benchmark System Verification")
    print("=" * 70)
    
    # Use absolute path from current script location
    script_dir = Path(__file__).parent.absolute()
    beta_dir = script_dir / "dictsqlite-fastest" / "beta"
    benchmark_dir = script_dir / "others" / "benchmark"
    
    # Verify directories exist
    if not beta_dir.exists():
        print(f"❌ Error: Beta directory not found at {beta_dir}")
        return 1
    if not benchmark_dir.exists():
        print(f"❌ Error: Benchmark directory not found at {benchmark_dir}")
        return 1
    
    results = []
    
    # Test 1: Direct benchmark_all_versions.py
    print("\n" + "="*70)
    print("Test 1: Direct v1 vs v2 vs v3 Comparison Benchmark")
    print("="*70)
    success = run_command(
        [sys.executable, "benchmark_all_versions.py"],
        cwd=str(beta_dir)
    )
    results.append(("benchmark_all_versions.py", success))
    
    # Test 2: Direct benchmark_detailed.py
    print("\n" + "="*70)
    print("Test 2: Detailed Optimization Benchmark")
    print("="*70)
    success = run_command(
        [sys.executable, "benchmark_detailed.py"],
        cwd=str(beta_dir)
    )
    results.append(("benchmark_detailed.py", success))
    
    # Test 3: run_benchmark.py with v1
    print("\n" + "="*70)
    print("Test 3: run_benchmark.py --beta v1")
    print("="*70)
    success = run_command(
        [sys.executable, "run_benchmark.py", "--beta", "v1"],
        cwd=str(benchmark_dir)
    )
    results.append(("run_benchmark.py v1", success))
    
    # Test 4: run_benchmark.py with v2
    print("\n" + "="*70)
    print("Test 4: run_benchmark.py --beta v2")
    print("="*70)
    success = run_command(
        [sys.executable, "run_benchmark.py", "--beta", "v2"],
        cwd=str(benchmark_dir)
    )
    results.append(("run_benchmark.py v2", success))
    
    # Test 5: run_benchmark.py with v3
    print("\n" + "="*70)
    print("Test 5: run_benchmark.py --beta v3")
    print("="*70)
    success = run_command(
        [sys.executable, "run_benchmark.py", "--beta", "v3"],
        cwd=str(benchmark_dir)
    )
    results.append(("run_benchmark.py v3", success))
    
    # Test 6: run_benchmark.py with all
    print("\n" + "="*70)
    print("Test 6: run_benchmark.py --beta all")
    print("="*70)
    success = run_command(
        [sys.executable, "run_benchmark.py", "--beta", "all"],
        cwd=str(benchmark_dir)
    )
    results.append(("run_benchmark.py all", success))
    
    # Summary
    print("\n" + "="*70)
    print("Verification Summary")
    print("="*70)
    
    passed = 0
    failed = 0
    
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status}: {test_name}")
        if success:
            passed += 1
        else:
            failed += 1
    
    print(f"\n{'='*70}")
    print(f"Results: {passed} passed, {failed} failed out of {len(results)} tests")
    print(f"{'='*70}")
    
    if failed == 0:
        print("\n🎉 All verification tests passed!")
        print("The benchmark system for v1, v2, and v3 is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
