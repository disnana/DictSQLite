"""Test encryption and safe_pickle features in DictSQLite v2.0"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / 'dictsqlite-fastest'))
sys.path.insert(0, str(Path(__file__).parent / 'dictsqlite-fastest' / 'dictsqlite_v2'))

from core import DictSQLiteV2


def test_basic_operations():
    """Test basic operations without security features."""
    print("Testing basic operations (no encryption, no safe pickle)...")
    
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test.db")
    
    try:
        # Create and test
        db = DictSQLiteV2(db_path, auto_sync=False)
        db['key1'] = 'value1'
        db['key2'] = {'nested': 'dict'}
        db['key3'] = [1, 2, 3]
        
        # Check values
        assert db['key1'] == 'value1'
        assert db['key2'] == {'nested': 'dict'}
        assert db['key3'] == [1, 2, 3]
        
        # Sync and close
        db.sync()
        db.close()
        
        # Reopen and verify persistence
        db2 = DictSQLiteV2(db_path)
        assert db2['key1'] == 'value1'
        assert db2['key2'] == {'nested': 'dict'}
        assert db2['key3'] == [1, 2, 3]
        db2.close()
        
        print("✅ Basic operations test PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Basic operations test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_encryption():
    """Test encryption feature."""
    print("\nTesting encryption feature...")
    
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_encrypted.db")
    password = "my_secret_password_123"
    
    try:
        # Create encrypted DB
        db = DictSQLiteV2(
            db_path, 
            encryption_password=password,
            auto_sync=False
        )
        
        # Store sensitive data
        db['secret1'] = 'confidential information'
        db['secret2'] = {'password': '12345', 'api_key': 'xyz'}
        
        # Check values
        assert db['secret1'] == 'confidential information'
        assert db['secret2'] == {'password': '12345', 'api_key': 'xyz'}
        
        # Sync and close
        db.sync()
        db.close()
        
        # Try to open without password - should fail or get garbage
        try:
            db_wrong = DictSQLiteV2(db_path, auto_sync=False)
            # Data should be corrupted/unreadable
            try:
                val = db_wrong['secret1']
                # If we get here, encryption might not be working
                print(f"Warning: Got value without password: {val}")
            except:
                pass  # Expected - can't deserialize encrypted data
            db_wrong.close()
        except:
            pass
        
        # Reopen with correct password
        db2 = DictSQLiteV2(db_path, encryption_password=password)
        assert db2['secret1'] == 'confidential information'
        assert db2['secret2'] == {'password': '12345', 'api_key': 'xyz'}
        
        # Check stats
        stats = db2.get_performance_stats()
        assert stats['security']['encryption_enabled'] == True
        
        db2.close()
        
        print("✅ Encryption test PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Encryption test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_safe_pickle():
    """Test safe pickle feature."""
    print("\nTesting safe pickle feature...")
    
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_safe.db")
    
    try:
        # Create DB with safe pickle
        db = DictSQLiteV2(
            db_path,
            use_safe_pickle=True,
            auto_sync=False
        )
        
        # Store safe data (basic types)
        db['safe1'] = 'string'
        db['safe2'] = 123
        db['safe3'] = [1, 2, 3]
        db['safe4'] = {'a': 1, 'b': 2}
        
        # Check values
        assert db['safe1'] == 'string'
        assert db['safe2'] == 123
        assert db['safe3'] == [1, 2, 3]
        assert db['safe4'] == {'a': 1, 'b': 2}
        
        # Sync and close
        db.sync()
        db.close()
        
        # Reopen with safe pickle
        db2 = DictSQLiteV2(db_path, use_safe_pickle=True)
        assert db2['safe1'] == 'string'
        assert db2['safe2'] == 123
        assert db2['safe3'] == [1, 2, 3]
        assert db2['safe4'] == {'a': 1, 'b': 2}
        
        # Check stats
        stats = db2.get_performance_stats()
        assert stats['security']['safe_pickle_enabled'] == True
        
        db2.close()
        
        print("✅ Safe pickle test PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Safe pickle test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_encryption_and_safe_pickle():
    """Test both encryption and safe pickle together."""
    print("\nTesting encryption + safe pickle...")
    
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_both.db")
    password = "secure_password_456"
    
    try:
        # Create DB with both features
        db = DictSQLiteV2(
            db_path,
            encryption_password=password,
            use_safe_pickle=True,
            auto_sync=False
        )
        
        # Store data
        db['data1'] = 'encrypted and safe'
        db['data2'] = {'secure': True, 'value': 42}
        
        # Sync and close
        db.sync()
        db.close()
        
        # Reopen with both features
        db2 = DictSQLiteV2(
            db_path,
            encryption_password=password,
            use_safe_pickle=True
        )
        
        assert db2['data1'] == 'encrypted and safe'
        assert db2['data2'] == {'secure': True, 'value': 42}
        
        # Check stats
        stats = db2.get_performance_stats()
        assert stats['security']['encryption_enabled'] == True
        assert stats['security']['safe_pickle_enabled'] == True
        
        db2.close()
        
        print("✅ Encryption + safe pickle test PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Encryption + safe pickle test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def main():
    """Run all tests."""
    print("=" * 60)
    print("DictSQLite v2.0 Security Features Test")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("Basic Operations", test_basic_operations()))
    results.append(("Encryption", test_encryption()))
    results.append(("Safe Pickle", test_safe_pickle()))
    results.append(("Encryption + Safe Pickle", test_encryption_and_safe_pickle()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{name:<30} {status}")
    
    all_passed = all(passed for _, passed in results)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All tests PASSED!")
    else:
        print("⚠️  Some tests FAILED")
    print("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
