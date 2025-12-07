# DictSQLite 包括的ベンチマーク結果

**実行日時:** 2025-12-07 11:43:29

## 概要

3つのバージョンを徹底比較:
- **DictSQLite (Original版)**: sqlite3ベース
- **dictsqlite_v2**: Rust拡張版 (v2.0.6)
- **dictsqlite-fastest Beta v2**: APSWベース、高速化

## ベンチマーク結果

| テスト | Original (ops/sec) | dictsqlite_v2 (ops/sec) | fastest Beta v2 (ops/sec) | 最速 |
|--------|-------------------|------------------------|---------------------------|------|
| Basic Write (300 items) | 251,658 | 37,283 | 156,446 | **Original** |
| Basic Read (300 items) | 1,207 | 746,317 | 2,104,166 | **fastest Beta v2** |
| Bulk Insert (500 items) | 295,457 | 417,676 | 351,812 | **dictsqlite_v2** |
| Mixed Operations (400 items) | 533 | 340,931 | 148,919 | **dictsqlite_v2** |

## 総合パフォーマンス

**平均スループット** (ops/sec):

- Original版: 137,214
- dictsqlite_v2版: 385,552
- fastest Beta v2版: 690,336

## 🏆 総括

**最速: fastest Beta v2版** (690,336 ops/sec)

### パフォーマンスランキング

🥇 1位. fastest Beta v2版: 690,336 ops/sec
🥈 2位. dictsqlite_v2版: 385,552 ops/sec
🥉 3位. Original版: 137,214 ops/sec
