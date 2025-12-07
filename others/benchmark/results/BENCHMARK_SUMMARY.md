# DictSQLite 包括的ベンチマーク結果

**実行日時:** 2025-12-07 11:11:48

## 概要

3つのバージョンを徹底比較:
- **DictSQLite (Original版)**: sqlite3ベース
- **dictsqlite_v2**: Rust拡張版 (v2.0.6)
- **dictsqlite-fastest Beta v2**: APSWベース、高速化

## ベンチマーク結果

| テスト | Original (ops/sec) | dictsqlite_v2 (ops/sec) | fastest Beta v2 (ops/sec) | 最速 |
|--------|-------------------|------------------------|---------------------------|------|
| Basic Write (300 items) | 253,944 | 37,407 | 158,976 | **Original** |
| Basic Read (300 items) | 943 | 591,302 | 2,143,597 | **fastest Beta v2** |
| Bulk Insert (500 items) | 278,358 | 360,273 | 339,675 | **dictsqlite_v2** |
| Mixed Operations (400 items) | 389 | 294,131 | 150,414 | **dictsqlite_v2** |

## 総合パフォーマンス

**平均スループット** (ops/sec):

- Original版: 133,408
- dictsqlite_v2版: 320,778
- fastest Beta v2版: 698,165

## 🏆 総括

**最速: fastest Beta v2版** (698,165 ops/sec)

### パフォーマンスランキング

🥇 1位. fastest Beta v2版: 698,165 ops/sec
🥈 2位. dictsqlite_v2版: 320,778 ops/sec
🥉 3位. Original版: 133,408 ops/sec
