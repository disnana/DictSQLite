# 総合パフォーマンステスト使用ガイド
# Comprehensive Performance Benchmark Usage Guide

このドキュメントは、DictSQLiteの3つのバージョン（dictsqlite、dictsqlite-fastest、beta）のパフォーマンスを測定するための総合ベンチマークツールの使用方法を説明します。

This document explains how to use the comprehensive benchmark tool for measuring the performance of three DictSQLite versions (dictsqlite, dictsqlite-fastest, beta).

## 📋 必要要件 / Requirements

### Python環境
- Python 3.8以上
- 必要なパッケージ:
  - `apsw` (dictsqlite-fastestとbeta版で必要)
  - `portalocker` (dictsqliteで必要)
  - `cryptography` (dictsqliteで必要)

### インストール方法
```bash
pip install apsw portalocker cryptography
```

## 🚀 使用方法 / Usage

### 基本的な実行
```bash
cd /path/to/DictSQLite
python comprehensive_performance_benchmark.py
```

### 実行時間
通常、完全なベンチマークの実行には約1〜2分かかります。

The full benchmark typically takes 1-2 minutes to complete.

## 📊 テスト内容 / Test Coverage

このベンチマークは以下の操作をテストします:

### 1. DictSQLite (オリジナル版)
- **テストアイテム数**: 1,000件
- **テスト操作**:
  - 個別書き込み (Individual Write)
  - 個別読み込み (Individual Read)
  - バルク書き込み (Bulk Write)
  - 更新 (Update)
  - 削除 (Delete)

### 2. DictSQLite-Fastest
- **テストアイテム数**: 10,000件 (同期), 100件 (非同期)
- **同期操作**:
  - 個別書き込み
  - 個別読み込み
  - バルク書き込み
  - 更新
  - 削除
  - 混合操作 (Read/Write/Update mix)
- **非同期操作**:
  - 個別書き込み
  - 個別読み込み
  - バルク書き込み

### 3. Beta版
- **テストアイテム数**: 10,000件
- **テストモード**:
  - 通常モード
  - 最適化モード (memory_budget_mb=100)
- **同期操作**:
  - 個別書き込み (両モード)
  - 個別読み込み
  - バルク書き込み
  - 更新
  - 削除
  - 混合操作

**注意**: Beta版の非同期操作は現在パフォーマンス問題のためスキップされます。

## 📄 出力ファイル / Output Files

ベンチマーク実行後、以下のファイルが生成されます:

### 1. performance_results.csv
詳細な測定データを含むCSVファイル。スプレッドシートやデータ分析ツールで開くことができます。

**カラム構成**:
- `version`: バージョン名 (dictsqlite, dictsqlite-fastest, beta)
- `mode`: モード (sync, async)
- `operation`: 操作タイプ (individual_write, bulk_write, etc.)
- `items`: テストアイテム数
- `duration_sec`: 実行時間（秒）
- `ops`: Operations Per Second (1秒あたりの操作回数)
- `ops_formatted`: フォーマット済みOPS値
- `notes`: 追加情報 (normal_mode, optimized_mode等)

### 2. performance_summary.md
人間が読みやすい形式のMarkdownレポート。

**含まれる情報**:
- バージョン別の詳細結果テーブル
- 操作タイプ別のパフォーマンス比較
- 速度倍率サマリー
- 主な発見事項

## 📈 結果の読み方 / Interpreting Results

### OPS (Operations Per Second)
1秒あたりに実行できる操作の回数。**値が大きいほど高速**。

- `K` = 1,000 ops/s (例: 247K = 247,000 ops/s)
- `M` = 1,000,000 ops/s

### ベースライン比 (Baseline Ratio)
DictSQLite (オリジナル版) を基準 (1.0x) とした場合の相対的なパフォーマンス。

- `> 1.0x`: オリジナル版より高速
- `< 1.0x`: オリジナル版より低速
- `1.0x`: オリジナル版と同等

### 一般的な傾向

1. **個別書き込み**: Beta (optimized) が最高パフォーマンス
2. **個別読み込み**: DictSQLite-Fastest と Beta が同等の高速性能
3. **バルク操作**: DictSQLite-Fastest が最速
4. **更新・削除**: DictSQLite (オリジナル版) が高速
5. **混合操作**: Beta (optimized) が優秀

## 🔧 カスタマイズ / Customization

ベンチマークスクリプトをカスタマイズして、特定のユースケースに合わせたテストを実行できます。

### テストアイテム数の変更
```python
# スクリプト内の run_all_tests() メソッドで変更
self.test_dictsqlite_sync_write(1000)  # 1000 を任意の数値に変更
```

### 特定のテストのみ実行
```python
# main() 関数内でコメントアウト
benchmark = ComprehensiveBenchmark()
benchmark.test_fastest_sync_bulk(10000)  # 特定のテストのみ実行
benchmark.save_to_csv()
```

### 出力ファイル名の変更
```python
benchmark = ComprehensiveBenchmark(
    output_csv='my_results.csv',
    output_md='my_summary.md'
)
```

## 💡 ベストプラクティス / Best Practices

1. **複数回実行**: より正確な結果を得るために、ベンチマークを複数回実行し、平均値を取ることを推奨
2. **システムの状態**: テスト実行中は他の重い処理を避ける
3. **ディスク容量**: 十分な空き容量があることを確認（一時ファイルが作成されます）
4. **環境の一貫性**: 比較する場合は同じマシン・環境で実行

## 🐛 トラブルシューティング / Troubleshooting

### ModuleNotFoundError: No module named 'apsw'
```bash
pip install apsw
```

### 一時ファイルのクリーンアップエラー
スクリプトは自動的に一時ファイルをクリーンアップしますが、エラーが発生した場合は手動で削除できます:
```bash
# Linuxの場合
rm -rf /tmp/tmp*

# Windowsの場合
# %TEMP% フォルダを確認
```

### 非同期テストが遅い
Beta版の非同期操作は現在最適化中です。デフォルトでスキップされますが、必要に応じてコメントを外して実行できます（時間がかかります）。

## 📞 サポート / Support

問題が発生した場合や質問がある場合は、GitHubのIssueで報告してください。

For issues or questions, please report them on GitHub Issues.

---

**最終更新日 / Last Updated**: 2025-10-03
