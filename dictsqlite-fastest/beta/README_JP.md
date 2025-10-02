# DictSQLite-Fastest Beta - メモリ最優先最適化版

## 概要

DictSQLite-Fastest Betaは、ディスクアクセスを最小限に抑え、メモリからのアクセスを最大化することで最高のパフォーマンスを実現するベータ版です。

## 主な最適化戦略

### 1. LRUキャッシュ
- 最も頻繁にアクセスされるデータをメモリに保持
- デフォルトで10,000アイテムをキャッシュ
- スレッドセーフな実装
- キャッシュヒット率の統計情報を提供
- **新機能**: `bulk_put()`メソッドで高速なバッチキャッシュ更新

### 2. 書き込みバッファリング（遅延書き込み）
- 小さな書き込みをメモリに蓄積
- 一定量または一定時間経過後に一括でディスクに書き込み
- ディスクI/Oの回数を大幅に削減
- **新機能**: 大きなバルク操作（100件以上）は直接書き込みでパフォーマンス維持

### 3. アグレッシブなメモリPRAGMA設定
- `cache_size`: 256MB（デフォルト）
- `mmap_size`: 1GB（デフォルト）
- `journal_mode`: WAL（Write-Ahead Logging）
- `temp_store`: MEMORY
- `locking_mode`: EXCLUSIVE
- **新機能**: `synchronous`: NORMAL（WALモードでの最適化）
- **新機能**: `wal_autocheckpoint`: 10000ページ（メモリ効率の改善）

### 4. 先読みキャッシング
- `prefetch_keys()`メソッドで関連データを事前にキャッシュ
- バルク操作を使用した効率的な読み込み
- **新機能**: `bulk_prefetch(key_pattern, limit)`でパターンマッチング先読み

### 5. メモリオンリーモード（オプション）
- 完全にメモリ内で動作（ディスク書き込みなし）
- 最高速度を実現
- 一時的なデータ処理に最適

### 6. 自動チューニング（新機能）
- アクセスパターンに基づいてキャッシュサイズを自動調整
- キャッシュヒット率が50%未満の場合、キャッシュを拡大
- キャッシュヒット率が95%以上の場合、メモリを節約するためキャッシュを縮小
- 10,000操作ごとに自動的に実行

### 7. WALチェックポイント最適化（新機能）
- `_optimize_wal_checkpoint()`メソッドで明示的にWALチェックポイントを実行
- メモリ使用量を最適化し、WALファイルの肥大化を防止

## インストール

```bash
# 既存のDictSQLite-Fastestがインストールされている環境で動作します
cd dictsqlite-fastest/beta
```

## 使用方法

### 基本的な使用方法

```python
from beta.dictsqlite_fastest_beta import DictSQLiteFastestBeta

# 通常モード（ディスクベース + メモリキャッシュ）
with DictSQLiteFastestBeta('data.db', cache_capacity=10000) as db:
    # データの書き込み（バッファに蓄積）
    db['user_1'] = {'name': '田中太郎', 'age': 30}
    db['user_2'] = {'name': '佐藤花子', 'age': 25}
    
    # データの読み込み（キャッシュ優先）
    user = db['user_1']
    print(user)  # {'name': '田中太郎', 'age': 30}
    
    # 明示的にディスクに書き込む
    db.flush()
```

### メモリオンリーモード（最高速）

```python
# メモリオンリーモード - ディスク書き込みなし
with DictSQLiteFastestBeta(':memory:', memory_only=True) as db:
    # すべてメモリ内で動作
    db['temp_data'] = 'temporary value'
    result = db['temp_data']
    
    # このデータベースは閉じると消えます
```

### カスタム設定

```python
# カスタム設定で最適化
db = DictSQLiteFastestBeta(
    'custom.db',
    cache_capacity=50000,        # LRUキャッシュ容量を拡大
    write_buffer_size=5000,      # バッファサイズを拡大
    write_buffer_interval=10.0,  # フラッシュ間隔を延長
    aggressive_memory=True       # アグレッシブなメモリ設定
)

# 大量データの処理
data = {f'key_{i}': f'value_{i}' for i in range(100000)}
db.bulk_insert(data)

# 保留中のデータをフラッシュ
db.flush()

# 統計情報の確認
stats = db.get_beta_stats()
print(f"キャッシュヒット率: {stats['cache']['hit_rate']:.2f}%")
print(f"ディスク読み込み: {stats['operations']['disk_reads']}")
print(f"ディスク書き込み: {stats['operations']['disk_writes']}")
print(f"バッファフラッシュ: {stats['operations']['buffer_flushes']}")

db.close()
```

