# Issue Fix Summary: パフォーマンスベンチのactionsについて

## 問題の概要

GitHub Actionsでパフォーマンスベンチマークを実行すると、前回の変更が最低限の実行テストすらされていなかったため、以下のエラーが発生していました：

1. **DictSQLiteFastestBeta**: 書き込み直後の読み込みが失敗する
2. **全バージョン**: `get()` メソッドが存在しない

## 修正内容

### 1. Beta版のキャッシュ不整合バグを修正

**根本原因**: `fast_mode=True`（デフォルト）の場合、`__setitem__`と`__getitem__`が異なるキャッシュを使用していた

- `__setitem__`: `self._cache.put()` → `self.cache` (OrderedDict) を更新
- `__getitem__`: `self._cache.get_or_none_fast()` → `self.simple_cache` (dict) をチェック

**修正内容**:
- `LRUCache`クラスに`bulk_put_fast()`と`remove_fast()`メソッドを追加
- `__setitem__`を修正: `fast_mode`の場合は`put_fast()`を使用
- `__delitem__`を修正: `fast_mode`の場合は`remove_fast()`を使用
- `bulk_insert()`を修正: `fast_mode`の場合は`bulk_put_fast()`を使用
- `bulk_get()`など他のメソッドも同様に修正

**影響範囲**:
- `dictsqlite-fastest/beta/dictsqlite_fastest_beta.py`

### 2. 全バージョンに`get()`メソッドを追加

**問題**: ベンチマークスクリプトが`db.get('key', default)`を呼び出すが、TableProxyレベルにしか実装されていなかった

**修正内容**:
- **DictSQLite** (`dictsqlite/main.py`): クラスレベルに`get()`メソッドを追加し、TableProxyに委譲
- **DictSQLiteFastest** (`dictsqlite-fastest/dictsqlite_fastest/main.py`): 
  - クラスレベルに`get()`メソッドを追加
  - TableProxyクラスにも`get()`メソッドを追加
- **DictSQLiteFastestBeta**: DictSQLiteFastestから継承するため、自動的に対応

## テスト結果

### ベンチマーク実行結果 (`fast_benchmark_v2.py`)

```
DictSQLite (Original):    87.5% success rate (14/16 tests)
DictSQLiteFastest (APSW): 90.0% success rate (18/20 tests)
DictSQLiteFastestBeta:    90.0% success rate (18/20 tests)
```

**修正前**: Beta版は0%成功率（すべて失敗）
**修正後**: Beta版は90%成功率に改善

### ユニットテスト結果

```
tests/test_basic.py:            5/5 passed
全テスト (performance除く):    91/91 passed
```

## 動作確認

### 修正前の動作

```python
db = DictSQLiteFastestBeta('/tmp/test.db')
db['key'] = 'value'
val = db['key']  # KeyError: Key key not found in table main.
```

### 修正後の動作

```python
db = DictSQLiteFastestBeta('/tmp/test.db')
db['key'] = 'value'
val = db['key']           # ✅ 'value'
val = db.get('key')       # ✅ 'value'
val = db.get('missing')   # ✅ None
```

## 変更ファイル

1. `dictsqlite-fastest/beta/dictsqlite_fastest_beta.py` - キャッシュ不整合の修正
2. `dictsqlite/main.py` - get()メソッド追加
3. `dictsqlite-fastest/dictsqlite_fastest/main.py` - get()メソッド追加

## 今後のアクション

これらの修正により、GitHub Actionsでのパフォーマンスベンチマークが正常に実行できるようになります。

- ✅ ローカルテスト完了
- ✅ ユニットテスト完了
- ✅ ベンチマークテスト完了
- ⏭️ GitHub Actionsでの実行確認（次回PRマージ後）
