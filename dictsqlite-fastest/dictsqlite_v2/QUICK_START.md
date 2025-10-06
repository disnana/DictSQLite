# DictSQLite-v2.0 クイックスタート

## インストール

```bash
cd dictsqlite-fastest/dictsqlite_v2
pip install -r requirements.txt
```

## 5分でわかる使い方

### 1. 基本的な操作 (30秒)

```python
from dictsqlite_v2 import DictSQLiteV2

# データベースを開く
db = DictSQLiteV2('mydata.db', write_buffer_size=1)

# 書き込み
db['user:1'] = {'name': 'Alice', 'age': 30}
db['user:2'] = {'name': 'Bob', 'age': 25}

# 読み込み
print(db['user:1'])  # {'name': 'Alice', 'age': 30}

# 確認
print('user:1' in db)  # True
print(len(db))  # 2

# 閉じる
db.close()
```

### 2. バルク操作 (1分)

```python
db = DictSQLiteV2('bulk.db', write_buffer_size=1)

# 大量データを一括挿入
data = {f'key_{i}': f'value_{i}' for i in range(10000)}
db.bulk_insert(data)

print(f"Total: {len(db)}")  # 10000
db.close()
```

### 3. パフォーマンス測定 (2分)

```python
from dictsqlite_v2.benchmarks import run_benchmark
from dictsqlite_v2.utils import format_ops

# ベンチマーク実行
results = run_benchmark(DictSQLiteV2, 'bench.db', num_items=1000)

print(f"Write: {format_ops(results['write_ops'])}")
print(f"Read:  {format_ops(results['read_ops'])}")
print(f"Bulk:  {format_ops(results['bulk_write_ops'])}")
```

### 4. ベースライン管理 (1.5分)

```python
from dictsqlite_v2.benchmarks import PerformanceBaseline
from pathlib import Path

# ベースライン保存
baseline = PerformanceBaseline(Path('baseline.json'))
baseline.save_baseline(results)

# 後で比較
new_results = run_benchmark(DictSQLiteV2, 'bench.db', num_items=1000)
comparison = baseline.compare(new_results, threshold=0.01)

if comparison['has_regression']:
    print("⚠️ Performance regression!")
else:
    print("✅ No regression")
```

## テストの実行

```bash
# 全テスト実行
pytest tests/ -v

# パフォーマンステストのみ
pytest tests/test_performance.py -v

# 特定のテスト
pytest tests/test_core.py::TestDictSQLiteV2Core::test_basic_operations -v
```

## ベンチマークの実行

```bash
python run_benchmark.py
```

出力例:
```
======================================================================
DictSQLite-v2.0 ベンチマーク
======================================================================

[1/3] ベンチマーク実行中...

結果:
  書き込み速度: 271.41K ops/s
  読み込み速度: 63.25K ops/s
  バルク書き込み: 446.73K ops/s

[2/3] ベースライン保存...
  ✓ ベースライン保存: reports/current_baseline.json

[3/3] 履歴追加...
  ✓ 履歴追加: reports/performance_history.json

======================================================================
✅ ベンチマーク完了!
======================================================================
```

## 使用例の実行

```bash
python examples.py
```

## よくある質問

### Q: write_buffer_size とは？
A: 書き込みをバッファリングするサイズです。`write_buffer_size=1` で即座にディスクに書き込みます。

### Q: テストが失敗する
A: `write_buffer_size=1` を使用しているか確認してください。

### Q: パフォーマンスが目標に達しない
A: ベースラインと比較して、回帰がないか確認してください。

### Q: ドキュメントはどこ？
A: 
- `README.md` - 基本ガイド
- `IMPLEMENTATION_REPORT.md` - 実装詳細
- `DESIGN_DECISIONS.md` - 設計判断
- `examples.py` - 実行可能な例

## 次のステップ

1. **テストを実行**: `pytest tests/ -v`
2. **ベンチマークを実行**: `python run_benchmark.py`
3. **例を実行**: `python examples.py`
4. **ドキュメントを読む**: `README.md`, `DESIGN_DECISIONS.md`
5. **独自のコードを書く**

## サポート

- 問題が発生した場合は、GitHubのIssueを作成してください
- ドキュメントを確認してください
- テストを参考にしてください
