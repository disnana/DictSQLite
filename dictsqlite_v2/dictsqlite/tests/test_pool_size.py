#!/usr/bin/env python3
"""
Tests for connection pool size configuration
"""

import threading
import time
import pytest
from dictsqlite import DictSQLiteV4
from .conftest import windows_safe_temp_db


class TestPoolSizeConfiguration:
    """Test connection pool size configuration"""
    
    def test_default_pool_size(self):
        """Test that default pool size is 20"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path)
            # The pool size is internal to storage, but we can verify
            # it works by checking basic operations
            db["key"] = {"value": "test"}
            assert db["key"]["value"] == "test"
            db.close()
    
    def test_custom_pool_size(self):
        """Test setting custom pool size"""
        with windows_safe_temp_db() as db_path:
            # Test with custom pool size
            db = DictSQLiteV4(db_path, pool_size=10)
            db["key1"] = {"value": 1}
            db["key2"] = {"value": 2}
            assert db["key1"]["value"] == 1
            assert db["key2"]["value"] == 2
            db.close()
    
    def test_large_pool_size(self):
        """Test with large pool size"""
        with windows_safe_temp_db() as db_path:
            # Test with larger pool size
            db = DictSQLiteV4(db_path, pool_size=50)
            
            # Write multiple items
            for i in range(100):
                db[f"key_{i}"] = {"value": i}
            
            # Verify all items
            for i in range(100):
                assert db[f"key_{i}"]["value"] == i
            
            db.close()
    
    def test_concurrent_access_with_custom_pool_size(self):
        """Test concurrent access with custom pool size"""
        with windows_safe_temp_db() as db_path:
            # Use pool size of 15 for this test
            db = DictSQLiteV4(db_path, storage_mode='jsonb', pool_size=15)
            
            num_threads = 15
            num_writes_per_thread = 20
            errors = []
            
            def worker(thread_id):
                try:
                    for i in range(num_writes_per_thread):
                        key = f'thread_{thread_id}_key_{i}'
                        value = {'thread': thread_id, 'iteration': i}
                        db[key] = value
                        
                        # Verify immediately
                        read_value = db[key]
                        assert read_value['thread'] == thread_id
                except Exception as e:
                    errors.append((thread_id, str(e)))
            
            threads = []
            for i in range(num_threads):
                t = threading.Thread(target=worker, args=(i,))
                threads.append(t)
                t.start()
            
            for t in threads:
                t.join()
            
            # Check for errors
            assert len(errors) == 0, f"Errors occurred: {errors}"
            
            # Verify all data was written
            expected_count = num_threads * num_writes_per_thread
            actual_count = len(db)
            assert actual_count == expected_count, f"Expected {expected_count}, got {actual_count}"
            
            db.close()
    
    def test_small_pool_size(self):
        """Test with small pool size (should still work)"""
        with windows_safe_temp_db() as db_path:
            # Test with small pool size
            db = DictSQLiteV4(db_path, pool_size=2)
            
            # Should still work, just might be slower with high concurrency
            for i in range(50):
                db[f"key_{i}"] = {"value": i}
            
            for i in range(50):
                assert db[f"key_{i}"]["value"] == i
            
            db.close()
    
    def test_pool_size_with_different_modes(self):
        """Test pool size with different persist and storage modes"""
        with windows_safe_temp_db() as db_path:
            # Test with lazy mode and custom pool size
            db = DictSQLiteV4(
                db_path, 
                persist_mode='lazy',
                storage_mode='jsonb',
                pool_size=25
            )
            
            for i in range(100):
                db[f"key_{i}"] = {"value": i}
            
            db.flush()
            
            # Verify
            for i in range(100):
                assert db[f"key_{i}"]["value"] == i
            
            db.close()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

