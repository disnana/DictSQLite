# 総合パフォーマンステスト結果
# Comprehensive Performance Test Results

**テスト実施日時 / Test Date**: 2025-10-04 04:47:50

---

## dictsqlite

| モード | 操作 | アイテム数 | 時間(秒) | OPS | 備考 |
|--------|------|-----------|---------|-----|------|
| sync | individual_write | 1,000 | 0.0036 | 276.25K ops/s |  |
| sync | individual_read | 1,000 | 0.0999 | 10.01K ops/s |  |
| sync | bulk_write | 1,000 | 0.0030 | 337.67K ops/s |  |
| sync | update | 1,000 | 0.0033 | 304.91K ops/s |  |
| sync | delete | 1,000 | 0.0020 | 510.85K ops/s |  |
| async | individual_write | 1,000 | 0.6797 | 1.47K ops/s | via_asyncio.to_thread |
| async | individual_read | 1,000 | 0.0715 | 13.98K ops/s | via_asyncio.to_thread |
| async | bulk_write | 1,000 | 0.6975 | 1.43K ops/s | via_asyncio.to_thread |
| async | update | 1,000 | 0.7010 | 1.43K ops/s | via_asyncio.to_thread |
| async | delete | 1,000 | 0.6727 | 1.49K ops/s | via_asyncio.to_thread |
| async | mixed_operations | 1,000 | 0.5030 | 1.99K ops/s | via_asyncio.to_thread |

## dictsqlite-fastest

| モード | 操作 | アイテム数 | 時間(秒) | OPS | 備考 |
|--------|------|-----------|---------|-----|------|
| sync | individual_write | 10,000 | 0.2277 | 43.92K ops/s | optimized |
| sync | individual_read | 10,000 | 0.1675 | 59.70K ops/s | optimized |
| sync | bulk_write | 10,000 | 0.0230 | 433.86K ops/s | optimized |
| sync | update | 10,000 | 0.2875 | 34.78K ops/s | optimized |
| sync | delete | 10,000 | 0.2057 | 48.62K ops/s | optimized |
| sync | mixed_operations | 10,000 | 0.2646 | 37.80K ops/s | optimized |
| async | individual_write | 10,000 | 15.5983 | 641.09 ops/s | optimized |
| async | individual_read | 10,000 | 6.8814 | 1.45K ops/s | optimized |
| async | bulk_write | 10,000 | 0.0308 | 325.03K ops/s | optimized |
| async | update | 10,000 | 16.2394 | 615.79 ops/s | optimized |
| async | delete | 10,000 | 15.8144 | 632.34 ops/s | optimized |
| async | mixed_operations | 10,000 | 13.1519 | 760.35 ops/s | optimized |

## beta

| モード | 操作 | アイテム数 | 時間(秒) | OPS | 備考 |
|--------|------|-----------|---------|-----|------|
| sync | individual_write | 10,000 | 0.0422 | 237.07K ops/s | normal_mode |
| sync | individual_write | 10,000 | 0.0408 | 244.93K ops/s | optimized_mode |
| sync | individual_read | 10,000 | 0.1661 | 60.19K ops/s | optimized_mode |
| sync | bulk_write | 10,000 | 0.0288 | 347.37K ops/s | optimized_mode |
| sync | update | 10,000 | 0.0441 | 226.81K ops/s | optimized_mode |
| sync | delete | 10,000 | 0.1606 | 62.27K ops/s | optimized_mode |
| sync | mixed_operations | 10,000 | 0.0862 | 115.99K ops/s | optimized_mode |

## パフォーマンス比較 / Performance Comparison

### 個別書き込み / Individual Write

| バージョン | OPS | ベースライン比 | 備考 |
|-----------|-----|---------------|------|
| dictsqlite | 276.25K ops/s | 1.00x |  |
| dictsqlite-fastest | 43.92K ops/s | 0.16x | optimized |
| beta | 237.07K ops/s | 0.86x | normal_mode |
| beta | 244.93K ops/s | 0.89x | optimized_mode |

### 個別読み込み / Individual Read

| バージョン | OPS | ベースライン比 | 備考 |
|-----------|-----|---------------|------|
| dictsqlite | 10.01K ops/s | 1.00x |  |
| dictsqlite-fastest | 59.70K ops/s | 5.96x | optimized |
| beta | 60.19K ops/s | 6.01x | optimized_mode |

### バルク書き込み / Bulk Write

| バージョン | OPS | ベースライン比 | 備考 |
|-----------|-----|---------------|------|
| dictsqlite | 337.67K ops/s | 1.00x |  |
| dictsqlite-fastest | 433.86K ops/s | 1.28x | optimized |
| beta | 347.37K ops/s | 1.03x | optimized_mode |

### 更新 / Update

| バージョン | OPS | ベースライン比 | 備考 |
|-----------|-----|---------------|------|
| dictsqlite | 304.91K ops/s | 1.00x |  |
| dictsqlite-fastest | 34.78K ops/s | 0.11x | optimized |
| beta | 226.81K ops/s | 0.74x | optimized_mode |

### 削除 / Delete

| バージョン | OPS | ベースライン比 | 備考 |
|-----------|-----|---------------|------|
| dictsqlite | 510.85K ops/s | 1.00x |  |
| dictsqlite-fastest | 48.62K ops/s | 0.10x | optimized |
| beta | 62.27K ops/s | 0.12x | optimized_mode |

### 混合操作 / Mixed Operations

| バージョン | OPS | ベースライン比 | 備考 |
|-----------|-----|---------------|------|
| dictsqlite-fastest | 37.80K ops/s | 37799.42x | optimized |
| beta | 115.99K ops/s | 115992.56x | optimized_mode |

### 非同期パフォーマンス / Async Performance

| バージョン | 操作 | OPS |
|-----------|------|-----|
| dictsqlite | individual_write | 1.47K ops/s |
| dictsqlite | individual_read | 13.98K ops/s |
| dictsqlite | bulk_write | 1.43K ops/s |
| dictsqlite | update | 1.43K ops/s |
| dictsqlite | delete | 1.49K ops/s |
| dictsqlite | mixed_operations | 1.99K ops/s |
| dictsqlite-fastest | individual_write | 641.09 ops/s |
| dictsqlite-fastest | individual_read | 1.45K ops/s |
| dictsqlite-fastest | bulk_write | 325.03K ops/s |
| dictsqlite-fastest | update | 615.79 ops/s |
| dictsqlite-fastest | delete | 632.34 ops/s |
| dictsqlite-fastest | mixed_operations | 760.35 ops/s |

## 速度倍率サマリー / Speed Multiplier Summary

DictSQLiteをベースライン(1.0x)とした場合の各バージョンの速度倍率:

| 操作 | dictsqlite-fastest | beta (optimized) |
|------|-------------------|------------------|
| 個別書き込み | 0.16x | 0.89x |
| 個別読み込み | 5.96x | 6.01x |
| バルク書き込み | 1.28x | 1.03x |
| 更新 | 0.11x | 0.74x |
| 削除 | 0.10x | 0.12x |

## サマリー / Summary

- **dictsqlite**: オリジナル版（ベースライン）
- **dictsqlite-fastest**: APSW使用の高速版
- **beta**: メモリ最適化版（LRUキャッシュ、バッファリング等）

### 主な発見事項 / Key Findings

1. バルク操作では dictsqlite-fastest が最も高速
2. 個別書き込みでは beta (optimized) が高いパフォーマンスを発揮
3. 混合操作では各バージョンの特性が顕著に現れる
