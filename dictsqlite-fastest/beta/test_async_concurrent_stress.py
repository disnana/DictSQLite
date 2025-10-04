"""
Concurrent stress test for AsyncDictSQLiteFastestBeta.

This test validates that the database lock issue is fixed by running
multiple concurrent operations simultaneously.
"""
import asyncio
import tempfile
import os
import sys
import pytest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))
from dictsqlite_fastest_beta import AsyncDictSQLiteFastestBeta


class TestAsyncConcurrentStress:
    """Stress tests for concurrent async operations."""
    
    def setup_method(self):
        """各テストの前に実行."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test_concurrent.db')
    
    def teardown_method(self):
        """各テストの後に実行."""
        # クリーンアップ
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)
    
    def test_concurrent_writes(self):
        """並行書き込みのストレステスト."""
        async def async_test():
            async with AsyncDictSQLiteFastestBeta(self.db_path) as db:
                # 100個の並行書き込み
                tasks = []
                for i in range(100):
                    tasks.append(db.aset(f'key_{i}', f'value_{i}'))
                
                await asyncio.gather(*tasks)
                
                # データが正しく書き込まれたことを確認
                for i in range(100):
                    value = await db.aget(f'key_{i}')
                    assert value == f'value_{i}', f'Expected value_{i}, got {value}'
        
        asyncio.run(async_test())
    
    def test_concurrent_reads(self):
        """並行読み込みのストレステスト."""
        async def async_test():
            async with AsyncDictSQLiteFastestBeta(self.db_path) as db:
                # データを準備
                for i in range(100):
                    await db.aset(f'key_{i}', f'value_{i}')
                
                # 100個の並行読み込み
                tasks = []
                for i in range(100):
                    tasks.append(db.aget(f'key_{i}'))
                
                results = await asyncio.gather(*tasks)
                
                # すべての結果が正しいことを確認
                for i, result in enumerate(results):
                    assert result == f'value_{i}', f'Expected value_{i}, got {result}'
        
        asyncio.run(async_test())
    
    def test_mixed_concurrent_operations(self):
        """読み書き混合の並行操作のストレステスト."""
        async def async_test():
            async with AsyncDictSQLiteFastestBeta(self.db_path) as db:
                # 初期データを準備
                for i in range(50):
                    await db.aset(f'key_{i}', f'initial_value_{i}')
                
                # 読み書き混合の並行操作
                tasks = []
                
                # 50個の更新
                for i in range(50):
                    tasks.append(db.aset(f'key_{i}', f'updated_value_{i}'))
                
                # 50個の新規書き込み
                for i in range(50, 100):
                    tasks.append(db.aset(f'key_{i}', f'new_value_{i}'))
                
                # 100個の読み込み
                for i in range(100):
                    tasks.append(db.aget(f'key_{i}', 'default'))
                
                await asyncio.gather(*tasks)
                
                # 最終状態を確認
                for i in range(50):
                    value = await db.aget(f'key_{i}')
                    assert value == f'updated_value_{i}'
                
                for i in range(50, 100):
                    value = await db.aget(f'key_{i}')
                    assert value == f'new_value_{i}'
        
        asyncio.run(async_test())
    
    def test_concurrent_bulk_operations(self):
        """並行バルク操作のストレステスト."""
        async def async_test():
            async with AsyncDictSQLiteFastestBeta(self.db_path) as db:
                # 複数のバルク挿入を並行実行
                tasks = []
                for batch in range(10):
                    bulk_data = {
                        f'batch{batch}_key_{i}': f'batch{batch}_value_{i}'
                        for i in range(100)
                    }
                    tasks.append(db.abulk_insert(bulk_data))
                
                await asyncio.gather(*tasks)
                
                # データが正しく挿入されたことを確認
                for batch in range(10):
                    for i in range(0, 100, 10):  # サンプリング
                        key = f'batch{batch}_key_{i}'
                        value = await db.aget(key)
                        expected = f'batch{batch}_value_{i}'
                        assert value == expected, f'Expected {expected}, got {value}'
        
        asyncio.run(async_test())
    
    def test_high_concurrency_stress(self):
        """高並行度ストレステスト (500 operations)."""
        async def async_test():
            async with AsyncDictSQLiteFastestBeta(self.db_path) as db:
                # 500個の並行書き込み
                tasks = []
                for i in range(500):
                    tasks.append(db.aset(f'stress_key_{i}', {'id': i, 'data': f'stress_value_{i}'}))
                
                await asyncio.gather(*tasks)
                
                # ランダムサンプリングで検証
                import random
                sample_indices = random.sample(range(500), 50)
                
                for i in sample_indices:
                    value = await db.aget(f'stress_key_{i}')
                    assert value['id'] == i
                    assert value['data'] == f'stress_value_{i}'
        
        asyncio.run(async_test())
    
    def test_concurrent_delete_operations(self):
        """並行削除操作のテスト."""
        async def async_test():
            async with AsyncDictSQLiteFastestBeta(self.db_path) as db:
                # データを準備
                for i in range(100):
                    await db.aset(f'key_{i}', f'value_{i}')
                
                # 並行削除
                tasks = []
                for i in range(0, 100, 2):  # 偶数キーを削除
                    tasks.append(db.adelete(f'key_{i}'))
                
                await asyncio.gather(*tasks)
                
                # 削除されたキーが存在しないことを確認
                for i in range(0, 100, 2):
                    value = await db.aget(f'key_{i}', 'DELETED')
                    assert value == 'DELETED', f'Key {i} should be deleted'
                
                # 削除されていないキーが存在することを確認
                for i in range(1, 100, 2):
                    value = await db.aget(f'key_{i}')
                    assert value == f'value_{i}'
        
        asyncio.run(async_test())
    
    def test_concurrent_with_flush(self):
        """並行操作とフラッシュのテスト."""
        async def async_test():
            async with AsyncDictSQLiteFastestBeta(self.db_path) as db:
                # 書き込みとフラッシュを混在
                tasks = []
                
                for i in range(50):
                    tasks.append(db.aset(f'key_{i}', f'value_{i}'))
                
                # 途中でフラッシュを実行
                tasks.append(db.aflush())
                
                for i in range(50, 100):
                    tasks.append(db.aset(f'key_{i}', f'value_{i}'))
                
                await asyncio.gather(*tasks)
                
                # すべてのデータが正しく保存されているか確認
                for i in range(100):
                    value = await db.aget(f'key_{i}')
                    assert value == f'value_{i}'
        
        asyncio.run(async_test())


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
