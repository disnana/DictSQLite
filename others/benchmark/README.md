# ベンチマーク構成

このディレクトリには、DictSQLiteのベンチマーク関連ファイルが含まれています。

## 📁 ディレクトリ構造

```
others/benchmark/
├── README.md                          # このファイル
├── BENCHMARK_README.md                # ベンチマークの詳細説明
├── comprehensive_benchmark.py         # 包括的ベンチマーク（全機能版）
├── fast_comprehensive_benchmark.py    # 高速版ベンチマーク（推奨）
├── test_simple_benchmark.py           # 簡易テスト用ベンチマーク
├── visualize_benchmark.py             # グラフ生成ツール
└── results/                           # ベンチマーク結果の出力先
    ├── README.md                      # 結果ディレクトリの説明
    ├── benchmark_*.csv                # CSV形式の結果
    ├── benchmark_*.json               # JSON形式の結果
    ├── benchmark_*.log                # 実行ログ
    ├── BENCHMARK_SUMMARY.md           # サマリー
    └── graphs/                        # 生成されたグラフ
        ├── *.png                      # PNG画像
        └── *.html                     # インタラクティブHTML
```

## 🚀 実行方法

### ローカルでの実行

```bash
# ディレクトリに移動
cd others/benchmark

# 高速版ベンチマークの実行（推奨）
python fast_comprehensive_benchmark.py

# 結果のグラフ化（自動的に最新のCSVを使用）
python visualize_benchmark.py

# または、特定のCSVファイルを指定
python visualize_benchmark.py results/benchmark_20241004_120000.csv
```

### GitHub Actionsでの実行

1. GitHubリポジトリの「Actions」タブを開く
2. 「Performance Benchmark」ワークフローを選択
3. 「Run workflow」ボタンをクリック
4. 実行完了後、「Artifacts」セクションから結果をダウンロード

## 📊 ベンチマーク内容

### 比較対象
- **DictSQLite** (オリジナル版)
- **DictSQLite-Fastest** (APSW使用版)
- **DictSQLite-Fastest Beta** (メモリ最適化版)

### テスト項目
- 基本操作（読み書き、更新、削除）
- バルク操作
- 非同期操作
- 複雑なデータ構造
- トランザクション処理
- 並行処理

## 📈 結果の確認

結果は以下の形式で出力されます：

1. **CSV**: データ分析用の数値データ
2. **JSON**: 詳細な実行情報
3. **Markdown**: 人間が読みやすいサマリー
4. **PNG/HTML**: 視覚的なグラフ

## ⚠️ 注意事項

- ベンチマークは負荷が大きいため、GitHub Actionsでは手動実行のみ許可されています
- ローカル実行時は十分なリソース（CPU、メモリ）を確保してください
- 結果ファイルは`.gitignore`に含まれており、リポジトリにコミットされません

## 🔧 要件

必要なパッケージ：
```bash
pip install matplotlib seaborn pandas numpy plotly kaleido apsw zstandard
```

## 📝 結果の解釈

- **OPS (Operations Per Second)**: 高いほど高速
- **実行時間**: 短いほど高速
- **メモリ使用量**: 少ないほど効率的
- **スループット**: 高いほど優秀

詳細な解釈方法は `BENCHMARK_README.md` を参照してください。
