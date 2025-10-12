# DictSQLite v2 包括的テストスイート

## 概要

dictsqlite_v2/dictsqlite/testsフォルダには、DictSQLite v4.2の包括的なテストスイートが含まれています。
このドキュメントでは、基本機能から高度な機能まで、同期・非同期の両方を徹底的にテストする新しいテストファイルについて説明します。

## 新規追加テストファイル

### 1. test_basic_operations.py - 基本操作テスト（10クラス、約50テスト）

基本的な機能を網羅的にテストします：

#### TestBasicCRUD
- **test_create_and_read**: 作成と読み取りのテスト
- **test_update**: 値の更新テスト
- **test_delete**: キーの削除テスト
- **test_contains**: `in`演算子のテスト

#### TestDictInterface
- **test_get_method**: get()メソッドのテスト（デフォルト値含む）
- **test_keys_method**: keys()メソッドのテスト
- **test_values_method**: values()メソッドのテスト
- **test_items_method**: items()メソッドのテスト
- **test_len_method**: len()関数のテスト
- **test_update_method**: update()メソッドのテスト
- **test_clear_method**: clear()メソッドのテスト
- **test_pop_method**: pop()メソッドのテスト

#### TestContextManager
- **test_with_statement**: with文でのコンテキストマネージャー
- **test_exception_in_context**: コンテキスト内での例外処理

#### TestIteration
- **test_iterate_keys**: キーのイテレーション
- **test_iterate_items**: アイテムのイテレーション

#### TestErrorHandling
- **test_keyerror_on_missing_key**: 存在しないキーへのアクセスエラー
- **test_keyerror_on_delete_missing_key**: 存在しないキーの削除エラー
- **test_invalid_persist_mode**: 無効な永続化モードエラー
- **test_invalid_storage_mode**: 無効なストレージモードエラー

#### TestDataPersistence
- **test_data_persists_after_close**: close後のデータ永続化
- **test_flush_method**: flush()メソッドのテスト

#### TestMultipleTypes
- **test_bytes_values**: 様々なバイト型の値
- **test_string_keys**: 様々な文字列キー（日本語、絵文字含む）

### 2. test_storage_modes.py - ストレージモードテスト（8クラス、約40テスト）

各ストレージモードを網羅的にテストします：

#### TestBytesMode
- **test_bytes_basic**: 基本的なバイト列の保存
- **test_bytes_all_byte_values**: 0-255すべてのバイト値
- **test_bytes_large_value**: 大きなバイト列（1MB）
- **test_bytes_persistence**: 永続化テスト

#### TestPickleMode
- **test_pickle_python_dict**: Python辞書の保存
- **test_pickle_python_list**: Pythonリストの保存
- **test_pickle_nested_structures**: ネストされた構造
- **test_pickle_various_types**: 様々なPython型（int、float、bool、None、tuple、set）
- **test_pickle_persistence**: 永続化テスト

#### TestJSONBMode
- **test_jsonb_dict**: JSON辞書の保存
- **test_jsonb_list**: JSONリストの保存
- **test_jsonb_nested**: ネストされたJSON構造
- **test_jsonb_unicode**: Unicodeデータ（日本語、絵文字）
- **test_jsonb_numeric_precision**: 数値の精度テスト
- **test_jsonb_null_values**: null値のテスト
- **test_jsonb_empty_containers**: 空のコンテナ
- **test_jsonb_persistence**: 永続化テスト

#### TestJSONMode
- **test_json_basic**: 基本的なJSON操作（実装されている場合）

#### TestStorageModeComparison
- **test_bytes_vs_pickle_for_bytes**: BytesモードとPickleモードの比較
- **test_pickle_vs_jsonb_for_dict**: PickleモードとJSONBモードの比較
- **test_mode_specific_capabilities**: モード固有の機能

#### TestStorageModeEdgeCases
- **test_bytes_mode_with_dict_fails**: Bytesモードで辞書保存エラー
- **test_jsonb_mode_with_non_json_serializable**: JSONB非対応オブジェクトエラー
- **test_pickle_mode_custom_class**: Pickleモードでカスタムクラス保存

### 3. test_persistence_modes.py - 永続化モードテスト（5クラス、約30テスト）

