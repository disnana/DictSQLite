"""DictSQLite-Fastest Beta のテスト.

pytest を使用してベータ版の機能をテストします。
"""

import sys
import os
import tempfile
from pathlib import Path

# ベータモジュールのパスを追加
sys.path.insert(0, str(Path(__file__).parent))

from dictsqlite_fastest_beta import (
    DictSQLiteFastestBeta,
    LRUCache,
    WriteBuffer
)


class TestLRUCache:
    """LRUキャッシュのテスト."""
    
    def test_basic_operations(self):
        """基本的な操作のテスト."""
        cache = LRUCache(capacity=3)
        
        # 追加
        cache.put('key1', 'value1')
        cache.put('key2', 'value2')
        cache.put('key3', 'value3')
        
        # 取得
        assert cache.get('key1') == 'value1'
        assert cache.get('key2') == 'value2'
        assert cache.get('key3') == 'value3'
    
    def test_capacity_limit(self):
        """容量制限のテスト."""
        cache = LRUCache(capacity=2)
        
        cache.put('key1', 'value1')
        cache.put('key2', 'value2')
        cache.put('key3', 'value3')  # key1が削除されるはず
        
        assert cache.get('key1') is None  # 削除された
        assert cache.get('key2') == 'value2'
        assert cache.get('key3') == 'value3'
    
    def test_lru_eviction(self):
        """LRU方式の削除のテスト."""
        cache = LRUCache(capacity=2)
        
        cache.put('key1', 'value1')
        cache.put('key2', 'value2')
        cache.get('key1')  # key1を最近使用したことにする
        cache.put('key3', 'value3')  # key2が削除されるはず
        
        assert cache.get('key1') == 'value1'
        assert cache.get('key2') is None  # 削除された
        assert cache.get('key3') == 'value3'
    
    def test_statistics(self):
        """統計情報のテスト."""
        cache = LRUCache(capacity=3)
        
        cache.put('key1', 'value1')
        cache.put('key2', 'value2')
        
        cache.get('key1')  # ヒット
        cache.get('key2')  # ヒット
        cache.get('key3')  # ミス
        
        stats = cache.get_stats()
        assert stats['hits'] == 2
        assert stats['misses'] == 1
        assert stats['size'] == 2


class TestWriteBuffer:
    """書き込みバッファのテスト."""
    
    def test_basic_operations(self):
        """基本的な操作のテスト."""
        buffer = WriteBuffer(flush_threshold=5, flush_interval=10.0)
        
        # 追加
        buffer.add('key1', 'value1')
        buffer.add('key2', 'value2')
        
        # 保留中のデータを確認
        assert buffer.has_pending()
    
    def test_flush_on_size(self):
        """サイズによるフラッシュのテスト."""
        buffer = WriteBuffer(flush_threshold=3, flush_interval=100.0)
        
        assert not buffer.add('key1', 'value1')
        assert not buffer.add('key2', 'value2')
        assert buffer.add('key3', 'value3')  # 閾値に達した
    
    def test_get_pending_data(self):
        """保留中のデータ取得のテスト."""
        buffer = WriteBuffer(flush_threshold=10, flush_interval=100.0)
        
        buffer.add('key1', 'value1')
        buffer.add('key2', 'value2')
        buffer.remove('key3')
        
        data, deleted = buffer.get_pending_data()
        
        assert data == {'key1': 'value1', 'key2': 'value2'}
        assert deleted == {'key3'}
        assert not buffer.has_pending()


