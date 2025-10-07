# DictSQLite v2.0 使用ガイド

## 目次

1. [基本的な使い方](#基本的な使い方)
2. [セキュリティ機能](#セキュリティ機能)
3. [パフォーマンス最適化](#パフォーマンス最適化)
4. [高度な使用例](#高度な使用例)
5. [API リファレンス](#apiリファレンス)

## 基本的な使い方

### インストール

```bash
# 基本パッケージ
pip install portalocker

# セキュリティ機能を使う場合
pip install cryptography
```

### シンプルな例

```python
from dictsqlite_v2 import DictSQLiteV2

# データベースを作成
db = DictSQLiteV2("mydata.db")

# 辞書のように使う
db['user:1'] = {'name': 'Alice', 'age': 30}
db['user:2'] = {'name': 'Bob', 'age': 25}

# データを取得
print(db['user:1'])  # {'name': 'Alice', 'age': 30}

# イテレーション
for key in db.keys():
    print(f"{key}: {db[key]}")

# クリーンアップ
db.close()
```

### コンテキストマネージャー

```python
# 自動的にcloseされる
with DictSQLiteV2("mydata.db") as db:
    db['data'] = 'value'
    print(db['data'])
# ここで自動的にcloseされる
```

## セキュリティ機能

### AES-256暗号化

機密データを保護するために暗号化を使用：

```python
from dictsqlite_v2 import DictSQLiteV2

# 暗号化を有効にしてDBを作成
db = DictSQLiteV2(
    "secure.db",
    encryption_password="YourSuperSecurePassword123!"
)

# 通常通り使用（自動的に暗号化/復号化）
db['api_key'] = 'sk-1234567890abcdef'
db['credentials'] = {
    'username': 'admin',
    'password': 'secret123'
}

# データは暗号化されて保存される
print(db['api_key'])  # 'sk-1234567890abcdef'（復号化済み）

db.close()
```

**注意**: パスワードを紛失すると、データを復元できません！

### Safe Pickle（安全なデシリアライゼーション）

信頼できないデータからの保護：

```python
from dictsqlite_v2 import DictSQLiteV2

# Safe pickleを有効化
db = DictSQLiteV2(
    "safe.db",
    use_safe_pickle=True
)

# 基本的なデータ型のみ許可
db['safe_data'] = [1, 2, 3, 4, 5]
db['safe_dict'] = {'a': 1, 'b': 2}

# 危険なオブジェクトは拒否される
db.close()
```

### カスタムSafe Pickleポリシー

```python
from dictsqlite_v2 import DictSQLiteV2, SafePolicy

# カスタムポリシーを作成
policy = SafePolicy(
    allowed_module_prefixes=('myapp', 'mylib'),  # 自分のモジュールを許可
    allowed_builtins=('int', 'str', 'list', 'dict', 'tuple'),  # 許可する型
    allow_classes_from_prefixes=True,  # クラスを許可
    allow_functions_from_prefixes=False  # 関数は拒否
)

db = DictSQLiteV2(
    "custom_safe.db",
    use_safe_pickle=True,
    safe_pickle_policy=policy
)
```

### 暗号化 + Safe Pickleの組み合わせ

最大限のセキュリティ：

```python
db = DictSQLiteV2(
    "ultra_secure.db",
    encryption_password="MySecurePassword",
    use_safe_pickle=True
)

# 完全にセキュアなストレージ
db['sensitive_data'] = {'credit_card': '****-****-****-1234'}
```

## パフォーマンス最適化

### 同期間隔の調整

```python
# 頻繁に書き込む場合は短い間隔
db = DictSQLiteV2(
    "frequent.db",
    sync_interval=0.5  # 0.5秒ごとに同期
)

# あまり書き込まない場合は長い間隔
db = DictSQLiteV2(
    "infrequent.db",
    sync_interval=5.0  # 5秒ごとに同期
)
```

### バルク操作

大量のデータを挿入する場合：

```python
db = DictSQLiteV2("bulk.db")

# 個別に挿入（遅い）
for i in range(10000):
    db[f'key_{i}'] = f'value_{i}'

# バルク挿入（超高速: 22M+ ops/sec）
data = {f'key_{i}': f'value_{i}' for i in range(10000)}
db.bulk_insert(data)

db.close()
```

### 手動同期

```python
db = DictSQLiteV2(
    "manual.db",
    auto_sync=False  # 自動同期を無効化
)

# データを書き込む
db['key1'] = 'value1'
db['key2'] = 'value2'

# 手動で同期
db.sync()  # または db.flush()

db.close()
```

## 高度な使用例

### パフォーマンス統計の取得

```python
db = DictSQLiteV2(
    "stats.db",
    encryption_password="password"
)

# 統計情報を取得
stats = db.get_performance_stats()
print(stats)

# 出力例:
# {
#     'version': '2.0.1-ultra',
#     'implementation': 'ultra-fast-memory',
#     'cache_size': 100,
#     'dirty_count': 10,
#     'db_name': 'stats.db',
#     'table_name': 'main',
#     'security': {
#         'encryption_enabled': True,
#         'safe_pickle_enabled': False
#     },
#     'performance': {
#         'write_ops_per_sec': '1.3M+',
#         'read_ops_per_sec': '2.2M+',
#         'bulk_ops_per_sec': '4.9M+',
#         'note': 'With encryption: ~20-30% slower but still fast'
#     }
# }
```

### マルチスレッド使用

```python
import threading
from dictsqlite_v2 import DictSQLiteV2

db = DictSQLiteV2("threaded.db")

def worker(worker_id):
    for i in range(1000):
        db[f'worker_{worker_id}_item_{i}'] = f'value_{i}'

# 複数のスレッドで同時に書き込み
threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
for t in threads:
    t.start()
for t in threads:
    t.join()

print(f"Total items: {len(db)}")
db.close()
```

### カスタムテーブル名

```python
# 複数のテーブルを使用
users_db = DictSQLiteV2("myapp.db", table_name="users")
settings_db = DictSQLiteV2("myapp.db", table_name="settings")

users_db['user:1'] = {'name': 'Alice'}
settings_db['theme'] = 'dark'

users_db.close()
settings_db.close()
```

## APIリファレンス

### DictSQLiteV2クラス

#### コンストラクタ

```python
DictSQLiteV2(
    db_name: str,                           # データベースファイル名
    table_name: str = 'main',               # テーブル名
    sync_interval: float = 1.0,             # 同期間隔（秒）
    auto_sync: bool = True,                 # 自動同期の有効化
    encryption_password: Optional[str] = None,  # 暗号化パスワード
    use_safe_pickle: bool = False,          # Safe pickleの有効化
    safe_pickle_policy: Optional[SafePolicy] = None  # カスタムポリシー
)
```

#### メソッド

##### 基本操作

- `db[key]` - 値を取得
- `db[key] = value` - 値を設定
- `del db[key]` - キーを削除
- `key in db` - キーの存在確認
- `len(db)` - アイテム数を取得

##### 辞書メソッド

- `db.keys()` - 全キーを取得
- `db.values()` - 全値を取得
- `db.items()` - 全アイテムを取得
- `db.get(key, default=None)` - デフォルト値付きで取得

##### バルク操作

- `db.bulk_insert(data: dict)` - 一括挿入
- `db.update_many(data: dict)` - 一括更新（bulk_insertのエイリアス）

##### 同期操作

- `db.sync()` - ディスクに強制同期
- `db.flush()` - syncのエイリアス
- `db.close()` - データベースを閉じる

##### ユーティリティ

- `db.get_performance_stats()` - パフォーマンス統計を取得

### パフォーマンス特性

| 操作 | 性能 | 備考 |
|------|------|------|
| 単発書き込み | 1.5M ops/sec | メモリ書き込み |
| 単発読み込み | 2.1M ops/sec | メモリ読み込み |
| バルク書き込み | 22M ops/sec | 超高速 |
| 更新 | 1.6M ops/sec | メモリ更新 |
| 削除 | 1.9M ops/sec | メモリ削除 |

**暗号化使用時**: 約70-80%の性能（それでも1M+ ops/sec）

## ベストプラクティス

### 1. パスワード管理

```python
import os

# 環境変数からパスワードを取得
password = os.environ.get('DB_PASSWORD')

db = DictSQLiteV2(
    "secure.db",
    encryption_password=password
)
```

### 2. エラーハンドリング

```python
try:
    db = DictSQLiteV2("mydata.db")
    db['key'] = 'value'
except KeyError as e:
    print(f"Key not found: {e}")
except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()
```

### 3. コンテキストマネージャーの使用

```python
# 推奨: 自動的にcloseされる
with DictSQLiteV2("mydata.db") as db:
    db['key'] = 'value'
```

### 4. 大量データの処理

```python
# バルク操作を使用
data = {}
for i in range(100000):
    data[f'key_{i}'] = f'value_{i}'

with DictSQLiteV2("large.db") as db:
    db.bulk_insert(data)  # 超高速
```

## トラブルシューティング

### Q: 暗号化したDBが開けない

A: パスワードが正しいか確認してください。パスワードを紛失した場合、復元はできません。

### Q: パフォーマンスが遅い

A: 
1. 暗号化を使用していませんか？（20-30%の遅延）
2. バルク操作を使用していますか？
3. sync_intervalを調整してみてください

### Q: メモリ使用量が多い

A: 全データをメモリに保持する設計です。大規模データセットには向きません（将来のLRUキャッシュ実装を待つ）。

## まとめ

DictSQLite v2.0は、高速性とセキュリティを両立した強力なツールです。

**利点**:
- 🚀 超高速（1M+ ops/sec）
- 🔒 セキュア（AES-256暗号化）
- 🎯 シンプル（dict-like API）
- 🔧 柔軟（カスタマイズ可能）

**使いどころ**:
- キャッシュストレージ
- セッション管理
- 設定ファイル
- 一時データ保存
- プロトタイピング

**向かないケース**:
- 巨大なデータセット（GB級）
- リアルタイム同期が必要
- 複雑なクエリが必要

---

**詳細情報**: `PERFORMANCE_ANALYSIS_JP.md`  
**実装レポート**: `IMPLEMENTATION_REPORT_JP.md`  
**バージョン**: v2.0.1
