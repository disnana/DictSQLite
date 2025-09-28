"""Comprehensive compatibility tests between DictSQLite and DictSQLite-Fastest."""

import pytest
import tempfile
import os
import json
import pickle

from dictsqlite.main import DictSQLite
from dictsqlite_fastest.main import DictSQLiteFastest


@pytest.fixture()
def tmp_db_paths(tmp_path):
    """一時的なDBファイルパスを提供"""
    return {
        'original': tmp_path / "original.db",
        'fastest': tmp_path / "fastest.db"
    }


class TestFullCompatibility:
    """完全な互換性テスト"""

    def test_data_type_compatibility(self, tmp_db_paths):
        """全データ型の互換性テスト"""
        
        test_data = {
            # 基本データ型
            "string": "hello world",
            "integer": 42,
            "float": 3.14159,
            "boolean_true": True,
            "boolean_false": False,
            "none_value": None,
            "empty_string": "",
            "zero": 0,
            
            # コレクション
            "list_simple": [1, 2, 3, 4, 5],
            "list_mixed": [1, "two", 3.0, True, None],
            "list_nested": [[1, 2], [3, 4], [5, 6]],
            "dict_simple": {"a": 1, "b": 2, "c": 3},
            "dict_nested": {"outer": {"inner": {"deep": "value"}}},
            "set_simple": {1, 2, 3, 4, 5},
            "set_mixed": {1, "two", 3.0},  # Note: True/False may conflict with 1/0
            
            # 複雑な構造
            "complex_structure": {
                "users": [
                    {
                        "id": 1,
                        "name": "Alice",
                        "tags": {"admin", "user"},
                        "scores": [95, 87, 92]
                    },
                    {
                        "id": 2,
                        "name": "Bob", 
                        "tags": {"user"},
                        "scores": [78, 85, 90]
                    }
                ],
                "metadata": {
                    "created": "2024-01-01",
                    "version": 1.0,
                    "enabled": True
                }
            },
            
            # バイナリデータ
            "bytes_data": b"binary data \x00\x01\x02",
            
            # 大きなデータ
            "large_string": "x" * 10000,
            "large_list": list(range(1000)),
        }
        
        # 両方のDBに同じデータを保存
        with DictSQLite(str(tmp_db_paths['original'])) as db_orig:
            for key, value in test_data.items():
                db_orig[key] = value
        
        with DictSQLiteFastest(str(tmp_db_paths['fastest'])) as db_fast:
            for key, value in test_data.items():
                db_fast[key] = value
        
        # データを読み戻して比較
        with DictSQLite(str(tmp_db_paths['original'])) as db_orig:
            with DictSQLiteFastest(str(tmp_db_paths['fastest'])) as db_fast:
                for key, expected_value in test_data.items():
                    orig_value = db_orig[key]
                    fast_value = db_fast[key]
                    
                    # セットは順序が不定なので特別処理
                    if isinstance(expected_value, set):
                        assert isinstance(orig_value, set), f"Original returned {type(orig_value)} for key {key}"
                        assert isinstance(fast_value, set), f"Fastest returned {type(fast_value)} for key {key}"
                        assert orig_value == fast_value == expected_value, f"Set mismatch for key {key}"
                    else:
                        assert orig_value == fast_value == expected_value, f"Value mismatch for key {key}"

    def test_api_compatibility(self, tmp_db_paths):
        """API互換性テスト"""
        
        # 同じ操作を両方で実行
        operations = [
            ("set_item", lambda db: db.__setitem__("test_key", "test_value")),
            ("get_item", lambda db: db.__getitem__("test_key")),
            ("contains", lambda db: "test_key" in db),
            ("keys", lambda db: list(db.keys())),
            ("has_key", lambda db: db.has_key("test_key")),
            ("delete", lambda db: db.__delitem__("test_key")),
            ("contains_after_delete", lambda db: "test_key" in db),
        ]
        
        orig_results = []
        fast_results = []
        
        with DictSQLite(str(tmp_db_paths['original'])) as db_orig:
            for op_name, op_func in operations:
                try:
                    result = op_func(db_orig)
                    orig_results.append((op_name, result, None))
                except Exception as e:
                    orig_results.append((op_name, None, type(e).__name__))
        
        with DictSQLiteFastest(str(tmp_db_paths['fastest'])) as db_fast:
            for op_name, op_func in operations:
                try:
                    result = op_func(db_fast)
                    fast_results.append((op_name, result, None))
                except Exception as e:
                    fast_results.append((op_name, None, type(e).__name__))
        
        # 結果を比較
        for orig, fast in zip(orig_results, fast_results):
            assert orig[0] == fast[0], "Operation names should match"
            
            if orig[2] is not None or fast[2] is not None:
                # 例外が発生した場合
                assert orig[2] == fast[2], f"Exception types should match for {orig[0]}: {orig[2]} vs {fast[2]}"
            else:
                # 正常な結果の場合
                assert orig[1] == fast[1], f"Results should match for {orig[0]}: {orig[1]} vs {fast[1]}"

    def test_storage_mode_compatibility(self, tmp_db_paths):
        """ストレージモード互換性テスト"""
        
        test_data = {
            "json_string": "hello",
            "json_number": 123,
            "json_float": 3.14,
            "json_bool": True,
            "json_null": None,
            "json_list": [1, 2, 3],
            "json_dict": {"a": 1, "b": 2},
            "json_set": {1, 2, 3}  # This gets special handling in JSON mode
        }
        
        # JSON mode test
        with DictSQLite(str(tmp_db_paths['original']), storage_mode='json') as db_orig:
            for key, value in test_data.items():
                db_orig[key] = value
        
        with DictSQLiteFastest(str(tmp_db_paths['fastest']), storage_mode='json') as db_fast:
            for key, value in test_data.items():
                db_fast[key] = value
        
        # Verify JSON mode results are identical
        with DictSQLite(str(tmp_db_paths['original']), storage_mode='json') as db_orig:
            with DictSQLiteFastest(str(tmp_db_paths['fastest']), storage_mode='json') as db_fast:
                for key, expected_value in test_data.items():
                    orig_value = db_orig[key]
                    fast_value = db_fast[key]
                    
                    if isinstance(expected_value, set):
                        assert orig_value == fast_value == expected_value
                    else:
                        assert orig_value == fast_value == expected_value

    def test_synced_collections_compatibility(self, tmp_db_paths):
        """同期コレクションの互換性テスト"""
        
        # List operations
        with DictSQLite(str(tmp_db_paths['original'])) as db_orig:
            db_orig["mylist"] = [1, 2, 3]
            db_orig["mylist"].append(4)
            db_orig["mylist"].extend([5, 6])
            orig_list = list(db_orig["mylist"])
        
        with DictSQLiteFastest(str(tmp_db_paths['fastest'])) as db_fast:
            db_fast["mylist"] = [1, 2, 3]
            db_fast["mylist"].append(4)
            db_fast["mylist"].extend([5, 6])
            fast_list = list(db_fast["mylist"])
        
        assert orig_list == fast_list == [1, 2, 3, 4, 5, 6]
        
        # Set operations
        with DictSQLite(str(tmp_db_paths['original'])) as db_orig:
            db_orig["myset"] = {1, 2, 3}
            db_orig["myset"].add(4)
            db_orig["myset"].update({5, 6})
            orig_set = set(db_orig["myset"])
        
        with DictSQLiteFastest(str(tmp_db_paths['fastest'])) as db_fast:
            db_fast["myset"] = {1, 2, 3}
            db_fast["myset"].add(4)
            db_fast["myset"].update({5, 6})
            fast_set = set(db_fast["myset"])
        
        assert orig_set == fast_set == {1, 2, 3, 4, 5, 6}

    def test_recursive_dict_compatibility(self, tmp_db_paths):
        """再帰辞書の互換性テスト"""
        
        test_nested = {
            "level1": {
                "level2": {
                    "level3": {
                        "value": "deep_value",
                        "number": 42
                    },
                    "list": [1, 2, 3]
                },
                "simple": "simple_value"
            }
        }
        
        # 両方に保存
        with DictSQLite(str(tmp_db_paths['original'])) as db_orig:
            db_orig["nested"] = test_nested
            
        with DictSQLiteFastest(str(tmp_db_paths['fastest'])) as db_fast:
            db_fast["nested"] = test_nested
        
        # 深いネストアクセスをテスト
        with DictSQLite(str(tmp_db_paths['original'])) as db_orig:
            with DictSQLiteFastest(str(tmp_db_paths['fastest'])) as db_fast:
                # レベル1アクセス
                assert db_orig["nested"]["level1"]["simple"] == db_fast["nested"]["level1"]["simple"] == "simple_value"
                
                # レベル3アクセス
                orig_deep = db_orig["nested"]["level1"]["level2"]["level3"]["value"]
                fast_deep = db_fast["nested"]["level1"]["level2"]["level3"]["value"]
                assert orig_deep == fast_deep == "deep_value"
                
                # 更新テスト
                db_orig["nested"]["level1"]["level2"]["level3"]["new_key"] = "new_value"
                db_fast["nested"]["level1"]["level2"]["level3"]["new_key"] = "new_value"
                
                # 更新が反映されているか確認
                orig_new = db_orig["nested"]["level1"]["level2"]["level3"]["new_key"]
                fast_new = db_fast["nested"]["level1"]["level2"]["level3"]["new_key"]
                assert orig_new == fast_new == "new_value"

    def test_journal_mode_compatibility(self, tmp_db_paths):
        """Journal mode互換性テスト"""
        
        journal_modes = ['DELETE', 'WAL', 'MEMORY']
        
        for mode in journal_modes:
            test_data = {f"key_{mode}_{i}": f"value_{mode}_{i}" for i in range(100)}
            
            # Original with specific journal mode
            with DictSQLite(str(tmp_db_paths['original']), journal_mode=mode) as db_orig:
                for key, value in test_data.items():
                    db_orig[key] = value
            
            # Fastest with same journal mode
            with DictSQLiteFastest(str(tmp_db_paths['fastest']), journal_mode=mode) as db_fast:
                for key, value in test_data.items():
                    db_fast[key] = value
            
            # Verify data integrity
            with DictSQLite(str(tmp_db_paths['original']), journal_mode=mode) as db_orig:
                with DictSQLiteFastest(str(tmp_db_paths['fastest']), journal_mode=mode) as db_fast:
                    for key, expected_value in test_data.items():
                        assert db_orig[key] == db_fast[key] == expected_value

    def test_error_handling_compatibility(self, tmp_db_paths):
        """エラーハンドリング互換性テスト"""
        
        error_tests = [
            ("missing_key", lambda db: db["nonexistent_key"], KeyError),
            # Note: original DictSQLite doesn't raise error when deleting missing keys
            # ("delete_missing", lambda db: db.__delitem__("nonexistent_key"), KeyError),
        ]
        
        for test_name, operation, expected_error in error_tests:
            orig_error = None
            fast_error = None
            
            # Original
            with DictSQLite(str(tmp_db_paths['original'])) as db_orig:
                try:
                    operation(db_orig)
                except Exception as e:
                    orig_error = type(e)
            
            # Fastest
            with DictSQLiteFastest(str(tmp_db_paths['fastest'])) as db_fast:
                try:
                    operation(db_fast)
                except Exception as e:
                    fast_error = type(e)
            
            # 同じエラータイプが発生することを確認
            assert orig_error == fast_error == expected_error, f"Error types should match for {test_name}"

    def test_performance_vs_compatibility_tradeoff(self, tmp_db_paths):
        """パフォーマンスと互換性のトレードオフテスト"""
        
        # 大量データでの動作確認
        n_items = 1000
        
        with DictSQLite(str(tmp_db_paths['original'])) as db_orig:
            with DictSQLiteFastest(str(tmp_db_paths['fastest'])) as db_fast:
                # 同じ操作パターンを実行
                for i in range(n_items):
                    key = f"perf_key_{i}"
                    value = {"id": i, "data": f"data_{i}", "tags": [f"tag_{j}" for j in range(5)]}
                    
                    db_orig[key] = value
                    db_fast[key] = value
                    
                    # 即座に読み戻し
                    orig_read = db_orig[key]
                    fast_read = db_fast[key]
                    
                    assert orig_read == fast_read == value
                
                # 全データの整合性確認
                orig_keys = set(db_orig.keys())
                fast_keys = set(db_fast.keys())
                
                expected_keys = {f"perf_key_{i}" for i in range(n_items)}
                assert orig_keys == fast_keys == expected_keys


