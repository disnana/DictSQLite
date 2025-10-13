#!/usr/bin/env python3
"""
Test for issue fixes:
1. AsyncDictSQLite.set_async() and get_async() methods
2. safe_pickle import path
"""

import tempfile
import os
import pytest


def test_async_set_get_async_methods():
    """Test that set_async and get_async methods exist and work"""
    from dictsqlite import AsyncDictSQLite
    
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    try:
        db = AsyncDictSQLite(
            db_path, 
            capacity=1000, 
            persist_mode='writethrough', 
            buffer_size=10
        )
        
        # Test set_async method exists and works
        for i in range(10):
            db.set_async(f'key_{i}', f'value_{i}'.encode())
        
        # Test get_async method exists and works
        value = db.get_async('key_0')
        assert value == b'value_0', f"Expected b'value_0', got {value}"
        
        # Test flush
        db.flush()
        
        # Verify value persists
        value = db.get_async('key_5')
        assert value == b'value_5', f"Expected b'value_5', got {value}"
        
        db.close()
        
    finally:
        for ext in ['', '-wal', '-shm']:
            try:
                os.unlink(db_path + ext)
            except:
                pass


def test_safe_pickle_import():
    """Test that safe_pickle can be imported and used correctly"""
    from dictsqlite import DictSQLite
    
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    try:
        # Test with safe_pickle enabled - this should trigger the safe_pickle import
        db = DictSQLite(
            db_path, 
            hot_capacity=1000, 
            storage_mode='pickle',
            enable_safe_pickle=True,
            safe_pickle_allowed_modules=['test_module']
        )
        
        # Basic operations should work
        db['key1'] = b'value1'
        assert db['key1'] == b'value1'
        
        db['key2'] = b'value2'
        assert db['key2'] == b'value2'
        
        db.close()
        
    finally:
        for ext in ['', '-wal', '-shm']:
            try:
                os.unlink(db_path + ext)
            except:
                pass


def test_async_dict_sqlite_backward_compatibility():
    """Test that AsyncDictSQLite maintains backward compatibility"""
    from dictsqlite import AsyncDictSQLite
    
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    try:
        db = AsyncDictSQLite(db_path, capacity=1000)
        
        # Old sync methods should still work
        db.set('key1', b'value1')
        assert db.get('key1') == b'value1'
        
        # New set_async/get_async methods should also work
        db.set_async('key2', b'value2')
        assert db.get_async('key2') == b'value2'
        
        # Both should be interchangeable
        db.set('key3', b'value3')
        assert db.get_async('key3') == b'value3'
        
        db.set_async('key4', b'value4')
        assert db.get('key4') == b'value4'
        
        db.close()
        
    finally:
        for ext in ['', '-wal', '-shm']:
            try:
                os.unlink(db_path + ext)
            except:
                pass


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
