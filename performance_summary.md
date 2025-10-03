# 総合パフォーマンステスト結果
# Comprehensive Performance Test Results

**テスト実施日時 / Test Date**: 2025-10-03 10:47:20

---

## dictsqlite

| モード | 操作 | アイテム数 | 時間(秒) | OPS | 備考 |
|--------|------|-----------|---------|-----|------|
| sync | individual_write | 1,000 | 0.0043 | 229.91K ops/s |  |
| sync | individual_read | 1,000 | 0.0846 | 11.81K ops/s |  |
| sync | bulk_write | 1,000 | 0.0029 | 344.99K ops/s |  |

## dictsqlite-fastest

| モード | 操作 | アイテム数 | 時間(秒) | OPS | 備考 |
|--------|------|-----------|---------|-----|------|
| sync | individual_write | 10,000 | 0.2418 | 41.35K ops/s |  |
| sync | individual_read | 10,000 | 0.1620 | 61.73K ops/s |  |
| sync | bulk_write | 10,000 | 0.0231 | 432.46K ops/s |  |
| async | individual_write | 100 | 0.1668 | 599.56 ops/s |  |
| async | individual_read | 100 | 0.0666 | 1.50K ops/s |  |
| async | bulk_write | 100 | 0.0038 | 26.64K ops/s |  |

## beta

| モード | 操作 | アイテム数 | 時間(秒) | OPS | 備考 |
|--------|------|-----------|---------|-----|------|
| sync | individual_write | 10,000 | 0.0420 | 237.82K ops/s | normal_mode |
| sync | individual_write | 10,000 | 0.0406 | 246.40K ops/s | optimized_mode |
| sync | individual_read | 10,000 | 0.1679 | 59.55K ops/s | optimized_mode |
| sync | bulk_write | 10,000 | 0.0290 | 344.38K ops/s | optimized_mode |

## パフォーマンス比較 / Performance Comparison

### 同期書き込みパフォーマンス / Sync Write Performance

| バージョン | OPS | ベースライン比 |
|-----------|-----|---------------|
| dictsqlite () | 229.91K ops/s | 1.00x |
| dictsqlite-fastest () | 41.35K ops/s | 0.18x |
| beta (normal_mode) | 237.82K ops/s | 1.03x |
| beta (optimized_mode) | 246.40K ops/s | 1.07x |

### バルク書き込みパフォーマンス / Bulk Write Performance

| バージョン | OPS | ベースライン比 |
|-----------|-----|---------------|
| dictsqlite | 344.99K ops/s | 1.00x |
| dictsqlite-fastest | 432.46K ops/s | 1.25x |
| beta | 344.38K ops/s | 1.00x |

### 非同期パフォーマンス / Async Performance

| バージョン | 操作 | OPS |
|-----------|------|-----|
| dictsqlite-fastest | individual_write | 599.56 ops/s |
| dictsqlite-fastest | individual_read | 1.50K ops/s |
| dictsqlite-fastest | bulk_write | 26.64K ops/s |

## サマリー / Summary

- **dictsqlite**: オリジナル版（ベースライン）
- **dictsqlite-fastest**: APSW使用の高速版
- **beta**: メモリ最適化版（LRUキャッシュ、バッファリング等）
