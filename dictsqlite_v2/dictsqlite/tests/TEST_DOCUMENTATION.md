# DictSQLite v4.2 - テストスイート ドキュメント

このファイルは、DictSQLite v4.2のテストスイートに含まれる全テストファイルの内容を記載しています。

## テスト概要

**総テストファイル数**: 29  
**テストクラス/関数**: 640+ テスト  
**最終確認**: 全テスト合格

---

## 1. 網羅的テスト（Exhaustive Tests）

今回新規作成した包括的テストスイートです。

### test_exhaustive_dictsqlite_v4.py

**対象**: `DictSQLiteV4` クラスの全メソッド

| クラス | テスト対象 |
|--------|-----------|
| `TestInitializationParameters` | 初期化パラメータ全組み合わせ |
| `TestDunderMethods` | `__getitem__`, `__setitem__`, `__delitem__`, `__contains__`, `__len__` |
| `TestAccessMethods` | `get`, `keys`, `values`, `items` |
| `TestMutationMethods` | `update`, `pop`, `setdefault`, `clear` |
| `TestStatsMethod` | `stats()` 戻り値検証 |
| `TestTableFunctionality` | `table()` メソッド、テーブル分離 |
| `TestPersistence` | `flush`, `close`, 永続化動作 |
| `TestBulkInsert` | `bulk_insert` 辞書/リスト |
| `TestIterator` | `__iter__` イテレーション |
| `TestEqualityAndRepresentation` | `__eq__`, `__repr__` |
| `TestErrorHandling` | 無効なモード時のエラー |
| `TestEncryption` | 暗号化機能 |
| `TestSafePickle` | Safe Pickle 機能 |
| `TestModesClass` | `Modes` クラス定数 |

---

### test_exhaustive_table_proxy.py

**対象**: `TableProxy` クラスの全メソッド

| クラス | テスト対象 |
|--------|-----------|
| `TestTableProxyBasicOperations` | テーブル作成、複数テーブル |
| `TestTableProxyItemAccess` | `__getitem__`, `__setitem__`, `__delitem__` |
| `TestTableProxyContainsLen` | `__contains__`, `__len__` |
| `TestTableProxyAccessMethods` | `keys`, `values`, `items` |
| `TestTableProxyGetPopSetdefault` | `get`, `pop`, `setdefault` |
| `TestTableProxyUpdateClear` | `update`, `clear` |
| `TestTableProxyIterator` | `__iter__` イテレーション |
| `TestTableProxyReprStrEq` | `__repr__`, `__str__`, `__eq__` |
| `TestTableModeDifferences` | prefix vs separate モード |
| `TestTableProxyStorageModes` | 全ストレージモード対応 |
| `TestTableProxyPersistence` | 永続化動作 |
| `TestTableProxyEdgeCases` | Unicode/絵文字キー、大量データ |

---

### test_exhaustive_async.py

**対象**: `AsyncDictSQLite` クラスの全メソッド

| クラス | テスト対象 |
|--------|-----------|
| `TestAsyncDictSQLiteInitialization` | 全モードでの初期化 |
| `TestAsyncGetSet` | `aset`, `aget` |
| `TestAsyncBatchOperations` | `abatch_set`, `abatch_get` |
| `TestAsyncContainsDelete` | `acontains`, `adelete` |
| `TestAsyncFlushClose` | `aflush`, `aclose` |
| `TestSyncMethods` | 同期ラッパーメソッド |
| `TestDictLikeInterface` | `__getitem__`, `__setitem__` |
| `TestUtilityMethods` | `stats`, `clear`, `flush`, `close` |
| `TestContextManagers` | 同期/非同期コンテキストマネージャー |
| `TestAsyncTableProxy` | `table()`, テーブル分離 |
| `TestAsyncConcurrency` | 並行読み書きテスト |
| `TestAsyncErrorHandling` | 無効モード時のエラー |
| `TestAsyncStorageModes` | bytes/pickle モード |
| `TestAsyncPersistence` | 永続化動作 |

---

### test_exhaustive_async_table_proxy.py

**対象**: `AsyncTableProxy` クラスの全メソッド

| クラス | テスト対象 |
|--------|-----------|
| `TestAsyncTableProxyBasicOperations` | テーブル作成 |
| `TestAsyncTableProxyItemAccess` | アイテムアクセス |
| `TestAsyncTableProxyContainsLen` | 包含確認、長さ |
| `TestAsyncTableProxyAccessMethods` | `keys`, `values`, `items` |
| `TestAsyncTableProxyGetPopSetdefault` | `get`, `pop`, `setdefault` |
| `TestAsyncTableProxyUpdateClear` | `update`, `clear` |
| `TestAsyncTableProxyIterator` | イテレーション |
| `TestAsyncTableProxyReprStrEq` | 表現と等価性 |
| `TestAsyncTableProxyModes` | テーブルモード |
| `TestAsyncTableProxyStorageModes` | ストレージモード |
| `TestAsyncTableProxyPersistence` | 永続化 |
| `TestAsyncTableProxyEdgeCases` | エッジケース |

---

### test_return_type_validation.py

**対象**: 全メソッドの戻り値型の厳密検証

