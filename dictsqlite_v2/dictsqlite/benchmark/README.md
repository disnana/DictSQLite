# DictSQLite Benchmark Suite

パフォーマンス測定とグラフ分析ツール

## 使い方

### 1. ベンチマーク実行
```bash
cd benchmark
python benchmark_all.py --profile quick
```

`--profile` は3段階です。

| profile | 用途 |
|---------|------|
| `quick` | CIや修正後のスモーク確認向け |
| `full` | ローカルでの通常比較向け |
| `stress` | 大きいサイズ・大量件数・高並行の確認向け |

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
| `benchmark_by_batch_size.png` | バッチサイズ/件数別性能 |
| `benchmark_p95_latency.png` | p95レイテンシ |
| `benchmark_category_comparison.png` | カテゴリ別総合比較 |

## テスト対象

- DictSQLiteV4: get, set, batch_get, batch_set, flush, delete, clear
- AsyncDictSQLite: get, set, batch_get, batch_set, flush
- TableProxy / AsyncTableProxy: prefix/separate mode の get, set, contains
- persist_mode: memory, lazy, writethrough
- storage_mode: bytes, json, jsonb, pickle
- cold read: 新しいインスタンスからのストレージ読み込み
- threaded access: 複数スレッドでの混合 get/set

## 測定軸

- `data_size`: 値のサイズ
- `batch_size`: 一括処理の件数、または対象レコード数
- `scenario`: hot read/write、cold storage read、table mode、threaded などの測定条件
- `p95_time_ms`: 外れ値に強いレイテンシ確認用
