# DictSQLite 包括的ベンチマーク結果

**実行日時:** 2025-12-06 13:50:57

## 概要

3つのバージョンを徹底比較:
- **DictSQLite (Original版)**: sqlite3ベース
- **dictsqlite_v2**: Rust拡張版 (v2.0.6)
- **dictsqlite-fastest Beta v2**: APSWベース、高速化

## ベンチマーク結果

| テスト | Original (ops/sec) | dictsqlite_v2 (ops/sec) | fastest Beta v2 (ops/sec) | 最速 |
|--------|-------------------|------------------------|---------------------------|------|
| Basic Write (300 items) | 0 | 27,213 | 0 | **dictsqlite_v2** |
| Basic Read (300 items) | 0 | 499,322 | 0 | **dictsqlite_v2** |
| Bulk Insert (500 items) | 0 | 299,166 | 0 | **dictsqlite_v2** |
| Mixed Operations (400 items) | 0 | 253,012 | 0 | **dictsqlite_v2** |

## 総合パフォーマンス

**平均スループット** (ops/sec):

- dictsqlite_v2版: 269,678

## 🏆 総括

**最速: dictsqlite_v2版** (269,678 ops/sec)

### パフォーマンスランキング

🥇 1位. dictsqlite_v2版: 269,678 ops/sec
