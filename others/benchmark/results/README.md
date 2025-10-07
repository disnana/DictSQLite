# ベンチマーク結果ディレクトリ

このディレクトリには、バージョン別のベンチマーク結果が固定ファイル名で保存されます。

## ディレクトリ構造

```
results/
├── versions/              # バージョン固有の結果（Git管理）
│   ├── v1/               # Beta版 v1 の結果
│   │   ├── benchmark.csv      # CSV結果（固定ファイル名）
│   │   ├── benchmark.json     # JSON結果（固定ファイル名）
│   │   ├── summary.md         # サマリー（固定ファイル名）
│   │   ├── benchmark.log      # ログ（固定ファイル名）
│   │   └── graphs/
│   │       └── stats_summary.png  # 統計サマリー（固定ファイル名）
│   ├── v2/               # Beta版 v2 の結果
│   ├── v3/               # Beta版 v3 の結果
│   ├── v4/               # Beta版 v4 の結果
│   └── all/              # 全バージョン比較の結果
│       ├── benchmark.csv
│       ├── benchmark.json
│       ├── summary.md
│       ├── benchmark.log
│       └── graphs/
│           ├── stats_summary.png          # 統計サマリー
│           ├── comparison_ops.png         # OPS比較
│           ├── comparison_time.png        # 時間比較
│           ├── comparison_speedup.png     # スピードアップ比
│           ├── comparison_heatmap.png     # ヒートマップ
│           ├── comparison_scalability.png # スケーラビリティ
│           ├── comparison_evolution.png   # バージョン進化
│           ├── comparison_metrics.png     # 詳細メトリクス
│           └── comparison_coverage.png    # テストカバレッジ
├── comparisons/           # バージョン間比較（Git管理）
├── version_history.json   # 実行履歴（Git管理）
├── VERSION_INDEX.md       # バージョン一覧（Git管理）
└── BENCHMARK_SUMMARY.md   # 最新のサマリー（Git管理）
```

## 固定ファイル名による上書き方式

- 同じバージョンで再実行すると、該当ファイルが自動的に上書きされます
- タイムスタンプ付きのファイルは生成されません
- ファイル数が増え続けることはありません

## 結果の確認方法

### ローカル実行
```bash
cd others/benchmark

# v1として保存（統計サマリーのみ）
export BETA_VERSION=v1
python fast_comprehensive_benchmark.py

# allとして保存（統計 + 徹底比較グラフ）
export BETA_VERSION=all
python comprehensive_benchmark.py
```

### GitHub Actions
1. GitHubの「Actions」タブを開く
2. 「Performance Benchmark」を選択
3. 「Run workflow」をクリック
4. Beta版のバージョン（v1/v2/v3/v4/all）を選択して実行

## グラフの確認

- 単体テスト（v1-v4）: `results/versions/{version}/graphs/stats_summary.png`
- allテスト: `results/versions/all/graphs/` に9個のグラフファイル

## 詳細ドキュメント

- [VERSION_MANAGEMENT.md](../VERSION_MANAGEMENT.md) - バージョン管理システムの詳細
- [GRAPH_GENERATION_REPORT.md](../GRAPH_GENERATION_REPORT.md) - グラフ生成システムの詳細
- [QUICK_REFERENCE.md](../QUICK_REFERENCE.md) - クイックリファレンス