各永続化モードを網羅的にテストします：

#### TestMemoryMode
- **test_memory_mode_basic**: 基本的な動作
- **test_memory_mode_not_persisted**: データが永続化されないこと
- **test_memory_mode_performance**: 高速性テスト
- **test_memory_mode_flush_has_no_effect**: flush()が効果なし

#### TestLazyMode
- **test_lazy_mode_basic**: 基本的な動作
- **test_lazy_mode_flush_persists**: flush()での永続化
- **test_lazy_mode_close_persists**: close()での自動永続化
- **test_lazy_mode_buffering**: バッファリング動作
- **test_lazy_mode_multiple_flushes**: 複数回のflush

#### TestWritethroughMode
- **test_writethrough_mode_basic**: 基本的な動作
- **test_writethrough_mode_immediate_persistence**: 即座の永続化
- **test_writethrough_mode_no_flush_needed**: flush()不要
- **test_writethrough_mode_update_persistence**: 更新の永続化
- **test_writethrough_mode_delete_persistence**: 削除の永続化

#### TestPersistModeComparison
- **test_memory_vs_writethrough_persistence**: MemoryとWritethroughの比較
- **test_lazy_vs_writethrough_timing**: LazyとWritethroughのタイミング比較
- **test_all_modes_final_persistence**: 全モードの最終永続化確認

#### TestPersistModeEdgeCases
- **test_lazy_mode_large_buffer**: 大量データのバッファリング
- **test_writethrough_mode_with_jsonb**: Writethrough + JSONB
- **test_mixed_persist_modes_same_db**: 同じDBを異なるモードで開く

### 4. test_async_operations.py - 非同期操作テスト（9クラス、約35テスト）

非同期機能を網羅的にテストします：

#### TestAsyncBasicCRUD
- **test_async_create_and_read**: 非同期での作成・読み取り
- **test_async_update**: 非同期での更新
- **test_async_delete**: 非同期での削除
- **test_async_contains**: 非同期でのcontainsチェック

#### TestAsyncBatchOperations
- **test_async_bulk_set**: 非同期一括設定
- **test_async_bulk_get**: 非同期一括取得
- **test_async_sequential_operations**: 非同期順次操作

#### TestAsyncConcurrentOperations
- **test_concurrent_async_writes**: 並行非同期書き込み（100並行）
- **test_concurrent_async_reads**: 並行非同期読み取り（100並行）
- **test_concurrent_mixed_operations**: 並行混合操作（読み書き混在）
- **test_high_concurrency**: 高並行度テスト（1000並行）

#### TestAsyncWithStorageModes
- **test_async_with_bytes_mode**: Bytesモードでの非同期
- **test_async_with_pickle_mode**: Pickleモードでの非同期
- **test_async_with_jsonb_mode**: JSONBモードでの非同期
- **test_async_mode_specific_data**: 各モード固有のデータ型

#### TestAsyncPersistence
- **test_async_data_persists**: 非同期書き込みデータの永続化
- **test_async_flush**: 非同期flushのテスト

#### TestAsyncErrorHandling
- **test_async_keyerror_on_missing_key**: 非同期KeyError
- **test_async_delete_missing_key**: 非同期削除エラー
- **test_async_operation_after_close**: close後の操作エラー

#### TestAsyncBackwardCompatibility
- **test_sync_methods_on_async_instance**: 非同期インスタンスでの同期メソッド
- **test_mixed_sync_async_operations**: 同期・非同期混在操作

#### TestAsyncContextManager
- **test_async_with_statement**: async with文
- **test_async_exception_in_context**: 非同期コンテキストでの例外

#### TestAsyncPerformance
- **test_async_throughput**: 非同期スループット測定（10000並行）

### 5. test_advanced_features.py - 高度な機能テスト（6クラス、約35テスト）

高度な機能を網羅的にテストします：

#### TestEncryption
- **test_encryption_basic**: 基本的な暗号化
- **test_encryption_wrong_password**: 間違ったパスワードでエラー
- **test_encryption_without_password**: パスワードなしでエラー
- **test_encryption_with_jsonb**: 暗号化 + JSONB
- **test_encryption_with_pickle**: 暗号化 + Pickle
- **test_encryption_multiple_keys**: 複数キーの暗号化

