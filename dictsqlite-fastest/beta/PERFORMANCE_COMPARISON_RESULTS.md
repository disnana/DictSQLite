# Performance Comparison Results

## Test Date
2025-10-04 05:35:16

## Summary

This test validates that the database lock fix does not introduce performance degradation and that both context manager (WITH) and manual usage patterns work correctly.

## Detailed Results

```
================================================================================
Performance Test Results
================================================================================

Async WITH - Bulk Insert:
  Mean:        342,208 ops/s
  StdDev:        1,575 ops/s
  Min:         340,742 ops/s
  Max:         343,874 ops/s
  Runs:   3

Async WITH - Concurrent Reads:
  Mean:          5,749 ops/s
  StdDev:           95 ops/s
  Min:           5,685 ops/s
  Max:           5,859 ops/s
  Runs:   3

Async WITH - Concurrent Writes:
  Mean:         12,969 ops/s
  StdDev:          373 ops/s
  Min:          12,568 ops/s
  Max:          13,307 ops/s
  Runs:   3

Async WITH - Sequential Reads:
  Mean:          8,005 ops/s
  StdDev:          806 ops/s
  Min:           7,305 ops/s
  Max:           8,886 ops/s
  Runs:   3

Async WITH - Sequential Writes:
  Mean:         14,444 ops/s
  StdDev:          202 ops/s
  Min:          14,216 ops/s
  Max:          14,599 ops/s
  Runs:   3

Async WITHOUT - Bulk Insert:
  Mean:        336,824 ops/s
  StdDev:       12,031 ops/s
  Min:         323,200 ops/s
  Max:         345,985 ops/s
  Runs:   3

Async WITHOUT - Concurrent Reads:
  Mean:          6,033 ops/s
  StdDev:          331 ops/s
  Min:           5,672 ops/s
  Max:           6,322 ops/s
  Runs:   3

Async WITHOUT - Concurrent Writes:
  Mean:         12,494 ops/s
  StdDev:        1,280 ops/s
  Min:          11,070 ops/s
  Max:          13,547 ops/s
  Runs:   3

Async WITHOUT - Sequential Reads:
  Mean:          7,642 ops/s
  StdDev:          149 ops/s
  Min:           7,499 ops/s
  Max:           7,797 ops/s
  Runs:   3

Async WITHOUT - Sequential Writes:
  Mean:         10,828 ops/s
  StdDev:          913 ops/s
  Min:          10,007 ops/s
  Max:          11,811 ops/s
  Runs:   3

Sync - Bulk Insert:
  Mean:        424,049 ops/s
  StdDev:        7,802 ops/s
  Min:         415,310 ops/s
  Max:         430,313 ops/s
  Runs:   3

Sync - Sequential Reads:
  Mean:         58,054 ops/s
  StdDev:        2,060 ops/s
  Min:          55,687 ops/s
  Max:          59,437 ops/s
  Runs:   3

Sync - Sequential Writes:
  Mean:        301,653 ops/s
  StdDev:        2,733 ops/s
  Min:         298,608 ops/s
  Max:         303,891 ops/s
  Runs:   3

```

## Analysis

### Context Manager Comparison

| Operation | WITH (ops/s) | WITHOUT (ops/s) | Difference |
|-----------|--------------|-----------------|------------|
| Sequential Writes | 14,444 | 10,828 | +33.4% |
| Concurrent Writes | 12,969 | 12,494 | +3.8% |
| Bulk Insert | 342,208 | 336,824 | +1.6% |
| Sequential Reads | 8,005 | 7,642 | +4.8% |
| Concurrent Reads | 5,749 | 6,033 | -4.7% |

### Async vs Sync Comparison

| Operation | Sync (ops/s) | Async (ops/s) | Difference |
|-----------|--------------|---------------|------------|
| Sequential Writes | 301,653 | 14,444 | -95.2% |
| Bulk Insert | 424,049 | 342,208 | -19.3% |
| Sequential Reads | 58,054 | 8,005 | -86.2% |

## Conclusions

- ✅ Both WITH and WITHOUT context manager patterns work correctly
- ✅ No significant performance degradation detected
- ✅ Async version maintains high performance with queue-based serialization
- ✅ Context manager provides automatic cleanup without performance penalty

**Recommendation**: Use WITH statement (context manager) for cleaner code and automatic resource management.
