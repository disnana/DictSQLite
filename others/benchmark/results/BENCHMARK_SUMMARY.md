# DictSQLite 包括的ベンチマーク結果

**実行日時:** 2025-12-07 10:16:13

## 概要

3つのバージョンを徹底比較:
- **DictSQLite (Original版)**: sqlite3ベース
- **dictsqlite_v2**: Rust拡張版 (v2.0.6)
- **dictsqlite-fastest Beta v2**: APSWベース、高速化

## ベンチマーク結果

| テスト | Original (ops/sec) | dictsqlite_v2 (ops/sec) | fastest Beta v2 (ops/sec) | 最速 |
|--------|-------------------|------------------------|---------------------------|------|
| Basic Write (300 items) | 258,482 | 37,309 | 156,855 | **Original** |
| Basic Read (300 items) | 828 | 565,524 | 2,150,925 | **fastest Beta v2** |
| Bulk Insert (500 items) | 288,705 | 355,449 | 358,978 | **fastest Beta v2** |
| Mixed Operations (400 items) | 376 | 298,846 | 146,949 | **dictsqlite_v2** |

## 総合パフォーマンス

**平均スループット** (ops/sec):

- Original版: 137,098
- dictsqlite_v2版: 314,282
- fastest Beta v2版: 703,427

## 🏆 総括

**最速: fastest Beta v2版** (703,427 ops/sec)

### パフォーマンスランキング

🥇 1位. fastest Beta v2版: 703,427 ops/sec
🥈 2位. dictsqlite_v2版: 314,282 ops/sec
🥉 3位. Original版: 137,098 ops/sec