#### TestSafePickle
- **test_safe_pickle_basic**: 基本的なSafe Pickle
- **test_safe_pickle_allowed_module**: 許可されたモジュール
- **test_safe_pickle_reject_dangerous**: 危険なオブジェクトの拒否

#### TestMultiTable
- **test_multi_table_basic**: 基本的なマルチテーブル
- **test_multi_table_isolation**: テーブル間の隔離
- **test_multi_table_different_storage_modes**: 異なるストレージモード
- **test_multi_table_many_tables**: 多数のテーブル（50個）

#### TestHotTierCapacity
- **test_hot_capacity_basic**: 基本的なホットティア
- **test_hot_capacity_overflow**: キャパシティオーバーフロー
- **test_hot_capacity_eviction**: LRU eviction

#### TestStatistics
- **test_stats_basic**: 基本的な統計
- **test_stats_after_operations**: 操作後の統計変化
- **test_stats_with_encryption**: 暗号化有効時の統計

#### TestFeatureCombinations
- **test_encryption_plus_multi_table**: 暗号化 + マルチテーブル
- **test_all_features_combined**: すべての機能の組み合わせ

## 既存のテストファイル

### test_comprehensive_edge_cases.py（39テスト）
エッジケースとエラーハンドリング

### test_comprehensive_integration.py（21テスト）
統合テストと実世界のシナリオ

### test_comprehensive_stress.py（18テスト）
ストレステストとパフォーマンス検証

### test_jsonb_table_support.py
JSONB + テーブルサポートのテスト

### test_dict_compat_api.py
辞書互換APIのテスト

### test_async_awaitable.py
非同期awaitable機能のテスト

### test_async_persistence.py
非同期永続化のテスト

### test_v4_security.py
セキュリティ機能のテスト

### test_performance.py
パフォーマンステスト

## テスト実行方法

### すべてのテストを実行

```bash
cd /home/runner/work/DictSQLite/DictSQLite/dictsqlite_v2/dictsqlite
python -m pytest tests/ -v
```

### 新規追加した基本テストのみ実行

```bash
# 基本操作テスト
python -m pytest tests/test_basic_operations.py -v

# ストレージモードテスト
python -m pytest tests/test_storage_modes.py -v

# 永続化モードテスト
python -m pytest tests/test_persistence_modes.py -v

# 非同期操作テスト
python -m pytest tests/test_async_operations.py -v

# 高度な機能テスト
python -m pytest tests/test_advanced_features.py -v
```

### 特定のテストクラスを実行

```bash
# 基本CRUDのみ
python -m pytest tests/test_basic_operations.py::TestBasicCRUD -v

# 非同期並行操作のみ
python -m pytest tests/test_async_operations.py::TestAsyncConcurrentOperations -v

# 暗号化テストのみ
python -m pytest tests/test_advanced_features.py::TestEncryption -v
```

### 特定のテストメソッドを実行

```bash
# 特定のテスト1つ
python -m pytest tests/test_basic_operations.py::TestBasicCRUD::test_create_and_read -v
```

### 詳細な出力付きで実行

```bash
# 詳細出力（-s）とカバレッジ（--cov）
python -m pytest tests/ -v -s --cov=dictsqlite --cov-report=html
```

## テストカバレッジ

### 新規テストによる追加カバレッジ

新しく追加されたテストにより、以下の領域が詳細にカバーされます：

1. **基本機能**（test_basic_operations.py）: 約50テスト
   - CRUD操作
   - 辞書型インターフェース
   - コンテキストマネージャー
   - イテレータ
   - エラーハンドリング

2. **ストレージモード**（test_storage_modes.py）: 約40テスト
   - Bytes、Pickle、JSONB、JSONモード
   - モード間の比較
   - エッジケース

3. **永続化モード**（test_persistence_modes.py）: 約30テスト
   - Memory、Lazy、Writethroughモード
   - モード間の比較
   - タイミングとバッファリング

4. **非同期操作**（test_async_operations.py）: 約35テスト
   - 基本的な非同期CRUD
   - バッチ操作
   - 並行操作（最大1000並行）
   - ストレージモード組み合わせ
   - エラーハンドリング
   - 同期互換性

