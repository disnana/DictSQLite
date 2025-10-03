# 総合パフォーマンステスト結果
# Comprehensive Performance Test Results

**テスト実施日時 / Test Date**: 2025-10-03 10:54:53

---

## dictsqlite

| モード | 操作 | アイテム数 | 時間(秒) | OPS | 備考 |
|--------|------|-----------|---------|-----|------|
| sync | individual_write | 1,000 | 0.0041 | 241.31K ops/s |  |
| sync | individual_read | 1,000 | 0.0661 | 15.13K ops/s |  |
| sync | bulk_write | 1,000 | 0.0029 | 344.80K ops/s |  |
| sync | update | 1,000 | 0.0033 | 307.56K ops/s |  |
| sync | delete | 1,000 | 0.0020 | 494.65K ops/s |  |

## dictsqlite-fastest

| モード | 操作 | アイテム数 | 時間(秒) | OPS | 備考 |
|--------|------|-----------|---------|-----|------|
| sync | individual_write | 10,000 | 0.2256 | 44.32K ops/s |  |
| sync | individual_read | 10,000 | 0.1676 | 59.67K ops/s |  |
| sync | bulk_write | 10,000 | 0.0232 | 430.38K ops/s |  |
| sync | update | 10,000 | 0.2889 | 34.61K ops/s |  |
| sync | delete | 10,000 | 0.2055 | 48.66K ops/s |  |
| sync | mixed_operations | 10,000 | 0.2610 | 38.32K ops/s |  |
| async | individual_write | 100 | 0.1613 | 620.07 ops/s |  |
| async | individual_read | 100 | 0.0676 | 1.48K ops/s |  |
| async | bulk_write | 100 | 0.0041 | 24.42K ops/s |  |

## beta

| モード | 操作 | アイテム数 | 時間(秒) | OPS | 備考 |
|--------|------|-----------|---------|-----|------|
| sync | individual_write | 10,000 | 0.0415 | 241.18K ops/s | normal_mode |
| sync | individual_write | 10,000 | 0.0408 | 245.14K ops/s | optimized_mode |
| sync | individual_read | 10,000 | 0.1656 | 60.38K ops/s | optimized_mode |
| sync | bulk_write | 10,000 | 0.0284 | 352.37K ops/s | optimized_mode |
| sync | update | 10,000 | 0.0448 | 223.03K ops/s | optimized_mode |
| sync | delete | 10,000 | 0.1620 | 61.73K ops/s | optimized_mode |
| sync | mixed_operations | 10,000 | 0.0868 | 115.23K ops/s | optimized_mode |

## パフォーマンス比較 / Performance Comparison

### 個別書き込み / Individual Write

| バージョン | OPS | ベースライン比 | 備考 |
|-----------|-----|---------------|------|
| dictsqlite | 241.31K ops/s | 1.00x |  |
| dictsqlite-fastest | 44.32K ops/s | 0.18x |  |
| beta | 241.18K ops/s | 1.00x | normal_mode |
| beta | 245.14K ops/s | 1.02x | optimized_mode |

### 個別読み込み / Individual Read

| バージョン | OPS | ベースライン比 | 備考 |
|-----------|-----|---------------|------|
| dictsqlite | 15.13K ops/s | 1.00x |  |
| dictsqlite-fastest | 59.67K ops/s | 3.94x |  |
| beta | 60.38K ops/s | 3.99x | optimized_mode |

### バルク書き込み / Bulk Write

| バージョン | OPS | ベースライン比 | 備考 |
|-----------|-----|---------------|------|
| dictsqlite | 344.80K ops/s | 1.00x |  |
| dictsqlite-fastest | 430.38K ops/s | 1.25x |  |
| beta | 352.37K ops/s | 1.02x | optimized_mode |

### 更新 / Update

| バージョン | OPS | ベースライン比 | 備考 |
|-----------|-----|---------------|------|
| dictsqlite | 307.56K ops/s | 1.00x |  |
| dictsqlite-fastest | 34.61K ops/s | 0.11x |  |
| beta | 223.03K ops/s | 0.73x | optimized_mode |

### 削除 / Delete

| バージョン | OPS | ベースライン比 | 備考 |
|-----------|-----|---------------|------|
| dictsqlite | 494.65K ops/s | 1.00x |  |
| dictsqlite-fastest | 48.66K ops/s | 0.10x |  |
| beta | 61.73K ops/s | 0.12x | optimized_mode |

### 混合操作 / Mixed Operations

| バージョン | OPS | ベースライン比 | 備考 |
|-----------|-----|---------------|------|
| dictsqlite-fastest | 38.32K ops/s | 38315.89x |  |
| beta | 115.23K ops/s | 115225.23x | optimized_mode |

### 非同期パフォーマンス / Async Performance

| バージョン | 操作 | OPS |
|-----------|------|-----|
| dictsqlite-fastest | individual_write | 620.07 ops/s |
| dictsqlite-fastest | individual_read | 1.48K ops/s |
| dictsqlite-fastest | bulk_write | 24.42K ops/s |

## 速度倍率サマリー / Speed Multiplier Summary

DictSQLiteをベースライン(1.0x)とした場合の各バージョンの速度倍率:

| 操作 | dictsqlite-fastest | beta (optimized) |
|------|-------------------|------------------|
| 個別書き込み | 0.18x | 1.02x |
| 個別読み込み | 3.94x | 3.99x |
| バルク書き込み | 1.25x | 1.02x |
| 更新 | 0.11x | 0.73x |
| 削除 | 0.10x | 0.12x |

## サマリー / Summary

- **dictsqlite**: オリジナル版（ベースライン）
- **dictsqlite-fastest**: APSW使用の高速版
- **beta**: メモリ最適化版（LRUキャッシュ、バッファリング等）

### 主な発見事項 / Key Findings

1. バルク操作では dictsqlite-fastest が最も高速
2. 個別書き込みでは beta (optimized) が高いパフォーマンスを発揮
3. 混合操作では各バージョンの特性が顕著に現れる
