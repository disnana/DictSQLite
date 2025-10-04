# 非同期版データベースロック問題の修正について

## 問題の概要

AsyncDictSQLiteFastestBeta で並行処理を行う際に、深刻なデータベースロック問題が発生していました：

- 複数の非同期操作を同時実行すると `apsw.BusyError: database is locked` エラーが発生
- バルク操作（bulk_insert、bulk_get）が実行できない
- 並行度が高い環境では安定して動作しない

## 根本原因

1. **不適切なExecutor管理**
   - `self._executor = None` により、各 `run_in_executor` 呼び出しで新しい ThreadPoolExecutor が作成されていた
   - 複数のスレッドが同時に同じ SQLite データベースにアクセスし、ロックが発生

2. **EXCLUSIVE locking mode**
   - `aggressive_memory=True` の設定により、EXCLUSIVE locking mode が有効化
   - 一度接続がロックを取得すると、他の接続がアクセスできなくなる

3. **自動フラッシュの競合**
   - 書き込みバッファの自動フラッシュが、バルク操作と競合
   - 複数のトランザクションが同時に開始され、デッドロックが発生

## 修正内容

### 1. Queue-based 操作シリアライゼーション

```python
# 非同期操作用のQueue（データベースロック問題を解決）
self._operation_queue = asyncio.Queue()
self._worker_task = asyncio.create_task(self._process_operations())
```

すべてのデータベース操作を `asyncio.Queue` を通じてシリアライズし、順次実行することで、並行アクセスによるロックを防止します。

### 2. 永続的な ThreadPoolExecutor

```python
from concurrent.futures import ThreadPoolExecutor
self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="AsyncDB")
```

シングルスレッドの永続的な Executor を使用し、すべての DB 操作が同じスレッド（= 同じ thread-local 接続）で実行されるようにします。

### 3. NORMAL locking mode への変更

```python
# 非同期モードでは排他ロックを無効化
aggressive_memory = False  # EXCLUSIVEロックが設定されない

# 手動でメモリ最適化設定を適用（EXCLUSIVEロック以外）
custom_pragma = {
    'temp_store': 'MEMORY',
    'locking_mode': 'NORMAL',  # EXCLUSIVEではなくNORMAL
    'synchronous': 'NORMAL',
    'wal_autocheckpoint': 10000,
}
```

EXCLUSIVE locking mode を無効化し、NORMAL mode を使用することで、複数の接続が共存できるようにします。

### 4. 自動フラッシュの無効化

```python
# 非同期モードでは、自動フラッシュを完全に無効化
self._sync_db._write_buffer.flush_threshold = 1000000  # 事実上無制限
```

書き込みバッファの自動フラッシュを無効化し、明示的な `aflush()` 呼び出しのみを許可します。

### 5. バルク操作前の明示的フラッシュ

```python
async def abulk_insert(self, items: dict) -> None:
    # 先にバッファをフラッシュしてからバルク挿入
    if self._sync_db._write_buffer.has_pending():
        await self._execute_in_queue(self._sync_db.flush)
    
    # ディスクへの書き込みはキュー経由で実行
    await self._execute_in_queue(self._sync_db.bulk_insert, items)
```

バルク操作の前にバッファを明示的にフラッシュし、トランザクションの競合を防止します。

## テスト結果

### 並行処理ストレステスト - すべて成功 ✅

| テスト項目 | 操作数 | 結果 |
|-----------|--------|------|
| 並行書き込み | 100 concurrent | ✅ PASS |
| 並行読み込み | 100 concurrent | ✅ PASS |
| 混合操作 | 200 concurrent | ✅ PASS |
| バルク挿入 | 10 concurrent (各100件) | ✅ PASS |
| 高並行度 | 500 concurrent | ✅ PASS |
| 並行削除 | 50 concurrent | ✅ PASS |
| フラッシュ付き | 100 writes + flush | ✅ PASS |

### 既存テスト - すべて成功 ✅

- **28 tests** in test_beta.py - ALL PASSING
- **7 new stress tests** - ALL PASSING

## パフォーマンスへの影響

### メリット
- ✅ データベースロック問題が完全に解決
- ✅ 並行処理が安定して動作
- ✅ キャッシュヒットにより読み込みは高速
- ✅ Queue-based approach により、オペレーションの順序が保証される

### トレードオフ
- ⚠️ 操作がシリアライズされるため、真の並列実行はできない
  - ただし、非同期インターフェースは維持されるため、ブロッキングはしない
  - I/O待機中に他の処理を実行可能（asyncioの利点）
- ⚠️ NORMAL locking mode のため、EXCLUSIVE mode よりわずかにオーバーヘッドがある
  - しかし、並行処理可能という利点がはるかに大きい

## 使用上の注意

### 推奨される使用パターン

```python
async def example():
    async with AsyncDictSQLiteFastestBeta('data.db') as db:
        # 複数の操作を同時に発行可能
        tasks = [
            db.aset('key1', 'value1'),
            db.aset('key2', 'value2'),
            db.aget('key3'),
        ]
        await asyncio.gather(*tasks)
        
        # バルク操作も問題なし
        await db.abulk_insert({'key4': 'value4', 'key5': 'value5'})
```

### 同期版との使い分け

- **同期版（DictSQLiteFastestBeta）**:
  - 単一スレッドでのバッチ処理
  - 最高のスループットが必要な場合
  - シンプルなスクリプトやバックグラウンドジョブ

- **非同期版（AsyncDictSQLiteFastestBeta）**:
  - Webアプリケーション（FastAPI、aiohttp など）
  - マルチクライアント対応が必要な場合
  - レスポンシブネスが重要な場合
  - 複数のI/O操作を効率的に処理したい場合

## まとめ

Queue-based 操作シリアライゼーションと NORMAL locking mode の採用により、AsyncDictSQLiteFastestBeta のデータベースロック問題を完全に解決しました。これにより、非同期版は並行処理環境で安定して動作し、Webアプリケーションやマルチクライアント環境での使用に最適化されました。
