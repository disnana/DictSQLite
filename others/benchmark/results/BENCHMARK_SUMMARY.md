# DictSQLite 包括的ベンチマーク結果

**実行日時:** 2025-12-06 13:28:56

## 概要

3つのバージョンを徹底比較:
- **DictSQLite (Original版)**: sqlite3ベース
- **dictsqlite_v2**: Rust拡張版 (v2.0.6)
- **dictsqlite-fastest Beta v2**: APSWベース、高速化

## ベンチマーク結果

| テスト | Original (ops/sec) | dictsqlite_v2 (ops/sec) | fastest Beta v2 (ops/sec) | 最速 |
|--------|-------------------|------------------------|---------------------------|------|
| Basic Write (300 items) | 259,816 | 0 | 181,493 | **Original** |
| Basic Read (300 items) | 966 | 0 | 2,199,810 | **fastest Beta v2** |
| Bulk Insert (500 items) | 296,166 | 0 | 393,831 | **fastest Beta v2** |
| Mixed Operations (400 items) | 454 | 0 | 176,826 | **fastest Beta v2** |

## 総合パフォーマンス

**平均スループット** (ops/sec):

- Original版: 139,351
- fastest Beta v2版: 737,990

## 🏆 総括

**最速: fastest Beta v2版** (737,990 ops/sec)

### パフォーマンスランキング

🥇 1位. fastest Beta v2版: 737,990 ops/sec
🥈 2位. Original版: 139,351 ops/sec
