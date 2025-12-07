# DictSQLite 包括的ベンチマーク結果

**実行日時:** 2025-12-06 17:22:41

## 概要

3つのバージョンを徹底比較:
- **DictSQLite (Original版)**: sqlite3ベース
- **dictsqlite_v2**: Rust拡張版 (v2.0.6)
- **dictsqlite-fastest Beta v2**: APSWベース、高速化

## ベンチマーク結果

| テスト | Original (ops/sec) | dictsqlite_v2 (ops/sec) | fastest Beta v2 (ops/sec) | 最速 |
|--------|-------------------|------------------------|---------------------------|------|
| Basic Write (300 items) | 254,354 | 36,044 | 157,523 | **Original** |
| Basic Read (300 items) | 795 | 585,524 | 2,162,012 | **fastest Beta v2** |
| Bulk Insert (500 items) | 291,555 | 311,058 | 358,733 | **fastest Beta v2** |
| Mixed Operations (400 items) | 349 | 301,261 | 151,857 | **dictsqlite_v2** |

## 総合パフォーマンス

**平均スループット** (ops/sec):

- Original版: 136,763
- dictsqlite_v2版: 308,472
- fastest Beta v2版: 707,531

## 🏆 総括

**最速: fastest Beta v2版** (707,531 ops/sec)

### パフォーマンスランキング

🥇 1位. fastest Beta v2版: 707,531 ops/sec
🥈 2位. dictsqlite_v2版: 308,472 ops/sec
🥉 3位. Original版: 136,763 ops/sec
