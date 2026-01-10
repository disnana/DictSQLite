# DictSQLite 包括的ベンチマーク結果

**実行日時:** 2025-12-07 12:25:05
**実行日時:** 2025-12-07 11:11:48

## 概要

3つのバージョンを徹底比較:
- **DictSQLite (Original版)**: sqlite3ベース
- **dictsqlite_v2**: Rust拡張版 (v2.0.6)
- **dictsqlite-fastest Beta v2**: APSWベース、高速化

## ベンチマーク結果

| テスト | Original (ops/sec) | dictsqlite_v2 (ops/sec) | fastest Beta v2 (ops/sec) | 最速 |
|--------|-------------------|------------------------|---------------------------|------|
| Basic Write (300 items) | 249,611 | 36,402 | 157,129 | **Original** |
| Basic Read (300 items) | 1,195 | 724,405 | 2,143,597 | **fastest Beta v2** |
| Bulk Insert (500 items) | 286,262 | 406,977 | 355,932 | **dictsqlite_v2** |
| Mixed Operations (400 items) | 590 | 337,570 | 150,387 | **dictsqlite_v2** |

## 総合パフォーマンス

**平均スループット** (ops/sec):

- Original版: 134,414
- dictsqlite_v2版: 376,338
- fastest Beta v2版: 701,761

## 🏆 総括

**最速: fastest Beta v2版** (701,761 ops/sec)

### パフォーマンスランキング

🥇 1位. fastest Beta v2版: 701,761 ops/sec
🥈 2位. dictsqlite_v2版: 376,338 ops/sec
🥉 3位. Original版: 134,414 ops/sec
