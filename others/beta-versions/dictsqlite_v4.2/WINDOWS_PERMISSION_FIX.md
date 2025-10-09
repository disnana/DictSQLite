# Windows PermissionError Fix

## 問題の概要

Windows環境において、主に非同期のテストで以下のようなエラーが発生していました：

```
PermissionError: [WinError 32] プロセスはファイルにアクセスできません。別のプロセスが使用中です。
```

## 原因

Windowsでは、データベースファイルを閉じた直後でも、OSがファイルハンドルを完全に解放するまでに少し時間がかかります。`tempfile.TemporaryDirectory()`や明示的な`os.unlink()`によるクリーンアップが`db.close()`の直後に実行されると、ファイルハンドルがまだ解放されていないためPermissionErrorが発生します。

## 修正内容（v2 - パフォーマンス最適化版）

パフォーマンスへの影響を最小限に抑えるため、以下のアプローチを採用しました：

1. **共有クリーンアップユーティリティの作成** (`conftest.py`)
   - `cleanup_db_files()`: データベースファイルのクリーンアップ用ヘルパー関数
   - `windows_safe_temp_db()`: `tempfile.mkstemp()`の代替となるコンテキストマネージャ
   - `windows_safe_temp_dir()`: `tempfile.TemporaryDirectory()`の代替となるコンテキストマネージャ

2. **プラットフォーム検出による条件付き遅延**
   - `sys.platform == 'win32'`でWindowsを検出
   - Windowsの場合のみ`time.sleep(0.1)`を実行
   - Linux/macOSでは遅延なし（パフォーマンスへの影響ゼロ）

3. **リトライロジックの実装**
   - PermissionErrorをキャッチして最大3回リトライ
   - 各リトライ間に200msの待機時間
   - 失敗した場合は静かに無視（テストの実行を妨げない）

### 修正したファイル

1. **conftest.py** (新規作成) - 共有ユーティリティ関数
2. **test_async_table_contains.py** - `windows_safe_temp_dir()`を使用
3. **test_dict_compat_api.py** - `windows_safe_temp_db()`を使用
4. **test_jsonb_table_support.py** - `windows_safe_temp_dir()`を使用
5. **test_lru_eviction.py** - `windows_safe_temp_db()`を使用

### 修正例

#### Before (v1 - パフォーマンスへの影響あり)

```python
# すべてのプラットフォームで遅延が発生
db.close()
time.sleep(0.1)  # 常に実行される
print("✅ Test passed")
```

#### After (v2 - パフォーマンス最適化版)

```python
from conftest import windows_safe_temp_db

# Windowsの場合のみクリーンアップ時に遅延
with windows_safe_temp_db() as db_path:
    db = DictSQLiteV4(db_path, persist_mode="lazy")
    # テストコード
    db.close()
    # コンテキスト終了時に自動クリーンアップ（Windowsのみ遅延）
```

## 既存の対策との整合性

以下のテストファイルには既にこのパターンが実装されていました：

- **test_async_persistence.py** - `cleanup_db_files()`関数内で同様のリトライロジックを使用
- **test_async_awaitable.py** - `cleanup_db_files()`関数内で同様のリトライロジックを使用

今回の修正により、同じパターンを`conftest.py`に統合し、すべてのテストファイルで再利用可能になりました。

## 影響

- **パフォーマンス**: 
  - Windows: クリーンアップ時のみ0.1秒の遅延（テスト実行中は遅延なし）
  - Linux/macOS: 遅延なし（**パフォーマンスへの影響ゼロ**）
- **互換性**: すべてのプラットフォームで動作
- **信頼性**: Windows環境でのテストの成功率が大幅に向上
- **保守性**: 共有ユーティリティによりコードの重複を削減

## テスト結果

修正後、以下のテストがWindows環境で成功するようになります：

- test_async_table_contains.py::test_async_table_contains_basic
- test_async_table_contains.py::test_async_table_contains_with_different_storage_modes
- test_async_table_contains.py::test_async_table_contains_multiple_tables
- test_dict_compat_api.py::test_dict_items_values_methods
- test_dict_compat_api.py::test_dict_update_method
- test_dict_compat_api.py::test_dict_pop_method
- test_dict_compat_api.py::test_dict_setdefault_method
- test_dict_compat_api.py::test_dict_compatibility_with_persistence
- test_jsonb_table_support.py::test_jsonb_mode_basic
- test_jsonb_table_support.py::test_json_mode_basic
- test_jsonb_table_support.py::test_table_support_basic
- test_jsonb_table_support.py::test_table_with_default_table_name
- test_jsonb_table_support.py::test_async_table_support
- test_jsonb_table_support.py::test_async_batch_operations_with_jsonb
- test_jsonb_table_support.py::test_async_multiple_tables
- test_jsonb_table_support.py::test_persistence_across_sessions
- test_jsonb_table_support.py::test_table_persistence
- test_jsonb_table_support.py::test_mixed_storage_modes
- test_lru_eviction.py::test_lru_eviction_basic
- test_lru_eviction.py::test_lru_eviction_access_pattern
- test_lru_eviction.py::test_lru_eviction_large_dataset
