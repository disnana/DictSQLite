# DictSQLite-v2.0

最高性能を目指す統合版 - Dictsqlite-FastestとBeta版の最良部分を統合し、継続的なパフォーマンス最適化を実現する自律開発システム。

## 概要

DictSQLite-v2.0は、以下の特徴を持つ高性能なSQLiteラッパーです：

- **最高性能**: DictSQLite-FastestとBeta版の最適化技術を統合
- **自律的改善**: ベンチマークベースの継続的な最適化
- **完全テスト**: 包括的なテストスイートによる品質保証
- **ベースライン管理**: パフォーマンス回帰の自動検出

## ディレクトリ構造

```
dictsqlite-v2/
├── __init__.py              # パッケージ初期化
├── core.py                  # コア実装（同期版・非同期版）
├── optimizations.py         # 最適化手法（LRUキャッシュ、書き込みバッファ）
├── utils.py                 # ユーティリティ関数
├── benchmarks.py            # ベンチマークとベースライン管理
├── tests/                   # テストスイート
│   ├── __init__.py
│   ├── conftest.py          # pytest設定
│   ├── test_core.py         # コア機能テスト
│   ├── test_performance.py  # パフォーマンステスト
│   ├── test_edge_cases.py   # エッジケーステスト
│   └── test_integration.py  # 統合テスト
├── reports/                 # レポート格納
│   ├── performance_history.json  # パフォーマンス履歴
│   ├── optimization_log.md       # 最適化ログ
│   └── current_baseline.json     # 現在のベースライン
└── README.md                # このファイル
```

## インストール

```bash
cd dictsqlite-fastest/dictsqlite-v2
pip install -r requirements.txt
```

## 基本的な使い方

### 同期版

```python
from dictsqlite_v2 import DictSQLiteV2

# 基本的な使い方
with DictSQLiteV2('mydata.db') as db:
    # 書き込み
    db['key1'] = 'value1'
    db['user:1'] = {'name': 'Alice', 'age': 30}
    
    # 読み込み
    print(db['key1'])  # 'value1'
    print(db['user:1'])  # {'name': 'Alice', 'age': 30}
    
    # バルク操作
    data = {f'key_{i}': f'value_{i}' for i in range(1000)}
    db.bulk_insert(data)
```

### 最適化オプション

```python
db = DictSQLiteV2(
    'mydata.db',
    cache_capacity=10000,           # キャッシュ容量
    write_buffer_size=1000,         # 書き込みバッファサイズ
    memory_budget_mb=256,           # メモリ予算
    enable_background_flush=True,   # バックグラウンドフラッシュ
    enable_hot_data_detection=True, # ホットデータ検出
)
```

### パフォーマンス統計

```python
stats = db.get_performance_stats()
print(f"Version: {stats['version']}")
print(f"Cache hit rate: {stats['cache']['hit_rate']:.2f}%")
print(f"Cache size: {stats['cache']['size']}/{stats['cache']['capacity']}")
```

## テストの実行

```bash
# 全テスト実行
pytest tests/ -v

# パフォーマンステストのみ
pytest tests/test_performance.py -v --benchmark-only

# カバレッジ付き
pytest tests/ --cov=. --cov-report=html
```

## ベンチマーク

```python
from dictsqlite_v2.benchmarks import run_benchmark, PerformanceBaseline
from pathlib import Path

# ベンチマーク実行
results = run_benchmark(DictSQLiteV2, 'benchmark.db', num_items=1000)
print(f"Write ops/s: {results['write_ops']:.2f}")
print(f"Read ops/s: {results['read_ops']:.2f}")
print(f"Bulk write ops/s: {results['bulk_write_ops']:.2f}")

# ベースライン管理
baseline = PerformanceBaseline(Path('reports/current_baseline.json'))
baseline.save_baseline(results)

# 比較
new_results = run_benchmark(DictSQLiteV2, 'benchmark.db', num_items=1000)
comparison = baseline.compare(new_results)

if comparison['has_regression']:
    print("⚠️ Performance regression detected!")
    for reg in comparison['regressions']:
        print(f"  {reg['name']}: {reg['change_pct']:.2f}% worse")
```

## 主な機能

### 1. LRUキャッシュ
頻繁にアクセスされるデータをメモリに保持し、ディスクアクセスを削減。

### 2. 書き込みバッファ
書き込み操作をバッファリングし、一括でディスクに書き込むことで性能向上。

### 3. バックグラウンド自動フラッシュ
定期的にバッファを自動フラッシュし、データ損失リスクを低減。

### 4. ホットデータ検出
頻繁にアクセスされるデータを自動検出し、キャッシュに優先的に保持。

### 5. パフォーマンス回帰検出
ベースラインとの比較により、1%以上の性能悪化を自動検出。

## パフォーマンス目標

- **書き込み**: 10,000+ ops/sec
- **読み込み**: 15,000+ ops/sec  
- **バルク書き込み**: 20,000+ ops/sec
- **キャッシュヒット率**: 80%+
- **回帰許容**: 1%未満

## 開発

### テスト追加

新しいテストを追加する場合は、`tests/` ディレクトリに配置してください。

### 最適化の追加

新しい最適化手法は `optimizations.py` に追加し、必ずベンチマークで効果を測定してください。

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## バージョン履歴

### v2.0.0 (2024-10-06)
- 初期リリース
- DictSQLite-FastestとBeta版の統合
- 包括的なテストスイート
- ベースライン管理機能
- パフォーマンス回帰検出
