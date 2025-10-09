# Windows PermissionError Fix

## 問題の概要

Windows環境において、主に非同期のテストで以下のようなエラーが発生していました：

```
PermissionError: [WinError 32] プロセスはファイルにアクセスできません。別のプロセスが使用中です。
```

## 原因

Windowsでは、データベースファイルを閉じた直後でも、OSがファイルハンドルを完全に解放するまでに少し時間がかかります。`tempfile.TemporaryDirectory()`や明示的な`os.unlink()`によるクリーンアップが`db.close()`の直後に実行されると、ファイルハンドルがまだ解放されていないためPermissionErrorが発生します。

## 修正内容

すべての`db.close()`呼び出しの直後に`time.sleep(0.1)`を追加しました。これにより、Windowsがファイルハンドルを完全に解放するまで0.1秒待機します。

### 修正したファイル

1. **test_async_table_contains.py** (3箇所)
2. **test_dict_compat_api.py** (5箇所)
3. **test_jsonb_table_support.py** (13箇所)
4. **test_lru_eviction.py** (6箇所)

### 修正例

```python
# 修正前
db.close()
print("✅ Test passed")

# 修正後
db.close()
time.sleep(0.1)  # Windows: Wait for file handles to be released
print("✅ Test passed")
```

## 既存の対策との整合性

以下のテストファイルには既にこのパターンが実装されていました：

- **test_async_persistence.py** - `cleanup_db_files()`関数内で同様のリトライロジックを使用
- **test_async_awaitable.py** - `cleanup_db_files()`関数内で同様のリトライロジックを使用

今回の修正により、すべてのテストファイルでWindows環境におけるファイルハンドル解放の問題に対処しています。

## 影響

- **パフォーマンス**: 各テストの実行時間が0.1秒増加しますが、これは許容範囲内です。
- **互換性**: Linux/macOS環境でも問題なく動作します（sleepは無害）。
- **信頼性**: Windows環境でのテストの成功率が大幅に向上します。

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
