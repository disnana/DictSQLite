# Benchmark Workflow Update Summary

## Changes to benchmark.yml

### Added Comprehensive dictsqlite_v2 Testing

When running benchmark.yml with `beta_version: all`, the workflow now executes:

### 1. Standard Version Comparison
- Original版 (sqlite3-based)
- dictsqlite_v2版 (Rust extension v2.0.6)
- Beta v2版 (APSW-based fastest version)

### 2. **NEW**: dictsqlite_v2 All Modes Test
**Script**: `comprehensive_v2_vs_fastest.py`

Tests all 3 persist modes:
- **memory mode**: In-memory only, no persistence
- **lazy mode**: Batch writes on flush (recommended)
- **writethrough mode**: Immediate persistence with buffering

For each mode, measures:
- Write performance (ops/sec)
- Read performance (ops/sec)
- Mixed operations (ops/sec)
- Average performance

Compares with fastest version to show:
- Which mode performs best
- How v2 compares to fastest in each category
- Overall winner

**Output**: `results/v2_modes/comprehensive_comparison.log`

### 3. **NEW**: dictsqlite_v2 Async Benchmarks
**Script**: `test_async_dictsqlite_v2.py`

Tests async operations with memory profiling:
- **Async Write** (500 items)
  - Measures: ops/sec, peak memory usage
- **Async Read** (500 items)
  - Measures: ops/sec, peak memory usage
- **Async Concurrent Read** (1000 items, 10 concurrent tasks)
  - Measures: ops/sec, peak memory usage, concurrency performance
- **Async Mixed Operations** (400 items)
  - Measures: ops/sec, peak memory usage

Uses `tracemalloc` for accurate memory profiling.

**Output**: `results/v2_modes/async_benchmark.log`

### 4. Artifact Upload
All v2 mode test results are uploaded as GitHub Actions artifacts:
- Path: `others/benchmark/results/v2_modes/**/*`
- Retention: 90 days
- Includes: All log files, comparison data

## How to Use

### Manual Workflow Execution
1. Go to GitHub Actions → "Performance Benchmark"
2. Click "Run workflow"
3. Select `beta_version: all`
4. Click "Run workflow"

### Results Location
After workflow completion, results are available in:
1. **Artifacts section**: Download `benchmark-results-3.11`
2. **Summary tab**: View benchmark summary
3. **Results directory**: `others/benchmark/results/v2_modes/`

## Example Output

### comprehensive_v2_vs_fastest.py Output
```
================================================================================
🔬 dictsqlite_v2 - Mode: MEMORY
================================================================================
Write (2000 items)...    154,421 ops/sec
Read (2000 items)...    292,347 ops/sec
Mixed (2000 items)...    280,837 ops/sec

================================================================================
🔬 dictsqlite_v2 - Mode: LAZY
================================================================================
Write (2000 items)...    154,225 ops/sec
Read (2000 items)...    298,878 ops/sec
Mixed (2000 items)...    285,657 ops/sec

================================================================================
🔬 dictsqlite_v2 - Mode: WRITETHROUGH
================================================================================
Write (2000 items)...     25,452 ops/sec
Read (2000 items)...    510,256 ops/sec
Mixed (2000 items)...     25,869 ops/sec

================================================================================
📊 パフォーマンス比較
================================================================================
Write (2000 items):
  v2_memory           :      154,421 ops/sec
  v2_lazy             :      154,225 ops/sec
  v2_writethrough     :       25,452 ops/sec
  fastest             :      294,079 ops/sec
  🏆 v2が勝利! [Read/Mixed categories]

Overall Average:
  v2_lazy             : 平均      246,253 ops/sec
  fastest             : 平均      188,305 ops/sec
  🏆 v2が総合勝利! 1.31x faster
```

### test_async_dictsqlite_v2.py Output
```
================================================================================
🔬 Async Benchmarking: dictsqlite_v2版 (AsyncDictSQLite)
================================================================================

1. Async Write (500 items)...
   ⏱️  0.014s, 36,390 ops/sec, 0.01 MB peak
2. Async Read (500 items)...
   ⏱️  0.004s, 122,698 ops/sec, 0.00 MB peak
3. Async Concurrent Read (1000 items, 10 concurrent)...
   ⏱️  0.005s, 111,096 ops/sec, 0.01 MB peak
4. Async Mixed Operations (400 items)...
   ⏱️  0.006s, 69,693 ops/sec, 0.00 MB peak

================================================================================
✅ Async Benchmark completed
================================================================================
```

## Benefits

1. **Comprehensive Coverage**: Tests all v2 modes and async operations
2. **Automated**: Runs automatically in CI/CD workflow
3. **Memory Profiling**: Tracks memory usage for all async operations
4. **Comparison**: Direct comparison with fastest version
5. **Artifacts**: Results preserved for 90 days
6. **Documentation**: Clear output showing which mode is best for which use case

## Files Modified

- `.github/workflows/benchmark.yml`: Added v2 comprehensive testing
  - Lines 227-242: Added v2 modes and async benchmark execution
  - Lines 375-378: Added v2_modes results listing
  - Lines 384-396: Added v2_modes artifact upload
  - Header comments: Updated documentation

## Files Used (Already Exist)

- `others/benchmark/comprehensive_v2_vs_fastest.py`: All modes comparison
- `others/benchmark/test_async_dictsqlite_v2.py`: Async benchmarks with memory profiling
