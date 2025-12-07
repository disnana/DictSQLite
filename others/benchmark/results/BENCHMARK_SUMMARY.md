# DictSQLite 包括的ベンチマーク結果

**実行日時:** 2025-12-07 11:22:52

## 概要

3つのバージョンを徹底比較:
- **DictSQLite (Original版)**: sqlite3ベース
- **dictsqlite_v2**: Rust拡張版 (v2.0.6)
- **dictsqlite-fastest Beta v2**: APSWベース、高速化

## ベンチマーク結果

| テスト | Original (ops/sec) | dictsqlite_v2 (ops/sec) | fastest Beta v2 (ops/sec) | 最速 |
|--------|-------------------|------------------------|---------------------------|------|
| Basic Write (300 items) | 248,871 | 37,229 | 154,429 | **Original** |
| Basic Read (300 items) | 1,262 | 660,174 | 2,143,597 | **fastest Beta v2** |
| Bulk Insert (500 items) | 290,384 | 415,278 | 346,008 | **dictsqlite_v2** |
| Mixed Operations (400 items) | 607 | 347,498 | 142,397 | **dictsqlite_v2** |

## 総合パフォーマンス

**平均スループット** (ops/sec):

- Original版: 135,281
- dictsqlite_v2版: 365,045
- fastest Beta v2版: 696,608

## 🏆 総括

**最速: fastest Beta v2版** (696,608 ops/sec)

### パフォーマンスランキング

🥇 1位. fastest Beta v2版: 696,608 ops/sec
🥈 2位. dictsqlite_v2版: 365,045 ops/sec
🥉 3位. Original版: 135,281 ops/sec
