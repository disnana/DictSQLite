# DictSQLite パフォーマンステスト - README
# DictSQLite Performance Testing - README

このディレクトリには、DictSQLiteの3つのバージョンの包括的なパフォーマンステストが含まれています。

This directory contains comprehensive performance testing for three versions of DictSQLite.

---

## 🚀 クイックスタート / Quick Start

### 1. ベンチマークの実行
```bash
python comprehensive_performance_benchmark.py
```

### 2. 結果の確認
```bash
# CSV形式の詳細データ
cat performance_results.csv

# Markdown形式のレポート
cat performance_summary.md

# クイックサマリー
cat PERFORMANCE_QUICK_SUMMARY.md
```

実行時間: 約1-2分  
Runtime: Approximately 1-2 minutes

---

## 📁 ファイル構成 / File Structure

### 実行ファイル / Executable
- **`comprehensive_performance_benchmark.py`** (32KB)
  - メインベンチマークスクリプト / Main benchmark script
  - 自動テスト実行、CSV/Markdown生成 / Auto-testing, CSV/Markdown generation

### 出力ファイル / Output Files
- **`performance_results.csv`** (1.9KB)
  - 詳細な測定データ / Detailed measurement data
  - 21行のテスト結果 / 21 rows of test results
  - Excel/スプレッドシート対応 / Excel/spreadsheet compatible

- **`performance_summary.md`** (4.8KB)
  - 人間が読みやすいレポート / Human-readable report
  - バージョン別・操作別の比較 / Version and operation comparisons
  - 速度倍率テーブル / Speed multiplier tables

### ドキュメント / Documentation
- **`BENCHMARK_USAGE.md`** (6.2KB)
  - 詳細な使用方法ガイド / Detailed usage guide
  - 日本語・英語バイリンガル / Japanese & English bilingual
  - インストール、カスタマイズ、トラブルシューティング

- **`PERFORMANCE_QUICK_SUMMARY.md`** (6.6KB)
  - ビジュアル化された結果サマリー / Visual results summary
  - ユースケース別推奨 / Use case recommendations
  - シナリオベースの選択ガイド / Scenario-based selection guide

- **`IMPLEMENTATION_REPORT.md`** (7.5KB)
  - 実装完了報告書 / Implementation completion report
  - 要件チェックリスト / Requirements checklist
  - 品質保証の確認 / Quality assurance verification

---

## 🎯 テスト対象バージョン / Tested Versions

### 1. DictSQLite (オリジナル版)
- **テストアイテム数**: 1,000件
- **強み**: 更新・削除操作
- **OPS**: 303K (update), 524K (delete)

### 2. DictSQLite-Fastest
- **テストアイテム数**: 10,000件 (sync), 100件 (async)
- **強み**: 読み込み、バルク操作
- **OPS**: 61K (read, 4.04x), 438K (bulk write, 1.31x)

### 3. Beta (メモリ最適化版)
- **テストアイテム数**: 10,000件
- **強み**: 個別書き込み、混合操作
- **OPS**: 247K (write, 1.04x), 117K (mixed)

---

## 📊 主な結果 / Key Results

| 操作タイプ | 最高パフォーマンス | OPS | 倍率 |
|-----------|------------------|-----|------|
| 個別書き込み | Beta (optimized) | 247K | 1.04x |
| 個別読み込み | DictSQLite-Fastest | 61K | 4.04x |
| バルク書き込み | DictSQLite-Fastest | 438K | 1.31x |
| 更新 | DictSQLite | 303K | 1.00x |
| 削除 | DictSQLite | 524K | 1.00x |
| 混合操作 | Beta (optimized) | 117K | - |

---

## 💡 推奨ユースケース / Recommended Use Cases

### 読み取り重視のアプリ → **DictSQLite-Fastest**
- 読み込み速度が4倍
- バルク操作も高速

### 書き込み重視のアプリ → **Beta (optimized)**
- 個別書き込みが最速
- 混合ワークロードにも最適

### 更新・削除が多いアプリ → **DictSQLite (original)**
- 更新・削除が圧倒的に高速
- シンプルな依存関係

### バランス型アプリ → **Beta (optimized)**
- 総合的に高パフォーマンス
- メモリ最適化機能

---

## 🔧 必要要件 / Requirements

### Python環境
- Python 3.8以上
- 必要パッケージ:
  ```bash
  pip install apsw portalocker cryptography
  ```

### システム要件
- ディスク空き容量: 100MB以上推奨
- メモリ: 512MB以上推奨
- OS: Windows, Linux, macOS

---

## 📖 詳細ドキュメント / Detailed Documentation

各ドキュメントの詳細:

1. **使用方法**: `BENCHMARK_USAGE.md`
   - インストール手順
   - 実行方法
   - 結果の読み方
   - カスタマイズ方法

2. **結果サマリー**: `PERFORMANCE_QUICK_SUMMARY.md`
   - ビジュアル比較
   - ベストパフォーマンス一覧
   - シナリオ別ガイド

3. **実装報告**: `IMPLEMENTATION_REPORT.md`
   - 要件達成状況
   - 統計データ
   - 品質保証

---

## 🐛 トラブルシューティング / Troubleshooting

### ModuleNotFoundError
```bash
pip install apsw portalocker cryptography
```

### 実行が遅い
- 正常です（1-2分かかります）
- バックグラウンドプロセスを確認

### 一時ファイルエラー
スクリプトは自動的にクリーンアップしますが、手動削除も可能:
```bash
# Linux/Mac
rm -rf /tmp/tmp*

# Windows
# %TEMP% フォルダを確認
```

---

## 📞 サポート / Support

問題がある場合:
1. `BENCHMARK_USAGE.md` のトラブルシューティングセクションを確認
2. GitHubのIssueで報告
3. 詳細なエラーメッセージを含める

---

## 📝 カスタマイズ例 / Customization Examples

### 特定のテストのみ実行
```python
from comprehensive_performance_benchmark import ComprehensiveBenchmark

benchmark = ComprehensiveBenchmark()
benchmark.test_fastest_sync_bulk(50000)  # 50,000アイテム
benchmark.save_to_csv()
```

### 出力ファイル名変更
```python
benchmark = ComprehensiveBenchmark(
    output_csv='my_results.csv',
    output_md='my_summary.md'
)
benchmark.run_all_tests()
```

---

## 📈 継続的な改善 / Continuous Improvement

### 今後の拡張予定
- [ ] グラフ生成機能 (matplotlib)
- [ ] HTML形式レポート
- [ ] メモリ使用量測定
- [ ] 複数回実行の統計分析
- [ ] Beta版非同期操作の最適化

### 貢献方法
プルリクエストを歓迎します:
1. フォーク
2. 機能ブランチ作成
3. テスト追加
4. プルリクエスト送信

---

## ✅ 検証済み環境 / Verified Environment

- **Python**: 3.12.3
- **OS**: Linux (GitHub Actions Runner)
- **パッケージ**: apsw, portalocker, cryptography
- **実行時間**: 1-2分
- **成功率**: 100%

---

## 🎉 まとめ / Summary

このベンチマークツールにより:
- ✅ 3つのバージョンの包括的な比較
- ✅ 詳細なパフォーマンスデータ (CSV)
- ✅ わかりやすいレポート (Markdown)
- ✅ ユースケース別の推奨
- ✅ 充実したドキュメント

**適切なバージョン選択により、アプリケーションのパフォーマンスを最大化できます！**

---

**作成日**: 2025-10-03  
**バージョン**: 1.0.0  
**ステータス**: Production Ready ✅
