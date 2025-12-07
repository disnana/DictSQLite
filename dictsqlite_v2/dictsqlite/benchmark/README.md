# DictSQLite Benchmark Suite

パフォーマンス測定とグラフ分析ツール

## 使い方

### 1. ベンチマーク実行
```bash
cd benchmark
python benchmark_all.py
```

### 2. グラフ生成
```bash
python analyze_results.py
```

## 出力ファイル

| ファイル | 説明 |
|----------|------|
| `benchmark_results.csv` | 性能結果データ（固定名） |
| `benchmark_ops_per_sec.png` | 操作/秒比較グラフ |
| `benchmark_avg_latency.png` | 平均レイテンシグラフ |
| `benchmark_by_data_size.png` | データサイズ別性能 |
| `benchmark_category_comparison.png` | カテゴリ別総合比較 |

## テスト対象

- DictSQLiteV4: get, set, batch_get, batch_set
- AsyncDictSQLite: get, set, batch_get, batch_set
- TableProxy: get, set