def test_migration_scenario(tmp_path):
    """マイグレーションシナリオテスト"""
    
    # Step 1: Create data with original DictSQLite
    original_db_path = tmp_path / "migration_test.db"
    
    migration_data = {
        "user_1": {"name": "Alice", "age": 30, "tags": {"admin", "user"}},
        "user_2": {"name": "Bob", "age": 25, "tags": {"user"}},
        "config": {"version": "1.0", "features": ["auth", "api", "ui"]},
        "stats": {"total_users": 2, "active_sessions": 5}
    }
    
    with DictSQLite(str(original_db_path)) as db:
        for key, value in migration_data.items():
            db[key] = value
    
    # Step 2: Read same data with DictSQLite-Fastest
    with DictSQLiteFastest(str(original_db_path)) as db_fast:
        for key, expected_value in migration_data.items():
            actual_value = db_fast[key]
            
            if isinstance(expected_value, dict) and "tags" in expected_value:
                # Handle set comparison specially
                expected_copy = expected_value.copy()
                actual_copy = dict(actual_value) if hasattr(actual_value, 'to_dict') else actual_value.copy()
                
                assert expected_copy.pop("tags") == actual_copy.pop("tags")  # Compare sets
                assert expected_copy == actual_copy  # Compare rest
            else:
                assert actual_value == expected_value
    
    # Step 3: Add new data with DictSQLite-Fastest
    with DictSQLiteFastest(str(original_db_path)) as db_fast:
        db_fast["new_user"] = {"name": "Charlie", "age": 28, "tags": {"user", "beta"}}
        db_fast["stats"]["total_users"] = 3
    
    # Step 4: Verify with original DictSQLite
    with DictSQLite(str(original_db_path)) as db_orig:
        new_user = db_orig["new_user"]
        assert new_user["name"] == "Charlie"
        assert new_user["age"] == 28
        assert new_user["tags"] == {"user", "beta"}
        
        updated_stats = db_orig["stats"]
        assert updated_stats["total_users"] == 3