class TestDictSQLiteFastestBeta:
    """DictSQLiteFastestBetaのテスト."""
    
    def setup_method(self):
        """各テストの前に実行."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test.db')
    
    def teardown_method(self):
        """各テストの後に実行."""
        # クリーンアップ
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)
    
    def test_basic_operations(self):
        """基本的な操作のテスト."""
        with DictSQLiteFastestBeta(self.db_path, cache_capacity=100) as db:
            # 書き込み
            db['key1'] = 'value1'
            db['key2'] = {'nested': 'value2'}
            
            # 読み込み
            assert db['key1'] == 'value1'
            assert db['key2'] == {'nested': 'value2'}
            
            # 存在確認
            assert 'key1' in db
            assert 'key3' not in db
            
            # 削除
            del db['key1']
            assert 'key1' not in db
    
    def test_cache_hit(self):
        """キャッシュヒットのテスト."""
        with DictSQLiteFastestBeta(self.db_path, cache_capacity=100) as db:
            db['key1'] = 'value1'
            
            # 最初のアクセス（書き込みバッファ経由）
            value1 = db['key1']
            
            # 2回目のアクセス（キャッシュヒット）
            value2 = db['key1']
            
            assert value1 == value2
            
            stats = db.get_beta_stats()
            assert stats['cache']['hits'] > 0
    
    def test_write_buffering(self):
        """書き込みバッファリングのテスト."""
        with DictSQLiteFastestBeta(
            self.db_path,
            cache_capacity=100,
            write_buffer_size=5
        ) as db:
            # 少量の書き込み
            db['key1'] = 'value1'
            db['key2'] = 'value2'
            
            stats = db.get_beta_stats()
            # バッファに蓄積されている
            assert stats['buffer']['pending_writes'] > 0
            
            # フラッシュ
            db.flush()
            
            stats = db.get_beta_stats()
            # バッファが空になった
            assert stats['buffer']['pending_writes'] == 0
    
    def test_bulk_operations(self):
        """バルク操作のテスト."""
        with DictSQLiteFastestBeta(self.db_path, cache_capacity=1000) as db:
            # バルク挿入
            data = {f'key_{i}': f'value_{i}' for i in range(100)}
            db.bulk_insert(data)
            
            # バルク取得
            keys = [f'key_{i}' for i in range(0, 100, 10)]
            results = db.bulk_get(keys)
            
            assert len(results) == 10
            assert results['key_0'] == 'value_0'
    
    def test_memory_only_mode(self):
        """メモリオンリーモードのテスト."""
        with DictSQLiteFastestBeta(':memory:', table_name='test_table', memory_only=True) as db:
            db['key1'] = 'value1'
            db['key2'] = 'value2'
            
            assert db['key1'] == 'value1'
            assert db['key2'] == 'value2'
            
            stats = db.get_beta_stats()
            assert stats['config']['memory_only'] is True
    
    def test_prefetch(self):
        """先読みキャッシングのテスト."""
        with DictSQLiteFastestBeta(self.db_path, cache_capacity=1000) as db:
            # データを準備
            data = {f'key_{i}': f'value_{i}' for i in range(100)}
            db.bulk_insert(data)
            db.flush()
            
            # キャッシュをクリア
            db.clear_cache()
            
            # 先読み
            keys = [f'key_{i}' for i in range(10)]
            db.prefetch_keys(keys)
            
            # キャッシュに入っているはず
            stats1 = db.get_beta_stats()
            cache_size1 = stats1['cache']['size']
            
            assert cache_size1 >= len(keys)
    
    def test_statistics(self):
        """統計情報のテスト."""
        with DictSQLiteFastestBeta(self.db_path, cache_capacity=100) as db:
            # 操作を実行
            db['key1'] = 'value1'
            _ = db['key1']
            db['key2'] = 'value2'
            
            stats = db.get_beta_stats()
            
            # 統計情報が取得できることを確認
            assert 'cache' in stats
            assert 'operations' in stats
            assert 'buffer' in stats
            assert 'config' in stats
            
            assert stats['cache']['capacity'] == 100
            assert stats['config']['cache_capacity'] == 100
    
    def test_context_manager(self):
        """コンテキストマネージャのテスト."""
        # コンテキストマネージャとして使用
        with DictSQLiteFastestBeta(self.db_path) as db:
            db['key1'] = 'value1'
        
        # 再度開いてデータが保存されているか確認
        with DictSQLiteFastestBeta(self.db_path) as db:
            assert db['key1'] == 'value1'
    
    def test_get_with_default(self):
        """getメソッドのテスト."""
        with DictSQLiteFastestBeta(self.db_path) as db:
            db['key1'] = 'value1'
            
            assert db.get('key1') == 'value1'
            assert db.get('key2', 'default') == 'default'
            assert db.get('key3') is None
    
    def test_aggressive_memory_settings(self):
        """アグレッシブメモリ設定のテスト."""
        with DictSQLiteFastestBeta(
            self.db_path,
            aggressive_memory=True
        ) as db:
            stats = db.get_beta_stats()
            assert stats['config']['aggressive_memory'] is True
            
            # データ操作が正常に動作することを確認
            db['key1'] = 'value1'
            assert db['key1'] == 'value1'


def run_tests():
    """テストを実行（pytestがない場合の代替）."""
    import traceback
    
    test_classes = [TestLRUCache, TestWriteBuffer, TestDictSQLiteFastestBeta]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    
    for test_class in test_classes:
        print(f"\n{'=' * 60}")
        print(f"Testing {test_class.__name__}")
        print(f"{'=' * 60}")
        
        test_instance = test_class()
        
        # テストメソッドを取得
        test_methods = [m for m in dir(test_instance) if m.startswith('test_')]
        
        for method_name in test_methods:
            total_tests += 1
            
            # setup_method を実行（存在する場合）
            if hasattr(test_instance, 'setup_method'):
                test_instance.setup_method()
            
            try:
                method = getattr(test_instance, method_name)
                method()
                print(f"✓ {method_name}")
                passed_tests += 1
            except Exception as e:
                print(f"✗ {method_name}")
                print(f"  Error: {e}")
                traceback.print_exc()
                failed_tests += 1
            finally:
                # teardown_method を実行（存在する場合）
                if hasattr(test_instance, 'teardown_method'):
                    try:
                        test_instance.teardown_method()
                    except Exception:
                        pass
    
    print(f"\n{'=' * 60}")
    print(f"Test Results")
    print(f"{'=' * 60}")
    print(f"Total: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Success Rate: {passed_tests/total_tests*100:.1f}%")
    
    return failed_tests == 0


if __name__ == '__main__':
    # pytestが利用可能か確認
    try:
        import pytest
        print("Running tests with pytest...")
        pytest.main([__file__, '-v'])
    except ImportError:
        print("pytest not available, running tests manually...")
        success = run_tests()
        sys.exit(0 if success else 1)