| クラス | テスト対象 |
|--------|-----------|
| `TestBytesStorageReturnTypes` | bytes モードの型検証 |
| `TestPickleStorageReturnTypes` | pickle モードの型検証 |
| `TestJsonbStorageReturnTypes` | jsonb モードの型検証 |
| `TestJsonStorageReturnTypes` | json モードの型検証 |
| `TestKeysReturnType` | `keys()` 戻り値型 |
| `TestLenReturnType` | `len()` 戻り値型 |
| `TestContainsReturnType` | `__contains__` 戻り値型 |
| `TestStatsReturnType` | `stats()` 戻り値型 |
| `TestPopReturnType` | `pop()` 戻り値型 |
| `TestSetdefaultReturnType` | `setdefault()` 戻り値型 |
| `TestTableProxyReturnTypes` | TableProxy 戻り値型 |
| `TestAsyncReturnTypes` | AsyncDictSQLite 戻り値型 |

---

### test_boundary_edge_cases.py

**対象**: 境界条件とエッジケース

| クラス | テスト対象 |
|--------|-----------|
| `TestSpecialKeys` | 空文字列、Unicode、絵文字、長いキー |
| `TestLargeData` | 1MB+データ、10000件、大規模ネスト構造 |
| `TestDeepNesting` | 20レベルネスト（dict/list） |
| `TestMinimumCapacity` | `hot_capacity=1`, `pool_size=1` |
| `TestConcurrentAccess` | マルチスレッド読み書き |
| `TestEncryptionEdgeCases` | 暗号化エッジケース |
| `TestEmptyDatabaseOperations` | 空DBでの全操作 |
| `TestBinaryDataEdgeCases` | 全256バイト値、NULLバイト |
| `TestAsyncEdgeCases` | 高速連続書き込み |
| `TestTableEdgeCases` | 同一キー異テーブル、特殊テーブル名 |

---

## 2. 既存テストファイル

### test_basic_operations.py
基本的なCRUD操作、辞書インターフェース、コンテキストマネージャー、イテレーション、エラーハンドリング、データ永続化のテスト。

### test_comprehensive_all_functions.py
応答データの詳細検証、深いネスト構造、全関数カバレッジのテスト。

### test_async_operations.py / test_async_awaitable.py / test_async_persistence.py
AsyncDictSQLiteの非同期操作、awaitable メソッド、永続化のテスト。

### test_async_table_contains.py
AsyncTableProxyの`__contains__`操作のテスト。

### test_storage_modes.py
全ストレージモード（pickle, jsonb, json, bytes）の動作テスト。

### test_persistence_modes.py
全永続化モード（memory, lazy, writethrough）の動作テスト。

### test_table_mode.py / test_table_proxy_eq.py / test_table_proxy_repr.py
テーブルモード、TableProxyの等価性・表現のテスト。

### test_pool_size.py
接続プールサイズ設定のテスト。

### test_lru_eviction.py
LRUキャッシュのエビクション動作テスト。

### test_performance.py / test_v4.2_comprehensive_performance.py
パフォーマンスベンチマークテスト。

### test_v4_security.py
セキュリティ機能（暗号化、Safe Pickle）のテスト。

### test_jsonb_table_support.py
JSONBモードでのテーブルサポートテスト。

### test_dict_compat_api.py
Python dict互換APIのテスト。

### test_advanced_features.py
高度な機能のテスト。

### test_comprehensive_edge_cases.py / test_comprehensive_integration.py / test_comprehensive_stress.py
エッジケース、統合テスト、ストレステストの包括的テスト。

### test_issue_fixes.py
バグ修正の回帰テスト。

---

## 3. テスト実行方法

```bash
# 全テスト実行
python -m pytest tests/ -v

# 特定のファイルを実行
python -m pytest tests/test_exhaustive_dictsqlite_v4.py -v

# 特定のクラスを実行
python -m pytest tests/test_exhaustive_dictsqlite_v4.py::TestStatsMethod -v

# カバレッジ付きで実行
python -m pytest tests/ --cov=dictsqlite --cov-report=html
```

---

## 4. テストユーティリティ

### conftest.py

| ユーティリティ | 説明 |
|--------------|------|
| `windows_safe_temp_db()` | Windows対応の一時DBファイル作成・クリーンアップ |
| `cleanup_db_files()` | DBファイルとWAL/SHMファイルの削除 |

---

## 5. カバレッジサマリー

### DictSQLiteV4
- ✅ 初期化パラメータ（全モード）
- ✅ CRUD操作（`__getitem__`, `__setitem__`, `__delitem__`）
- ✅ 辞書インターフェース（`get`, `keys`, `values`, `items`）
- ✅ 変更メソッド（`update`, `pop`, `setdefault`, `clear`）
- ✅ ユーティリティ（`stats`, `flush`, `close`, `bulk_insert`）
- ✅ テーブル機能（`table`）
- ✅ コンテキストマネージャー
- ✅ 暗号化・Safe Pickle
- ✅ エラーハンドリング

### AsyncDictSQLite
- ✅ 非同期メソッド（`aget`, `aset`, `abatch_get`, `abatch_set`）
- ✅ `acontains`, `adelete`, `aflush`, `aclose`
- ✅ 同期ラッパー
- ✅ 非同期コンテキストマネージャー
- ✅ 並行処理

### TableProxy / AsyncTableProxy
- ✅ 全dict-likeインターフェース
- ✅ テーブルモード（prefix/separate）
- ✅ ストレージモード
- ✅ 永続化

### エッジケース
- ✅ 空文字列・Unicode・絵文字キー
- ✅ 大規模データ（1MB+）
- ✅ 深いネスト構造（20レベル）
- ✅ 最小キャパシティ
- ✅ 並行アクセス
- ✅ 暗号化
