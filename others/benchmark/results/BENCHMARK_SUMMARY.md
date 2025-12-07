# DictSQLite 包括的ベンチマーク結果

**実行日時:** 2025-12-07 12:01:00

## 概要

3つのバージョンを徹底比較:
- **DictSQLite (Original版)**: sqlite3ベース
- **dictsqlite_v2**: Rust拡張版 (v2.0.6)
- **dictsqlite-fastest Beta v2**: APSWベース、高速化

## ベンチマーク結果

| テスト | Original (ops/sec) | dictsqlite_v2 (ops/sec) | fastest Beta v2 (ops/sec) | 最速 |
|--------|-------------------|------------------------|---------------------------|------|
| Basic Write (300 items) | 252,011 | 36,883 | 154,354 | **Original** |
| Basic Read (300 items) | 1,024 | 673,243 | 2,139,951 | **fastest Beta v2** |
| Bulk Insert (500 items) | 284,900 | 408,802 | 357,084 | **dictsqlite_v2** |
| Mixed Operations (400 items) | 456 | 337,027 | 149,224 | **dictsqlite_v2** |

## 総合パフォーマンス

**平均スループット** (ops/sec):

- Original版: 134,598
- dictsqlite_v2版: 363,989
- fastest Beta v2版: 700,153

## 🏆 総括

**最速: fastest Beta v2版** (700,153 ops/sec)

### パフォーマンスランキング

🥇 1位. fastest Beta v2版: 700,153 ops/sec
🥈 2位. dictsqlite_v2版: 363,989 ops/sec
🥉 3位. Original版: 134,598 ops/sec
