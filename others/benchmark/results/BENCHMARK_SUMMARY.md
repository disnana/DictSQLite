# DictSQLite 包括的ベンチマーク結果

**実行日時:** 2025-12-07 11:48:20

## 概要

3つのバージョンを徹底比較:
- **DictSQLite (Original版)**: sqlite3ベース
- **dictsqlite_v2**: Rust拡張版 (v2.0.6)
- **dictsqlite-fastest Beta v2**: APSWベース、高速化

## ベンチマーク結果

| テスト | Original (ops/sec) | dictsqlite_v2 (ops/sec) | fastest Beta v2 (ops/sec) | 最速 |
|--------|-------------------|------------------------|---------------------------|------|
| Basic Write (300 items) | 254,303 | 39,571 | 161,319 | **Original** |
| Basic Read (300 items) | 843 | 708,497 | 2,158,304 | **fastest Beta v2** |
| Bulk Insert (500 items) | 285,366 | 406,977 | 355,510 | **dictsqlite_v2** |
| Mixed Operations (400 items) | 390 | 343,092 | 150,861 | **dictsqlite_v2** |

## 総合パフォーマンス

**平均スループット** (ops/sec):

- Original版: 135,226
- dictsqlite_v2版: 374,534
- fastest Beta v2版: 706,498

## 🏆 総括

**最速: fastest Beta v2版** (706,498 ops/sec)

### パフォーマンスランキング

🥇 1位. fastest Beta v2版: 706,498 ops/sec
🥈 2位. dictsqlite_v2版: 374,534 ops/sec
🥉 3位. Original版: 135,226 ops/sec
