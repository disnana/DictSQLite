# DictSQLite 包括的ベンチマーク結果

**実行日時:** 2025-12-06 14:12:50

## 概要

3つのバージョンを徹底比較:
- **DictSQLite (Original版)**: sqlite3ベース
- **dictsqlite_v2**: Rust拡張版 (v2.0.6)
- **dictsqlite-fastest Beta v2**: APSWベース、高速化

## ベンチマーク結果

| テスト | Original (ops/sec) | dictsqlite_v2 (ops/sec) | fastest Beta v2 (ops/sec) | 最速 |
|--------|-------------------|------------------------|---------------------------|------|
| Basic Write (300 items) | 250,008 | 28,513 | 157,740 | **Original** |
| Basic Read (300 items) | 869 | 524,070 | 2,104,166 | **fastest Beta v2** |
| Bulk Insert (500 items) | 286,066 | 310,551 | 338,196 | **fastest Beta v2** |
| Mixed Operations (400 items) | 465 | 253,854 | 147,078 | **dictsqlite_v2** |

## 総合パフォーマンス

**平均スループット** (ops/sec):

- Original版: 134,352
- dictsqlite_v2版: 279,247
- fastest Beta v2版: 686,795

## 🏆 総括

**最速: fastest Beta v2版** (686,795 ops/sec)

### パフォーマンスランキング

🥇 1位. fastest Beta v2版: 686,795 ops/sec
🥈 2位. dictsqlite_v2版: 279,247 ops/sec
🥉 3位. Original版: 134,352 ops/sec