### 先読みキャッシング

```python
# アクセスパターンに基づいて事前にデータをキャッシュ
with DictSQLiteFastestBeta('data.db') as db:
    # 関連するキーを事前にキャッシュに読み込む
    related_keys = ['user_1', 'user_2', 'user_3', 'user_4', 'user_5']
    db.prefetch_keys(related_keys)
    
    # これらのキーへのアクセスはキャッシュから高速に取得される
    for key in related_keys:
        user = db[key]
        process_user(user)
    
    # 新機能: パターンマッチングで一括プリフェッチ
    db.bulk_prefetch('user_%', limit=100)  # user_で始まるキーを100件プリフェッチ
```

### バルク操作の活用

```python
with DictSQLiteFastestBeta('bulk.db') as db:
    # バルク挿入（大きなバルク操作は自動的に直接書き込みで高速化）
    data = {f'item_{i}': {'value': i} for i in range(10000)}
    db.bulk_insert(data)  # 100件以上は直接ディスクに書き込み
    
    # バルク取得（キャッシュ優先）
    keys = [f'item_{i}' for i in range(0, 1000, 10)]
    results = db.bulk_get(keys)
    
    # 最後にフラッシュ（WALチェックポイントも実行）
    db.flush()
```

### パフォーマンス統計の活用（新機能）

```python
with DictSQLiteFastestBeta('stats.db') as db:
    # データ操作
    for i in range(1000):
        db[f'key_{i}'] = f'value_{i}'
    
    # 詳細な統計情報を取得
    stats = db.get_beta_stats()
    
    # キャッシュ統計
    print(f"キャッシュヒット率: {stats['cache']['hit_rate']:.2f}%")
    print(f"キャッシュサイズ: {stats['cache']['size']}/{stats['cache']['capacity']}")
    
    # 操作統計
    print(f"ディスク読み込み: {stats['operations']['disk_reads']}")
    print(f"ディスク書き込み: {stats['operations']['disk_writes']}")
    print(f"バッファフラッシュ: {stats['operations']['buffer_flushes']}")
    
    # パフォーマンス指標（新機能）
    print(f"キャッシュ効率: {stats['performance']['cache_effectiveness']:.2%}")
    print(f"ディスク削減率: {stats['performance']['disk_savings_rate']:.2%}")
    print(f"総操作数: {stats['performance']['total_operations']}")
```

## 統計情報の活用

```python
with DictSQLiteFastestBeta('stats.db') as db:
    # データ操作
    for i in range(1000):
        db[f'key_{i}'] = f'value_{i}'
    
    # 統計情報を取得
    stats = db.get_beta_stats()
    
    print("=== キャッシュ統計 ===")
    print(f"サイズ: {stats['cache']['size']}/{stats['cache']['capacity']}")
    print(f"ヒット: {stats['cache']['hits']}")
    print(f"ミス: {stats['cache']['misses']}")
    print(f"ヒット率: {stats['cache']['hit_rate']:.2f}%")
    
    print("\n=== 操作統計 ===")
    print(f"キャッシュヒット: {stats['operations']['cache_hits']}")
    print(f"キャッシュミス: {stats['operations']['cache_misses']}")
    print(f"ディスク読み込み: {stats['operations']['disk_reads']}")
    print(f"ディスク書き込み: {stats['operations']['disk_writes']}")
    print(f"バッファフラッシュ: {stats['operations']['buffer_flushes']}")
    
    if stats['buffer']:
        print("\n=== バッファ状態 ===")
        print(f"保留中の書き込み: {stats['buffer']['pending_writes']}")
        print(f"保留中の削除: {stats['buffer']['pending_deletes']}")
```

## パフォーマンスチューニング

