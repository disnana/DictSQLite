# 総合パフォーマンステスト結果
# Comprehensive Performance Test Results

**テスト実施日時 / Test Date**: 2025-10-03 10:50:30

---

## dictsqlite

| モード | 操作 | アイテム数 | 時間(秒) | OPS | 備考 |
|--------|------|-----------|---------|-----|------|
| sync | individual_write | 1,000 | 0.0042 | 237.72K ops/s |  |
| sync | individual_read | 1,000 | 0.0663 | 15.08K ops/s |  |
| sync | bulk_write | 1,000 | 0.0030 | 334.97K ops/s |  |
| sync | update | 1,000 | 0.0033 | 302.61K ops/s |  |
| sync | delete | 1,000 | 0.0019 | 523.50K ops/s |  |

## dictsqlite-fastest

| モード | 操作 | アイテム数 | 時間(秒) | OPS | 備考 |
|--------|------|-----------|---------|-----|------|
| sync | individual_write | 10,000 | 0.2340 | 42.73K ops/s |  |
| sync | individual_read | 10,000 | 0.1642 | 60.90K ops/s |  |
| sync | bulk_write | 10,000 | 0.0228 | 437.86K ops/s |  |
| sync | update | 10,000 | 0.2900 | 34.48K ops/s |  |
| sync | delete | 10,000 | 0.2049 | 48.81K ops/s |  |
| sync | mixed_operations | 10,000 | 0.2612 | 38.28K ops/s |  |
| async | individual_write | 100 | 0.1649 | 606.28 ops/s |  |
| async | individual_read | 100 | 0.0675 | 1.48K ops/s |  |
| async | bulk_write | 100 | 0.0042 | 23.85K ops/s |  |

## beta

| モード | 操作 | アイテム数 | 時間(秒) | OPS | 備考 |
|--------|------|-----------|---------|-----|------|
| sync | individual_write | 10,000 | 0.0413 | 242.07K ops/s | normal_mode |
| sync | individual_write | 10,000 | 0.0405 | 247.15K ops/s | optimized_mode |
| sync | individual_read | 10,000 | 0.1646 | 60.74K ops/s | optimized_mode |
| sync | bulk_write | 10,000 | 0.0303 | 329.50K ops/s | optimized_mode |
| sync | update | 10,000 | 0.0440 | 227.07K ops/s | optimized_mode |
| sync | delete | 10,000 | 0.1598 | 62.59K ops/s | optimized_mode |
| sync | mixed_operations | 10,000 | 0.0854 | 117.11K ops/s | optimized_mode |

## パフォーマンス比較 / Performance Comparison

### 個別書き込み / Individual Write

| バージョン | OPS | ベースライン比 | 備考 |
|-----------|-----|---------------|------|
| dictsqlite | 237.72K ops/s | 1.00x |  |
| dictsqlite-fastest | 42.73K ops/s | 0.18x |  |
| beta | 242.07K ops/s | 1.02x | normal_mode |
| beta | 247.15K ops/s | 1.04x | optimized_mode |

### 個別読み込み / Individual Read

| バージョン | OPS | ベースライン比 | 備考 |
|-----------|-----|---------------|------|
| dictsqlite | 15.08K ops/s | 1.00x |  |
| dictsqlite-fastest | 60.90K ops/s | 4.04x |  |
| beta | 60.74K ops/s | 4.03x | optimized_mode |

### バルク書き込み / Bulk Write

| バージョン | OPS | ベースライン比 | 備考 |
|-----------|-----|---------------|------|
| dictsqlite | 334.97K ops/s | 1.00x |  |
| dictsqlite-fastest | 437.86K ops/s | 1.31x |  |
| beta | 329.50K ops/s | 0.98x | optimized_mode |

### 更新 / Update

| バージョン | OPS | ベースライン比 | 備考 |
|-----------|-----|---------------|------|
| dictsqlite | 302.61K ops/s | 1.00x |  |
| dictsqlite-fastest | 34.48K ops/s | 0.11x |  |
| beta | 227.07K ops/s | 0.75x | optimized_mode |

### 削除 / Delete

| バージョン | OPS | ベースライン比 | 備考 |
|-----------|-----|---------------|------|
| dictsqlite | 523.50K ops/s | 1.00x |  |
| dictsqlite-fastest | 48.81K ops/s | 0.09x |  |
| beta | 62.59K ops/s | 0.12x | optimized_mode |

### 混合操作 / Mixed Operations

| バージョン | OPS | ベースライン比 | 備考 |
|-----------|-----|---------------|------|
| dictsqlite-fastest | 38.28K ops/s | 38283.50x |  |
| beta | 117.11K ops/s | 117107.28x | optimized_mode |

### 非同期パフォーマンス / Async Performance

| バージョン | 操作 | OPS |
|-----------|------|-----|
| dictsqlite-fastest | individual_write | 606.28 ops/s |
| dictsqlite-fastest | individual_read | 1.48K ops/s |
| dictsqlite-fastest | bulk_write | 23.85K ops/s |

## 速度倍率サマリー / Speed Multiplier Summary

DictSQLiteをベースライン(1.0x)とした場合の各バージョンの速度倍率:

| 操作 | dictsqlite-fastest | beta (optimized) |
|------|-------------------|------------------|
| 個別書き込み | 0.18x | 1.04x |
| 個別読み込み | 4.04x | 4.03x |
| バルク書き込み | 1.31x | 0.98x |
| 更新 | 0.11x | 0.75x |
| 削除 | 0.09x | 0.12x |

## サマリー / Summary

- **dictsqlite**: オリジナル版（ベースライン）
- **dictsqlite-fastest**: APSW使用の高速版
- **beta**: メモリ最適化版（LRUキャッシュ、バッファリング等）

### 主な発見事項 / Key Findings

1. バルク操作では dictsqlite-fastest が最も高速
2. 個別書き込みでは beta (optimized) が高いパフォーマンスを発揮
3. 混合操作では各バージョンの特性が顕著に現れる
