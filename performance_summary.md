# 総合パフォーマンステスト結果
# Comprehensive Performance Test Results

**テスト実施日時 / Test Date**: 2025-10-04 03:56:24

---

## dictsqlite

| モード | 操作 | アイテム数 | 時間(秒) | OPS | 備考 |
|--------|------|-----------|---------|-----|------|
| sync | individual_write | 1,000 | 0.0036 | 277.85K ops/s |  |
| sync | individual_read | 1,000 | 0.0665 | 15.05K ops/s |  |
| sync | bulk_write | 1,000 | 0.0030 | 338.98K ops/s |  |
| sync | update | 1,000 | 0.0034 | 296.84K ops/s |  |
| sync | delete | 1,000 | 0.0019 | 513.50K ops/s |  |

## dictsqlite-fastest

| モード | 操作 | アイテム数 | 時間(秒) | OPS | 備考 |
|--------|------|-----------|---------|-----|------|
| sync | individual_write | 10,000 | 0.2422 | 41.28K ops/s | optimized |
| sync | individual_read | 10,000 | 0.1628 | 61.43K ops/s | optimized |
| sync | bulk_write | 10,000 | 0.0230 | 434.38K ops/s | optimized |
| sync | update | 10,000 | 0.3105 | 32.21K ops/s | optimized |
| sync | delete | 10,000 | 0.2168 | 46.12K ops/s | optimized |
| sync | mixed_operations | 10,000 | 0.2709 | 36.92K ops/s | optimized |
| async | individual_write | 10,000 | 21.4490 | 466.22 ops/s | optimized |
| async | individual_read | 10,000 | 6.6473 | 1.50K ops/s | optimized |
| async | bulk_write | 10,000 | 0.0310 | 322.64K ops/s | optimized |
| async | update | 10,000 | 19.6516 | 508.86 ops/s | optimized |
| async | delete | 10,000 | 20.8451 | 479.73 ops/s | optimized |
| async | mixed_operations | 10,000 | 17.0715 | 585.77 ops/s | optimized |

## beta

| モード | 操作 | アイテム数 | 時間(秒) | OPS | 備考 |
|--------|------|-----------|---------|-----|------|
| sync | individual_write | 10,000 | 0.0425 | 235.19K ops/s | normal_mode |
| sync | individual_write | 10,000 | 0.0404 | 247.31K ops/s | optimized_mode |
| sync | individual_read | 10,000 | 0.1632 | 61.27K ops/s | optimized_mode |
| sync | bulk_write | 10,000 | 0.0293 | 341.10K ops/s | optimized_mode |
| sync | update | 10,000 | 0.0471 | 212.42K ops/s | optimized_mode |
| sync | delete | 10,000 | 0.1615 | 61.93K ops/s | optimized_mode |
| sync | mixed_operations | 10,000 | 0.0840 | 119.05K ops/s | optimized_mode |

## パフォーマンス比較 / Performance Comparison

### 個別書き込み / Individual Write

| バージョン | OPS | ベースライン比 | 備考 |
|-----------|-----|---------------|------|
| dictsqlite | 277.85K ops/s | 1.00x |  |
| dictsqlite-fastest | 41.28K ops/s | 0.15x | optimized |
| beta | 235.19K ops/s | 0.85x | normal_mode |
| beta | 247.31K ops/s | 0.89x | optimized_mode |

### 個別読み込み / Individual Read

| バージョン | OPS | ベースライン比 | 備考 |
|-----------|-----|---------------|------|
| dictsqlite | 15.05K ops/s | 1.00x |  |
| dictsqlite-fastest | 61.43K ops/s | 4.08x | optimized |
| beta | 61.27K ops/s | 4.07x | optimized_mode |

### バルク書き込み / Bulk Write

| バージョン | OPS | ベースライン比 | 備考 |
|-----------|-----|---------------|------|
| dictsqlite | 338.98K ops/s | 1.00x |  |
| dictsqlite-fastest | 434.38K ops/s | 1.28x | optimized |
| beta | 341.10K ops/s | 1.01x | optimized_mode |

### 更新 / Update

| バージョン | OPS | ベースライン比 | 備考 |
|-----------|-----|---------------|------|
| dictsqlite | 296.84K ops/s | 1.00x |  |
| dictsqlite-fastest | 32.21K ops/s | 0.11x | optimized |
| beta | 212.42K ops/s | 0.72x | optimized_mode |

### 削除 / Delete

| バージョン | OPS | ベースライン比 | 備考 |
|-----------|-----|---------------|------|
| dictsqlite | 513.50K ops/s | 1.00x |  |
| dictsqlite-fastest | 46.12K ops/s | 0.09x | optimized |
| beta | 61.93K ops/s | 0.12x | optimized_mode |

### 混合操作 / Mixed Operations

| バージョン | OPS | ベースライン比 | 備考 |
|-----------|-----|---------------|------|
| dictsqlite-fastest | 36.92K ops/s | 36917.16x | optimized |
| beta | 119.05K ops/s | 119045.55x | optimized_mode |

### 非同期パフォーマンス / Async Performance

| バージョン | 操作 | OPS |
|-----------|------|-----|
| dictsqlite-fastest | individual_write | 466.22 ops/s |
| dictsqlite-fastest | individual_read | 1.50K ops/s |
| dictsqlite-fastest | bulk_write | 322.64K ops/s |
| dictsqlite-fastest | update | 508.86 ops/s |
| dictsqlite-fastest | delete | 479.73 ops/s |
| dictsqlite-fastest | mixed_operations | 585.77 ops/s |

## 速度倍率サマリー / Speed Multiplier Summary

DictSQLiteをベースライン(1.0x)とした場合の各バージョンの速度倍率:

| 操作 | dictsqlite-fastest | beta (optimized) |
|------|-------------------|------------------|
| 個別書き込み | 0.15x | 0.89x |
| 個別読み込み | 4.08x | 4.07x |
| バルク書き込み | 1.28x | 1.01x |
| 更新 | 0.11x | 0.72x |
| 削除 | 0.09x | 0.12x |

## サマリー / Summary

- **dictsqlite**: オリジナル版（ベースライン）
- **dictsqlite-fastest**: APSW使用の高速版
- **beta**: メモリ最適化版（LRUキャッシュ、バッファリング等）

### 主な発見事項 / Key Findings

1. バルク操作では dictsqlite-fastest が最も高速
2. 個別書き込みでは beta (optimized) が高いパフォーマンスを発揮
3. 混合操作では各バージョンの特性が顕著に現れる
