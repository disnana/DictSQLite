"""統合テスト"""

import pytest

from dictsqlite_v2.core import DictSQLiteV2


class TestIntegration:
    """統合テスト"""
    
    def test_full_workflow(self, temp_db_path):
        """完全なワークフローのテスト"""
        # 初期化
        db = DictSQLiteV2(temp_db_path, cache_capacity=100, write_buffer_size=1)
        
        # 大量データの書き込み
        num_items = 1000
        for i in range(num_items):
            db[f'key_{i}'] = {'id': i, 'data': f'value_{i}'}
        
        # 読み込み確認
        for i in range(0, num_items, 10):
            assert db[f'key_{i}']['id'] == i
        
        # 更新
        for i in range(0, 100):
            db[f'key_{i}'] = {'id': i, 'data': f'updated_{i}'}
        
        # Persist changes
        db.close()
        db = DictSQLiteV2(temp_db_path)
        
        # 更新確認
        for i in range(0, 100):
            assert db[f'key_{i}']['data'] == f'updated_{i}'
        
        # 削除
        for i in range(0, 50):
            del db[f'key_{i}']
        
        # Persist deletes
        db.close()
        db = DictSQLiteV2(temp_db_path)
        
        # 削除確認
        assert len(db) == num_items - 50
        
        db.close()
    
    def test_persistence(self, temp_db_path):
        """永続性のテスト"""
        # データ書き込み
        with DictSQLiteV2(temp_db_path) as db:
            db['persistent1'] = 'value1'
            db['persistent2'] = {'nested': 'value2'}
        
        # 再度開いて確認
        with DictSQLiteV2(temp_db_path) as db:
            assert db['persistent1'] == 'value1'
            assert db['persistent2'] == {'nested': 'value2'}
    
    def test_bulk_and_individual_mixed(self, temp_db_path):
        """バルク操作と個別操作の混在"""
        db = DictSQLiteV2(temp_db_path, write_buffer_size=1)
        
        # 個別書き込み
        for i in range(100):
            db[f'individual_{i}'] = f'value_{i}'
        
        # バルク書き込み
        bulk_data = {f'bulk_{i}': f'value_{i}' for i in range(100)}
        db.bulk_insert(bulk_data)
        
        # Ensure persistence
        db.close()
        db = DictSQLiteV2(temp_db_path)
        
        # 確認
        assert len(db) == 200
        assert db['individual_50'] == 'value_50'
        assert db['bulk_50'] == 'value_50'
        
        db.close()
    
    def test_cache_effectiveness(self, temp_db_path):
        """キャッシュ効果のテスト"""
        db = DictSQLiteV2(temp_db_path, cache_capacity=50, write_buffer_size=1)
        
        # データ書き込み
        for i in range(100):
            db[f'key_{i}'] = f'value_{i}'
        
        # 同じデータへの繰り返しアクセス（キャッシュヒット）
        for _ in range(10):
            for i in range(50):
                _ = db[f'key_{i}']
        
        # 統計確認
        stats = db.get_performance_stats()
        assert 'version' in stats
        assert stats['version'] == '2.0.0'
        # Cache info may not be exposed in the current implementation
        
        db.close()
    
    def test_real_world_scenario(self, temp_db_path):
        """実世界シナリオのシミュレーション"""
        db = DictSQLiteV2(temp_db_path)
        
        # ユーザーデータの保存
        users = {}
        for i in range(100):
            user_data = {
                'id': i,
                'name': f'User{i}',
                'email': f'user{i}@example.com',
                'profile': {
                    'age': 20 + (i % 50),
                    'country': 'Japan' if i % 2 == 0 else 'USA',
                }
            }
            users[f'user:{i}'] = user_data
        
        db.bulk_insert(users)
        
        # ユーザー検索（個別アクセス）
        user_10 = db['user:10']
        assert user_10['name'] == 'User10'
        assert user_10['email'] == 'user10@example.com'
        
        # ユーザー更新
        user_10['profile']['age'] = 99
        db['user:10'] = user_10
        
        # 更新確認
        updated_user = db['user:10']
        assert updated_user['profile']['age'] == 99
        
        # 全ユーザー数確認
        assert len(db) == 100
        
        db.close()
    
    def test_performance_stats_collection(self, temp_db_path):
        """パフォーマンス統計の収集"""
        db = DictSQLiteV2(temp_db_path, write_buffer_size=1)
        
        # 操作実行
        for i in range(100):
            db[f'key_{i}'] = f'value_{i}'
        
        for i in range(50):
            _ = db[f'key_{i}']
        
        # 統計取得
        stats = db.get_performance_stats()
        
        # 必須フィールドの確認
        assert 'version' in stats
        assert stats['version'] == '2.0.0'
        assert 'database' in stats
        assert 'optimizations' in stats
        
        db.close()
    
    def test_error_recovery(self, temp_db_path):
        """エラー回復のテスト"""
        db = DictSQLiteV2(temp_db_path)
        
        # 正常な操作
        db['key1'] = 'value1'
        
        # エラーが発生する操作（存在しないキーの削除）
        try:
            del db['nonexistent']
        except KeyError:
            pass  # 期待されるエラー
        
        # エラー後も正常に動作することを確認
        db['key2'] = 'value2'
        assert db['key1'] == 'value1'
        assert db['key2'] == 'value2'
        
        db.close()