5. **高度な機能**（test_advanced_features.py）: 約35テスト
   - 暗号化（AES-256-GCM）
   - Safe Pickle
   - マルチテーブル
   - ホットティア/キャパシティ
   - 統計
   - 機能の組み合わせ

### 総合テスト数

- **既存テスト**: 約100テスト
  - test_comprehensive_edge_cases.py: 39テスト
  - test_comprehensive_integration.py: 21テスト
  - test_comprehensive_stress.py: 18テスト
  - その他: 約22テスト

- **新規テスト**: 約190テスト
  - test_basic_operations.py: 約50テスト
  - test_storage_modes.py: 約40テスト
  - test_persistence_modes.py: 約30テスト
  - test_async_operations.py: 約35テスト
  - test_advanced_features.py: 約35テスト

**総計**: 約290テスト以上

## テスト設計の原則

### 1. 段階的カバレッジ
- **基本**: 基本的なCRUD操作から開始
- **中級**: ストレージモード、永続化モードの詳細
- **高度**: 暗号化、マルチテーブル、並行操作
- **統合**: 複数機能の組み合わせ

### 2. 同期・非同期の両対応
- すべての主要機能に同期版と非同期版のテスト
- 互換性テストで両方の動作を確認

### 3. 隔離性と再現性
- 各テストは独立して実行可能
- 一時ファイルを使用（windows_safe_temp_db fixture）
- テスト後の自動クリーンアップ

### 4. エラーケースの網羅
- 正常系だけでなく異常系も徹底的にテスト
- KeyError、ValueError、RuntimeErrorなど

### 5. 実用性
- 実際の使用パターンに基づくテスト
- パフォーマンス測定を含む

## 前提条件

### モジュールのビルド

テストを実行する前に、Rust拡張モジュールをビルドする必要があります：

```bash
cd /home/runner/work/DictSQLite/DictSQLite/dictsqlite_v2/dictsqlite
maturin develop --release
```

または：

```bash
cd /home/runner/work/DictSQLite/DictSQLite/dictsqlite_v2/dictsqlite
./build.sh
```

### 依存関係

```bash
pip install pytest pytest-asyncio
```

## CI/CDでの実行

GitHub ActionsなどのCI/CDパイプラインでテストを実行する場合：

```yaml
- name: Build Rust extension
  run: |
    cd dictsqlite_v2/dictsqlite
    maturin develop --release

- name: Run basic tests
  run: |
    cd dictsqlite_v2/dictsqlite
    pytest tests/test_basic_operations.py -v

- name: Run all tests
  run: |
    cd dictsqlite_v2/dictsqlite
    pytest tests/ -v --maxfail=5
```

## トラブルシューティング

### モジュールが見つからないエラー

```
ModuleNotFoundError: No module named 'dictsqlite'
```

**解決策**: Rust拡張モジュールをビルドしてください：
```bash
cd dictsqlite_v2/dictsqlite
maturin develop --release
```

### Windowsでのファイルロックエラー

```
PermissionError: [WinError 32] The process cannot access the file...
```

**解決策**: conftest.pyの`windows_safe_temp_db` fixtureが自動的にリトライロジックでハンドリングします。

### 非同期テストの実行エラー

```
RuntimeError: no running event loop
```

**解決策**: `pytest-asyncio`がインストールされているか確認してください：
```bash
pip install pytest-asyncio
```

## まとめ

この包括的なテストスイートにより、DictSQLite v4.2のすべての主要機能が基本から高度まで、同期・非同期の両方で徹底的にテストされます。

- ✅ 基本CRUD操作
- ✅ 辞書型インターフェース
- ✅ 全ストレージモード（Bytes、Pickle、JSONB、JSON）
- ✅ 全永続化モード（Memory、Lazy、Writethrough）
- ✅ 非同期操作（基本～高並行度）
- ✅ 暗号化機能
- ✅ Safe Pickle
- ✅ マルチテーブル
- ✅ ホットティア管理
- ✅ 統計・モニタリング
- ✅ エラーハンドリング
- ✅ 機能の組み合わせ

約290個以上のテストにより、品質と信頼性が保証されます。
