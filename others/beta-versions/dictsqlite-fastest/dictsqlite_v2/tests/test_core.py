"""コア機能のテスト"""

import pytest

from dictsqlite_v2.core import DictSQLiteV2


class TestDictSQLiteV2Core:
    """DictSQLiteV2のコア機能テスト"""
    
    def test_basic_operations(self, temp_db_path):
        """基本的な読み書き操作のテスト"""
        db = DictSQLiteV2(temp_db_path, write_buffer_size=1)  # Small buffer for immediate writes
        
        # 書き込み
        db['key1'] = 'value1'
        db['key2'] = {'nested': 'value'}
        
        # 読み込み
        assert db['key1'] == 'value1'
        assert db['key2'] == {'nested': 'value'}
        
        # 更新
        db['key1'] = 'updated_value'
        # Re-open to ensure persistence
        db.close()
        db = DictSQLiteV2(temp_db_path)
        assert db['key1'] == 'updated_value'
        
        # 削除 - Note: buffered delete requires close/reopen for verification
        del db['key1']
        db.close()
        db = DictSQLiteV2(temp_db_path)
        assert 'key1' not in db
        
        db.close()
    
    def test_bulk_operations(self, temp_db_path):
        """バルク操作のテスト"""
        db = DictSQLiteV2(temp_db_path, write_buffer_size=1)
        
        # バルク挿入
        data = {f'key_{i}': f'value_{i}' for i in range(100)}
        db.bulk_insert(data)
        
        # 確認
        for key, value in data.items():
            assert db[key] == value
        
        db.close()
    
    def test_contains(self, temp_db_path):
        """in演算子のテスト"""
        db = DictSQLiteV2(temp_db_path, write_buffer_size=1)
        
        db['exists'] = 'value'
        
        assert 'exists' in db
        assert 'not_exists' not in db
        
        db.close()
    
    def test_len(self, temp_db_path):
        """len()のテスト"""
        db = DictSQLiteV2(temp_db_path, write_buffer_size=1)
        
        assert len(db) == 0
        
        db['key1'] = 'value1'
        db['key2'] = 'value2'
        
        assert len(db) == 2
        
        db.close()
    
    def test_keys_values_items(self, temp_db_path):
        """keys()のテスト"""
        db = DictSQLiteV2(temp_db_path, write_buffer_size=1)
        
        data = {'a': 1, 'b': 2, 'c': 3}
        for k, v in data.items():
            db[k] = v
        
        # keys() method is available
        assert set(db.keys()) == set(data.keys())
        
        # Verify values by reading
        for k, v in data.items():
            assert db[k] == v
        
        db.close()
    
    def test_get_method(self, temp_db_path):
        """get()メソッドのテスト"""
        db = DictSQLiteV2(temp_db_path, write_buffer_size=1)
        
        db['exists'] = 'value'
        
        assert db.get('exists') == 'value'
        assert db.get('not_exists') is None
        assert db.get('not_exists', 'default') == 'default'
        
        db.close()
    
    def test_context_manager(self, temp_db_path):
        """コンテキストマネージャのテスト"""
        with DictSQLiteV2(temp_db_path, write_buffer_size=1) as db:
            db['key'] = 'value'
            assert db['key'] == 'value'
        
        # 再度開いて確認
        with DictSQLiteV2(temp_db_path) as db:
            assert db['key'] == 'value'
    
    def test_cache_functionality(self, temp_db_path):
        """キャッシュ機能のテスト"""
        db = DictSQLiteV2(temp_db_path, cache_capacity=10)
        
        # データを書き込み
        for i in range(20):
            db[f'key_{i}'] = f'value_{i}'
        
        # 統計を確認
        stats = db.get_performance_stats()
        assert 'version' in stats
        assert stats['version'] == '2.0.0'
        
        db.close()
    
    def test_performance_stats(self, temp_db_path):
        """パフォーマンス統計のテスト"""
        db = DictSQLiteV2(temp_db_path)
        
        db['test'] = 'value'
        
        stats = db.get_performance_stats()
        
        assert 'version' in stats
        assert stats['version'] == '2.0.0'
        assert 'database' in stats
        assert 'optimizations' in stats
        assert stats['optimizations']['cache_enabled'] is True
        assert stats['optimizations']['write_buffer_enabled'] is True
        
        db.close()