### シナリオ1: 読み込み中心のワークロード

```python
# 大きなキャッシュ、少ない書き込みバッファ
db = DictSQLiteFastestBeta(
    'read_heavy.db',
    cache_capacity=100000,      # 大きなキャッシュ
    write_buffer_size=100,      # 小さなバッファ（すぐに書き込む）
    write_buffer_interval=1.0   # 短い間隔
)
```

### シナリオ2: 書き込み中心のワークロード

```python
# 大きなバッファ、長いフラッシュ間隔
db = DictSQLiteFastestBeta(
    'write_heavy.db',
    cache_capacity=10000,        # 適度なキャッシュ
    write_buffer_size=10000,     # 大きなバッファ
    write_buffer_interval=30.0   # 長い間隔
)
```

### シナリオ3: 一時データ処理

```python
# メモリオンリーモード
db = DictSQLiteFastestBeta(':memory:', memory_only=True)
# 最高速、ディスクI/Oなし
```

## ベンチマーク（予想）

DictSQLite-Fastest標準版と比較した場合の期待される性能向上:

| 操作タイプ | 標準版 | Beta版 | 改善率 |
|-----------|--------|--------|--------|
| キャッシュヒット時の読み込み | 0.001s | 0.00001s | **100x** |
| キャッシュミス時の読み込み | 0.001s | 0.0011s | 0.9x (オーバーヘッド) |
| 小さな書き込み（バッファあり） | 0.001s | 0.00001s | **100x** |
| バルク書き込み | 0.1s | 0.05s | **2x** |
| メモリオンリーモード | N/A | 0.000001s | **極めて高速** |

注: 実際の性能は使用パターンとデータサイズに依存します。

## 注意事項

### データ永続性

- **書き込みバッファリング**: デフォルトでは書き込みがバッファに蓄積されるため、`flush()`または`close()`を呼び出す前にプロセスがクラッシュするとデータが失われる可能性があります
- **メモリオンリーモード**: データベースを閉じるとすべてのデータが失われます

### メモリ使用量

- LRUキャッシュとバッファによりメモリ使用量が増加します
- `cache_capacity`と`write_buffer_size`を適切に設定してください

### スレッドセーフティ

- LRUキャッシュと書き込みバッファはスレッドセーフです
- 複数スレッドからの同時アクセスが可能です

## ベストプラクティス

1. **コンテキストマネージャの使用**: 自動的にフラッシュと閉じる処理が行われます
   ```python
   with DictSQLiteFastestBeta('data.db') as db:
       # 操作
       pass
   # 自動的にflush()とclose()が呼ばれます
   ```

2. **定期的なフラッシュ**: 長時間動作するアプリケーションでは定期的に`flush()`を呼び出してください
   ```python
   for i, batch in enumerate(large_dataset):
       db.bulk_insert(batch)
       if i % 10 == 0:  # 10バッチごとにフラッシュ
           db.flush()
   ```

3. **統計情報の監視**: `get_beta_stats()`でキャッシュヒット率を監視し、設定を調整してください

4. **先読みの活用**: アクセスパターンが予測可能な場合は`prefetch_keys()`を使用してください

## トラブルシューティング

### メモリ使用量が多すぎる

```python
# キャッシュサイズを削減
db = DictSQLiteFastestBeta('data.db', cache_capacity=1000)
```

### データが失われた

```python
# より頻繁にフラッシュ
db = DictSQLiteFastestBeta(
    'data.db',
    write_buffer_interval=1.0  # 1秒ごとにフラッシュ
)
```

### パフォーマンスが期待より低い

```python
# 統計情報を確認
stats = db.get_beta_stats()
if stats['cache']['hit_rate'] < 50:
    # キャッシュヒット率が低い場合、キャッシュサイズを増やす
    db.clear_cache()
    db = DictSQLiteFastestBeta('data.db', cache_capacity=50000)
```

## まとめ

DictSQLite-Fastest Betaは、メモリ最優先のアーキテクチャにより、通常版よりもさらに高速なパフォーマンスを実現します。適切な設定により、特定のワークロードで劇的な性能向上が期待できます。

ベータ版のため、本番環境での使用前に十分なテストを行ってください。
