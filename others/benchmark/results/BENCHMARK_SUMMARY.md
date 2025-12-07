# DictSQLite 包括的ベンチマーク結果

**実行日時:** 2025-12-07 10:42:38

## 概要

3つのバージョンを徹底比較:
- **DictSQLite (Original版)**: sqlite3ベース
- **dictsqlite_v2**: Rust拡張版 (v2.0.6)
- **dictsqlite-fastest Beta v2**: APSWベース、高速化

## ベンチマーク結果

| テスト | Original (ops/sec) | dictsqlite_v2 (ops/sec) | fastest Beta v2 (ops/sec) | 最速 |
|--------|-------------------|------------------------|---------------------------|------|
| Basic Write (300 items) | 249,265 | 34,450 | 128,096 | **Original** |
| Basic Read (300 items) | 1,159 | 673,964 | 1,805,296 | **fastest Beta v2** |
| Bulk Insert (500 items) | 277,585 | 392,431 | 327,526 | **dictsqlite_v2** |
| Mixed Operations (400 items) | 568 | 333,080 | 121,865 | **dictsqlite_v2** |

## 総合パフォーマンス

**平均スループット** (ops/sec):

- Original版: 132,144
- dictsqlite_v2版: 358,481
- fastest Beta v2版: 595,696

## 🏆 総括

**最速: fastest Beta v2版** (595,696 ops/sec)

### パフォーマンスランキング

🥇 1位. fastest Beta v2版: 595,696 ops/sec
🥈 2位. dictsqlite_v2版: 358,481 ops/sec
🥉 3位. Original版: 132,144 ops/sec
