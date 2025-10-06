"""エッジケースのテスト"""

import pytest

from dictsqlite_v2.core import DictSQLiteV2


class TestEdgeCases:
    """エッジケーステスト"""
    
    def test_empty_database(self, temp_db_path):
        """空のデータベース"""
        db = DictSQLiteV2(temp_db_path)
        
        assert len(db) == 0
        assert list(db.keys()) == []
        assert list(db.values()) == []
        assert list(db.items()) == []
        
        db.close()
    
    def test_large_values(self, temp_db_path):
        """大きな値の処理"""
        db = DictSQLiteV2(temp_db_path)
        
        # 1MBの値
        large_value = 'x' * (1024 * 1024)
        db['large'] = large_value
        
        assert db['large'] == large_value
        
        db.close()
    
    def test_special_characters_in_keys(self, temp_db_path):
        """特殊文字を含むキー"""
        db = DictSQLiteV2(temp_db_path)
        
        special_keys = [
            'key with spaces',
            'key:with:colons',
            'key/with/slashes',
            'key\\with\\backslashes',
            'key"with"quotes',
            "key'with'quotes",
            'key\nwith\nnewlines',
            'キー日本語',
            '🔑emoji_key',
        ]
        
        for key in special_keys:
            db[key] = f'value_for_{key}'
        
        for key in special_keys:
            assert db[key] == f'value_for_{key}'
        
        db.close()
    
    def test_unicode_values(self, temp_db_path):
        """Unicode値の処理"""
        db = DictSQLiteV2(temp_db_path)
        
        db['japanese'] = 'こんにちは世界'
        db['emoji'] = '🎉🎊🎈'
        db['mixed'] = 'Hello 世界 🌍'
        
        assert db['japanese'] == 'こんにちは世界'
        assert db['emoji'] == '🎉🎊🎈'
        assert db['mixed'] == 'Hello 世界 🌍'
        
        db.close()
    
    def test_none_values(self, temp_db_path):
        """None値の処理"""
        db = DictSQLiteV2(temp_db_path)
        
        db['none_key'] = None
        
        assert db['none_key'] is None
        assert 'none_key' in db
        
        db.close()
    
    def test_nested_structures(self, temp_db_path):
        """ネストされたデータ構造"""
        db = DictSQLiteV2(temp_db_path)
        
        nested = {
            'level1': {
                'level2': {
                    'level3': {
                        'value': 'deep'
                    }
                }
            },
            'list': [1, 2, [3, 4, [5, 6]]],
        }
        
        db['nested'] = nested
        
        assert db['nested'] == nested
        
        db.close()
    
    def test_duplicate_operations(self, temp_db_path):
        """重複操作の処理"""
        db = DictSQLiteV2(temp_db_path)
        
        # 同じキーに複数回書き込み
        db['key'] = 'value1'
        db['key'] = 'value2'
        db['key'] = 'value3'
        
        assert db['key'] == 'value3'
        
        db.close()
    
    def test_rapid_open_close(self, temp_db_path):
        """高頻度でのopen/close"""
        for i in range(10):
            db = DictSQLiteV2(temp_db_path)
            db[f'key_{i}'] = f'value_{i}'
            db.close()
        
        # 最終確認
        db = DictSQLiteV2(temp_db_path)
        for i in range(10):
            assert db[f'key_{i}'] == f'value_{i}'
        db.close()
    
    def test_concurrent_same_key(self, temp_db_path):
        """同じキーへの連続アクセス"""
        db = DictSQLiteV2(temp_db_path)
        
        # 同じキーを連続で読み書き
        for i in range(100):
            db['same_key'] = f'value_{i}'
            assert db['same_key'] == f'value_{i}'
        
        db.close()
    
    def test_delete_nonexistent_key(self, temp_db_path):
        """存在しないキーの削除"""
        db = DictSQLiteV2(temp_db_path)
        
        with pytest.raises(KeyError):
            del db['nonexistent']
        
        db.close()
    
    def test_get_nonexistent_key(self, temp_db_path):
        """存在しないキーの取得"""
        db = DictSQLiteV2(temp_db_path)
        
        # []でアクセス
        with pytest.raises(KeyError):
            _ = db['nonexistent']
        
        # get()でアクセス
        assert db.get('nonexistent') is None
        assert db.get('nonexistent', 'default') == 'default'
        
        db.close()
    
    def test_many_small_items(self, temp_db_path):
        """多数の小さなアイテム"""
        db = DictSQLiteV2(temp_db_path)
        
        # 10,000個の小さなアイテム
        num_items = 10000
        for i in range(num_items):
            db[f'key_{i}'] = i
        
        assert len(db) == num_items
        
        # ランダムアクセス
        assert db['key_5000'] == 5000
        assert db['key_9999'] == 9999
        
        db.close()
    
    def test_empty_string_key(self, temp_db_path):
        """空文字列のキー"""
        db = DictSQLiteV2(temp_db_path)
        
        db[''] = 'empty_key_value'
        
        assert db[''] == 'empty_key_value'
        assert '' in db
        
        db.close()
    
    def test_boolean_values(self, temp_db_path):
        """Boolean値の処理"""
        db = DictSQLiteV2(temp_db_path)
        
        db['true'] = True
        db['false'] = False
        
        assert db['true'] is True
        assert db['false'] is False
        
        db.close()
    
    def test_numeric_values(self, temp_db_path):
        """数値型の処理"""
        db = DictSQLiteV2(temp_db_path)
        
        db['int'] = 42
        db['float'] = 3.14159
        db['negative'] = -100
        db['zero'] = 0
        
        assert db['int'] == 42
        assert db['float'] == 3.14159
        assert db['negative'] == -100
        assert db['zero'] == 0
        
        db.close()
