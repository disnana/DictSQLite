# ベンチマークグラフ機能について

## 概要

ベンチマークスクリプトにグラフ生成機能が追加されました。実行後、自動的にパフォーマンス比較グラフが生成されます。

## グラフ生成されるベンチマーク

### 1. `dictsqlite-fastest/benchmark.py`
DictSQLite (オリジナル) vs DictSQLite-Fastest の比較ベンチマーク

**生成されるグラフ:**
- `ops_comparison.png` - OPS (Operations Per Second) 比較
- `speedup_comparison.png` - スピードアップ倍率

**実行方法:**
```bash
cd dictsqlite-fastest
python benchmark.py
```

**出力先:**
```
dictsqlite-fastest/benchmark_results/
  ├── benchmark_YYYYMMDD_HHMMSS.csv
  └── graphs/
      ├── ops_comparison.png
      └── speedup_comparison.png
```

### 2. `others/benchmark/comprehensive_benchmark.py`
DictSQLite (オリジナル) vs DictSQLite-Fastest vs DictSQLite-Fastest Beta の3バージョン比較

**生成されるグラフ:**
- OPS比較グラフ
- 実行時間比較グラフ  
- スピードアップ比グラフ
- パフォーマンスヒートマップ
- 操作タイプ別パフォーマンス
- スケーラビリティグラフ
- 総合ダッシュボード

**実行方法:**
```bash
cd others/benchmark
python comprehensive_benchmark.py
```

**出力先:**
```
others/benchmark/results/
  ├── benchmark_YYYYMMDD_HHMMSS.csv
  ├── benchmark_YYYYMMDD_HHMMSS.json
  ├── benchmark_summary_YYYYMMDD_HHMMSS.md
  └── graphs/
      ├── 1_ops_comparison_YYYYMMDD_HHMMSS.png
      ├── 2_time_comparison_YYYYMMDD_HHMMSS.png
      ├── 3_speedup_ratio_YYYYMMDD_HHMMSS.png
      ├── 4_performance_heatmap_YYYYMMDD_HHMMSS.png
      ├── 5_performance_by_operation_YYYYMMDD_HHMMSS.png
      ├── 6_scalability_YYYYMMDD_HHMMSS.png
      └── 7_dashboard_YYYYMMDD_HHMMSS.png
```

## 必要なライブラリ

グラフ生成には以下のライブラリが必要です：

```bash
pip install matplotlib seaborn plotly pandas numpy
```

ライブラリがインストールされていない場合は、グラフ生成をスキップして警告を表示します。

## グラフの自動生成について

- CSV/JSON/サマリーレポート生成後、自動的にグラフを生成します
- グラフ生成に失敗しても、ベンチマーク自体は正常に完了します
- エラーメッセージで問題を確認できます

## 個別にグラフ生成する場合

既存のCSVファイルからグラフを生成する場合:

```bash
cd others/benchmark
python visualize_benchmark.py results/benchmark_YYYYMMDD_HHMMSS.csv
```

または、最新のCSVファイルを自動選択:

```bash
python visualize_benchmark.py
```

## トラブルシューティング

### グラフが生成されない

1. **matplotlibがインストールされているか確認**
   ```bash
   pip list | grep matplotlib
   ```

2. **日本語フォントの問題**
   - Windows: Yu Gothic, Meiryo などが利用可能
   - macOS: Hiragino Sans などが利用可能
   - Linux: Noto Sans CJK JP などをインストール

3. **エラーメッセージを確認**
   ```
   ⚠ グラフ生成中にエラーが発生: [エラー内容]
   ```

### グラフファイルが空

`graphs/` ディレクトリ内を確認してください:
```bash
ls -lh others/benchmark/results/graphs/
ls -lh dictsqlite-fastest/benchmark_results/graphs/
```

## 今後の改善予定

- [ ] インタラクティブなHTMLグラフ (Plotly)
- [ ] リアルタイムプログレスバー付きグラフ
- [ ] 比較レポートPDF自動生成
- [ ] テストスイート実行時の自動グラフ生成
