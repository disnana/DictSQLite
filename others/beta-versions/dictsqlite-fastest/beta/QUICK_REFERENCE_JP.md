# DictSQLite-Fastest Beta クイックリファレンス

## 新機能一覧（2024年12月）

### 1. メモリ予算の指定
```python
db = DictSQLiteFastestBeta('data.db', memory_budget_mb=512)
```
- メモリ使用量を明示的に制御
- キャッシュとバッファサイズを自動計算

### 2. 小容量DBの自動ロード
```python
db = DictSQLiteFastestBeta('data.db', auto_load_threshold_mb=10.0)
```
- 10MB以下のDBは起動時に全データをメモリロード
- 100%キャッシュヒット率

### 3. バックグラウンド自動フラッシュ
```python
db = DictSQLiteFastestBeta('data.db', enable_background_flush=True)
```
- メインスレッドをブロックせずに自動フラッシュ
- デフォルトで有効

### 4. ホットデータ検出
```python
db = DictSQLiteFastestBeta('data.db', enable_hot_data_detection=True)
```
- 頻繁にアクセスされるデータを自動検出
- 関連データを自動先読み
- デフォルトで有効

### 5. 非同期操作
```python
async with AsyncDictSQLiteFastestBeta('data.db', memory_budget_mb=256) as db:
    await db.aset('key', 'value')
    value = await db.aget('key')
```
- 全機能を非同期インターフェースで提供

## 推奨設定

### 小容量DB（< 10MB）
```python
db = DictSQLiteFastestBeta(
    'small.db',
    memory_budget_mb=50,
    auto_load_threshold_mb=10.0
)
```

### 中容量DB（10MB - 1GB）
```python
db = DictSQLiteFastestBeta(
    'medium.db',
    memory_budget_mb=256,
    auto_load_threshold_mb=50.0,
    enable_hot_data_detection=True
)
```

### 大容量DB（> 1GB）
```python
db = DictSQLiteFastestBeta(
    'large.db',
    memory_budget_mb=1024,
    auto_load_threshold_mb=0,  # 自動ロードなし
    enable_hot_data_detection=True,
    write_buffer_interval=10.0
)
```

## 統計情報の確認

```python
stats = db.get_beta_stats()

# 基本統計
print(f"キャッシュヒット率: {stats['cache']['hit_rate']:.2f}%")
print(f"ディスク削減率: {stats['performance']['disk_savings_rate']:.2%}")

# 新機能の統計
print(f"自動プリロード数: {stats['operations']['auto_preloads']}")
print(f"ホットキー数: {stats['hot_data']['hot_keys_count']}")
print(f"バッファフラッシュ回数: {stats['operations']['buffer_flushes']}")
```

## パラメータ一覧

| パラメータ | 型 | デフォルト | 説明 |
|-----------|---|-----------|------|
| `memory_budget_mb` | int/None | None | メモリ予算（MB）。自動でキャッシュとバッファサイズを計算 |
| `auto_load_threshold_mb` | float | 10.0 | この容量以下のDBは起動時に全ロード |
| `enable_background_flush` | bool | True | バックグラウンド自動フラッシュを有効化 |
| `enable_hot_data_detection` | bool | True | ホットデータ検出と自動プリフェッチを有効化 |
| `cache_capacity` | int | 10000 | LRUキャッシュの容量（アイテム数） |
| `write_buffer_size` | int | 1000 | 書き込みバッファのサイズ |
| `write_buffer_interval` | float | 5.0 | バッファの自動フラッシュ間隔（秒） |

## ベストプラクティス

1. **コンテキストマネージャを使用**
```python
with DictSQLiteFastestBeta('data.db', memory_budget_mb=256) as db:
    db['key'] = 'value'
# 自動的にflushとcloseが呼ばれる
```

2. **統計情報を監視**
```python
stats = db.get_beta_stats()
if stats['cache']['hit_rate'] < 50:
    # キャッシュサイズを増やす
    pass
```

3. **メモリ予算を設定**
```python
# 利用可能なメモリの50%以下を推奨
db = DictSQLiteFastestBeta('data.db', memory_budget_mb=512)
```

## トラブルシューティング

### メモリ使用量が多い
→ `memory_budget_mb` を減らす

### パフォーマンスが低い
→ 統計情報を確認し、`cache_capacity` を増やす

### データが失われた
→ `write_buffer_interval` を短くする、または明示的に `flush()` を呼ぶ

## ドキュメント

- **README_JP.md** - 基本的な使い方
- **IMPROVEMENTS_2024_JP.md** - 詳細な機能説明と使用例
- **COMPLETION_REPORT_JP.md** - プロジェクト完成報告
- **demo_new_features_2024.py** - 実用的なデモ

## サンプルコード

### すべての新機能を使った例
```python
from dictsqlite_fastest_beta import DictSQLiteFastestBeta

with DictSQLiteFastestBeta(
    'mydata.db',
    memory_budget_mb=256,          # メモリ予算
    auto_load_threshold_mb=10.0,   # 小容量は自動ロード
    enable_background_flush=True,  # 自動フラッシュ
    enable_hot_data_detection=True # ホットデータ検出
) as db:
    # データ操作
    db['user_1'] = {'name': 'Alice', 'age': 30}
    db['user_2'] = {'name': 'Bob', 'age': 25}
    
    # 頻繁にアクセス（ホットキーに）
    for _ in range(15):
        user = db['user_1']
    
    # 統計確認
    stats = db.get_beta_stats()
    print(f"キャッシュヒット率: {stats['cache']['hit_rate']:.2f}%")
    print(f"ホットキー数: {stats['hot_data']['hot_keys_count']}")
```

---

**バージョン**: DictSQLite-Fastest Beta v2.0
**更新日**: 2024年12月
