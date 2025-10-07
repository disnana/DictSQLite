# DictSQLite v4.2 パフォーマンス最適化ガイド

v4.2の各パラメータを最適化してパフォーマンスを最大化するための詳細ガイド

## 📋 目次

1. [パフォーマンスパラメータ概要](#パフォーマンスパラメータ概要)
2. [buffer_sizeの最適化](#buffer_sizeの最適化)
3. [hot_capacityの最適化](#hot_capacityの最適化)
4. [persist_modeの選択](#persist_modeの選択)
5. [暗号化のパフォーマンス影響](#暗号化のパフォーマンス影響)
6. [ユースケース別推奨設定](#ユースケース別推奨設定)
7. [ベンチマーク方法](#ベンチマーク方法)

---

## パフォーマンスパラメータ概要

DictSQLite v4.2には、パフォーマンスを制御する主要なパラメータがあります：

```python
DictSQLiteV4(
    db_path,                        # データベースパス
    hot_capacity=1_000_000,         # ホットティアの最大サイズ
    buffer_size=100,                # v4.2: 書き込みバッファサイズ
    persist_mode="writethrough",    # 永続化モード
    encryption_password=None,       # 暗号化パスワード
    enable_async=True,              # 非同期フラッシュ
)
```

### パラメータの影響範囲

| パラメータ | 影響する性能指標 | 推奨範囲 |
|-----------|----------------|---------|
| `buffer_size` | 書き込みスループット、レイテンシ | 50-1000 |
| `hot_capacity` | 読み込み速度、メモリ使用量 | 10,000-10,000,000 |
| `persist_mode` | 書き込み速度、データ保証 | memory/lazy/writethrough |
| `encryption_password` | 全体的な速度 | - |
| `enable_async` | バックグラウンド処理 | True/False |

---

## buffer_sizeの最適化

### 概要

`buffer_size`は、書き込みバッファに溜めるエントリ数を制御します。v4.2の最も重要な最適化ポイントです。

### 動作メカニズム

```
書き込みリクエスト → バッファに蓄積 → buffer_size到達 → まとめてフラッシュ
```

**メリット:**
- SQLトランザクション数の削減
- Mutexロック回数の削減
- ディスクI/O回数の削減

**デメリット:**
- メモリ使用量の増加
- レイテンシの増加（バッファフル時まで遅延）

### サイズ別の特性

#### 小さいbuffer_size（50-100）

**適用場面:**
- リアルタイムデータ処理
- 低レイテンシが必要
- メモリ制約がある環境

**性能特性:**
```
レイテンシ: ★★★★★ (最低)
スループット: ★★☆☆☆ (低)
メモリ使用: ★★★★★ (最小)
```

**設定例:**
```python
# リアルタイムセンサーデータ収集
db = DictSQLiteV4('sensors.db', buffer_size=50)
for reading in sensor_stream():
    db[f'sensor:{reading.id}'] = reading.to_bytes()
    # 50件ごとにフラッシュされるため、データロスが最小限
```

#### 中程度のbuffer_size（100-500）

**適用場面:**
- 汎用アプリケーション
- バランス重視
- デフォルト推奨

**性能特性:**
```
レイテンシ: ★★★☆☆ (中)
スループット: ★★★★☆ (高)
メモリ使用: ★★★☆☆ (中)
```

**設定例:**
```python
# Webアプリケーションのセッションストア
db = DictSQLiteV4('sessions.db', buffer_size=200)
```

#### 大きいbuffer_size（500-1000+）

**適用場面:**
- バッチ処理
- 最高スループット重視
- メモリに余裕がある環境

**性能特性:**
```
レイテンシ: ★☆☆☆☆ (高)
スループット: ★★★★★ (最高)
メモリ使用: ★★☆☆☆ (大)
```

**設定例:**
```python
# 大量ログデータのバッチ投入
db = DictSQLiteV4('logs.db', buffer_size=1000)
for batch in log_batches:
    for log in batch:
        db[log.id] = log.to_bytes()
# 1000件ごとにまとめてフラッシュ
```

### 最適化のヒント

1. **ワークロードを測定する**
   ```python
   import time
   
   # 異なるbuffer_sizeでテスト
   for size in [50, 100, 200, 500, 1000]:
       db = DictSQLiteV4('test.db', buffer_size=size)
       
       start = time.time()
       for i in range(10000):
           db[f'key:{i}'] = f'value_{i}'.encode('utf-8')
       elapsed = time.time() - start
       
       print(f"buffer_size={size}: {elapsed:.3f}秒, {10000/elapsed:.0f} ops/sec")
       db.close()
   ```

2. **データロス許容度を考慮**
   - クリティカルデータ: 小さいbuffer_size（50-100）
   - 一般データ: 中程度（100-200）
   - ログ/メトリクス: 大きい（500-1000）

3. **手動フラッシュの活用**
   ```python
   db = DictSQLiteV4('app.db', buffer_size=1000)
   
   # 大量書き込み
   for i in range(10000):
       db[f'key:{i}'] = f'value_{i}'.encode('utf-8')
   
   # 重要なポイントで手動フラッシュ
   db.flush()  # バッファに残っているデータを強制的に永続化
   ```

---

## hot_capacityの最適化

### 概要

`hot_capacity`は、メモリキャッシュ（ホットティア）に保持する最大エントリ数を制御します。

### 動作メカニズム

```
読み込みリクエスト → ホットティアチェック → ヒット: メモリから返す
                                        → ミス: SQLから読み込み + キャッシュ

容量超過時: LRUエビクション（最も古いエントリを削除）
```

### サイズ選択ガイド

#### データセットサイズベース

| データセット | hot_capacity推奨値 | 理由 |
|------------|------------------|------|
| 小規模（~10K） | 10,000 | 全データがメモリに載る |
| 中規模（~100K） | 100,000 | 頻繁にアクセスされるデータを保持 |
| 大規模（~1M） | 1,000,000 | ワーキングセットを保持 |
| 超大規模（1M+） | 1,000,000-5,000,000 | メモリと相談 |

#### アクセスパターンベース

**ホットデータが多い場合（80/20ルール）:**
```python
# 全データの20%に80%のアクセスが集中
total_entries = 1_000_000
hot_capacity = int(total_entries * 0.2)  # 200,000

db = DictSQLiteV4('app.db', hot_capacity=hot_capacity)
```

**均等アクセスの場合:**
```python
# メモリに応じて決定
available_memory_mb = 1024  # 1GB
entry_size_bytes = 1024     # 1KB/エントリと仮定
hot_capacity = (available_memory_mb * 1024 * 1024) // entry_size_bytes

db = DictSQLiteV4('app.db', hot_capacity=hot_capacity)
```

### パフォーマンス測定

```python
import random
import time

db = DictSQLiteV4(':memory:', hot_capacity=10_000)

# データ投入
for i in range(50_000):
    db[f'key:{i}'] = f'value_{i}'.encode('utf-8')

# ランダムアクセステスト
keys = [f'key:{random.randint(0, 49_999)}' for _ in range(10_000)]

start = time.time()
for key in keys:
    _ = db[key]
elapsed = time.time() - start

print(f"10,000回のランダムアクセス: {elapsed:.3f}秒")
print(f"スループット: {10_000/elapsed:.0f} ops/sec")

# hot_capacityを変えて比較
```

---

## persist_modeの選択

### モード比較

| モード | 永続化タイミング | 速度 | データ保証 | 用途 |
|--------|----------------|------|----------|------|
| `memory` | なし | ★★★★★ | ☆☆☆☆☆ | テスト、一時データ |
| `lazy` | 手動flush時 | ★★★★☆ | ★★☆☆☆ | バッチ処理 |
| `writethrough` | バッファフル時 | ★★★☆☆ | ★★★★★ | 本番環境 |

### 詳細

#### memory モード

**特徴:**
- ディスク書き込みなし
- メモリのみで動作
- 最速

**使用例:**
```python
# ユニットテスト
db = DictSQLiteV4(':memory:', persist_mode='memory')

# テストデータ投入
db['test_key'] = b'test_value'
assert db['test_key'] == b'test_value'

# プロセス終了時にデータは消える
```

#### lazy モード

**特徴:**
- 明示的なflush()まで永続化しない
- 高速な書き込み
- flush()忘れのリスク

**使用例:**
```python
# バッチETL処理
db = DictSQLiteV4('etl.db', persist_mode='lazy', buffer_size=1000)

try:
    # 大量データ処理
    for batch in data_batches:
        for item in batch:
            db[item.id] = item.to_bytes()
    
    # 処理完了後に永続化
    db.flush()
    print("ETL完了")
    
except Exception as e:
    print(f"エラー: {e}")
    # エラー時もflushするかはケースバイケース
    db.flush()  # または db.close()でロールバック風に扱う
```

#### writethrough モード（推奨）

**特徴:**
- バッファリング付き即座永続化
- データ保証とパフォーマンスのバランス
- 本番環境向け

**使用例:**
```python
# 本番Webアプリケーション
db = DictSQLiteV4(
    'production.db',
    persist_mode='writethrough',
    buffer_size=200
)

# 通常の書き込み
db['user:123'] = user_data
# buffer_size(200)到達時に自動フラッシュ

# アプリケーション終了時
db.close()  # 残りのバッファもフラッシュされる
```

---

## 暗号化のパフォーマンス影響

### オーバーヘッド測定

暗号化（AES-256-GCM）によるオーバーヘッドは一般的に小さいです：

```python
import time

# 暗号化なし
db_plain = DictSQLiteV4(':memory:')
start = time.time()
for i in range(10000):
    db_plain[f'key:{i}'] = f'value_{i}'.encode('utf-8')
elapsed_plain = time.time() - start

# 暗号化あり
db_encrypted = DictSQLiteV4(':memory:', encryption_password='test')
start = time.time()
for i in range(10000):
    db_encrypted[f'key:{i}'] = f'value_{i}'.encode('utf-8')
elapsed_encrypted = time.time() - start

overhead = (elapsed_encrypted - elapsed_plain) / elapsed_plain * 100
print(f"暗号化オーバーヘッド: {overhead:.1f}%")
# 一般的に5-15%程度
```

### 推奨事項

- 機密データには必ず暗号化を使用
- パフォーマンス影響は通常軽微（5-15%）
- buffer_sizeの最適化で影響を軽減可能

---

## ユースケース別推奨設定

### 1. Webアプリケーションのセッションストア

```python
db = DictSQLiteV4(
    'sessions.db',
    hot_capacity=20_000,          # アクティブセッション数の2倍
    buffer_size=200,              # バランス重視
    persist_mode='writethrough',  # データ保証
    encryption_password='...',    # セキュリティ
    enable_async=True             # バックグラウンドフラッシュ
)
```

**理由:**
- セッションは頻繁にアクセスされる → 大きなhot_capacity
- データロスは許容できない → writethrough
- 機密情報を含む → 暗号化

### 2. ログ収集システム

```python
db = DictSQLiteV4(
    'logs.db',
    buffer_size=1000,             # 大きなバッファ
    persist_mode='lazy',          # 高速書き込み
    enable_async=True             # バックグラウンド処理
)

# 定期的なフラッシュ
import threading

def periodic_flush():
    while True:
        time.sleep(60)  # 60秒ごと
        db.flush()

threading.Thread(target=periodic_flush, daemon=True).start()
```

**理由:**
- 書き込み量が多い → 大きなbuffer_size
- 若干のデータロスは許容 → lazy
- スループット重視

### 3. キャッシュストア

```python
db = DictSQLiteV4(
    ':memory:',                   # ディスク不要
    hot_capacity=1_000_000,       # 大きなキャッシュ
    persist_mode='memory'         # 永続化不要
)
```

**理由:**
- 一時データ → メモリのみ
- 高速アクセス必須 → memory mode
- 再起動時に再構築可能 → 永続化不要

### 4. データ分析・ETL

```python
db = DictSQLiteV4(
    'analytics.db',
    buffer_size=1000,             # バッチ処理向け
    persist_mode='lazy'           # 処理完了時にflush
)

# ETL処理
for batch in large_dataset:
    process_and_store(batch, db)

# 完了時にflush
db.flush()
db.close()
```

**理由:**
- 大量データ処理 → 大きなbuffer_size
- 処理完了後に永続化 → lazy

### 5. IoTデータ収集

```python
db = DictSQLiteV4(
    'iot_data.db',
    buffer_size=50,               # 小さなバッファ
    persist_mode='writethrough',  # データ保証
    hot_capacity=10_000           # 最近のデータをキャッシュ
)
```

**理由:**
- リアルタイム性重視 → 小さなbuffer_size
- データロス回避 → writethrough
- センサーデータは時系列 → 適度なキャッシュ

---

## ベンチマーク方法

### 基本的なベンチマーク

```python
import time

def benchmark_write(db, num_items=10000):
    """書き込み性能測定"""
    start = time.time()
    for i in range(num_items):
        db[f'key:{i}'] = f'value_{i}'.encode('utf-8')
    elapsed = time.time() - start
    return elapsed, num_items / elapsed

def benchmark_read(db, num_items=10000):
    """読み込み性能測定"""
    start = time.time()
    for i in range(num_items):
        _ = db[f'key:{i}']
    elapsed = time.time() - start
    return elapsed, num_items / elapsed

# 使用例
db = DictSQLiteV4(':memory:', buffer_size=200)

write_time, write_ops = benchmark_write(db)
print(f"書き込み: {write_time:.3f}秒, {write_ops:.0f} ops/sec")

read_time, read_ops = benchmark_read(db)
print(f"読み込み: {read_time:.3f}秒, {read_ops:.0f} ops/sec")
```

### 詳細なベンチマーク

examples/v4.2_performance_examples.py を参照してください。

---

## まとめ

### クイックリファレンス

| 用途 | buffer_size | hot_capacity | persist_mode |
|------|-------------|--------------|--------------|
| リアルタイム | 50-100 | データ量に応じて | writethrough |
| 汎用Web | 100-200 | 10K-100K | writethrough |
| バッチ処理 | 500-1000 | 10K-100K | lazy |
| キャッシュ | - | 大きく | memory |
| ログ収集 | 500-1000 | 小さく | lazy |

### チューニングのステップ

1. **デフォルトで開始** - `buffer_size=100`, `persist_mode=writethrough`
2. **ベンチマーク実施** - 実際のワークロードで測定
3. **パラメータ調整** - ボトルネックに応じて最適化
4. **再測定** - 改善効果を確認
5. **本番適用** - 段階的にロールアウト

詳細なサンプルコードは [examples/](./examples/) ディレクトリを参照してください。
