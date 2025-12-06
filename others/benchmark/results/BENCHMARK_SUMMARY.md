# DictSQLite 包括的ベンチマーク結果

**実行日時:** 2025-12-06 15:51:15

## 概要

3つのバージョンを徹底比較:
- **DictSQLite (Original版)**: sqlite3ベース
- **dictsqlite_v2**: Rust拡張版 (v2.0.6)
- **dictsqlite-fastest Beta v2**: APSWベース、高速化

## ベンチマーク結果

| テスト | Original (ops/sec) | dictsqlite_v2 (ops/sec) | fastest Beta v2 (ops/sec) | 最速 |
|--------|-------------------|------------------------|---------------------------|------|
| Basic Write (300 items) | 249,959 | 37,755 | 149,388 | **Original** |
| Basic Read (300 items) | 990 | 99,407 | 1,938,815 | **fastest Beta v2** |
| Bulk Insert (500 items) | 288,229 | 344,247 | 347,844 | **fastest Beta v2** |
| Mixed Operations (400 items) | 488 | 278,645 | 147,401 | **dictsqlite_v2** |

## 総合パフォーマンス

**平均スループット** (ops/sec):

- Original版: 134,916
- dictsqlite_v2版: 190,013
- fastest Beta v2版: 645,862

## 🏆 総括

**最速: fastest Beta v2版** (645,862 ops/sec)

### パフォーマンスランキング

🥇 1位. fastest Beta v2版: 645,862 ops/sec
🥈 2位. dictsqlite_v2版: 190,013 ops/sec
🥉 3位. Original版: 134,916 ops/sec
