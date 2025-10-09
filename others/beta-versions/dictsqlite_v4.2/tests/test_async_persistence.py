#!/usr/bin/env python3
"""
Test AsyncDictSQLite persistence functionality (Phase 1, Task 1.1)
"""
import tempfile
import os
import sys
import time

# Import the built module
try:
    from dictsqlite import AsyncDictSQLite
except ImportError:
    print("Error: dictsqlite module not found. Please build with 'maturin develop'")
    sys.exit(1)


def cleanup_db_files(db_path):
    """
    データベースファイルとWALファイルをクリーンアップ
    Windows対応: リトライロジック付き
    """
    # 小さな遅延でファイルハンドルが確実に解放されるのを待つ
    time.sleep(0.1)
    
    for attempt in range(3):
        try:
            if os.path.exists(db_path):
                os.unlink(db_path)
            # WALファイルもクリーンアップ
            for ext in ['-wal', '-shm']:
                wal_file = db_path + ext
                if os.path.exists(wal_file):
                    os.unlink(wal_file)
            break
        except PermissionError:
            if attempt < 2:
                time.sleep(0.2)  # 200ms待機してリトライ
            # 最後の試行でも失敗した場合は無視
        except Exception:
            # その他のエラーは無視
            break


def test_async_persistence_lazy_mode():
    """Test AsyncDictSQLite with lazy persistence mode"""
    print("\n" + "="*60)
    print("Test 1: AsyncDictSQLite Lazy Persistence")
    print("="*60)
    
    # Create temporary database file
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    try:
        # Test 1: Write data with lazy mode
        print("Step 1: Creating AsyncDictSQLite with lazy mode...")
        db1 = AsyncDictSQLite(db_path, capacity=1000, persist_mode="lazy")
        
        print("Step 2: Writing test data...")
        db1.set_async("key1", b"value1")
        db1.set_async("key2", b"value2")
        db1.set_async("key3", b"value3")
        
        print("Step 3: Verifying in-memory reads...")
        assert db1.get_async("key1") == b"value1", "Failed to read key1 from cache"
        assert db1.get_async("key2") == b"value2", "Failed to read key2 from cache"
        assert db1.get_async("key3") == b"value3", "Failed to read key3 from cache"
        print("✓ In-memory reads successful")
        
        print("Step 4: Flushing to disk...")
        db1.flush()
        
        print("Step 5: Closing database...")
        db1.close()
        
        # Test 2: Read persisted data in new instance
        print("\nStep 6: Creating new AsyncDictSQLite instance...")
        db2 = AsyncDictSQLite(db_path, capacity=1000, persist_mode="lazy")
        
        print("Step 7: Reading persisted data...")
        assert db2.get_async("key1") == b"value1", "Failed to read persisted key1"
        assert db2.get_async("key2") == b"value2", "Failed to read persisted key2"
        assert db2.get_async("key3") == b"value3", "Failed to read persisted key3"
        print("✓ Persisted data read successfully")
        
        db2.close()
        
        print("\n✅ Test PASSED: Lazy persistence works correctly")
        
    except Exception as e:
        print(f"\n❌ Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        cleanup_db_files(db_path)


def test_async_persistence_writethrough_mode():
    """Test AsyncDictSQLite with writethrough persistence mode"""
    print("\n" + "="*60)
    print("Test 2: AsyncDictSQLite WriteThrough Persistence")
    print("="*60)
    
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    try:
        print("Step 1: Creating AsyncDictSQLite with writethrough mode...")
        db1 = AsyncDictSQLite(db_path, capacity=1000, persist_mode="writethrough")
        
        print("Step 2: Writing test data (should persist immediately)...")
        db1.set_async("key_wt1", b"value_wt1")
        db1.set_async("key_wt2", b"value_wt2")
        
        print("Step 3: Verifying in-memory reads...")
        assert db1.get_async("key_wt1") == b"value_wt1"
        assert db1.get_async("key_wt2") == b"value_wt2"
        print("✓ In-memory reads successful")
        
        # No explicit flush needed for writethrough
        db1.close()
        
        print("\nStep 4: Reading from new instance (data should already be persisted)...")
        db2 = AsyncDictSQLite(db_path, capacity=1000, persist_mode="writethrough")
        
        assert db2.get_async("key_wt1") == b"value_wt1", "Failed to read persisted key_wt1"
        assert db2.get_async("key_wt2") == b"value_wt2", "Failed to read persisted key_wt2"
        print("✓ Persisted data read successfully (without explicit flush)")
        
        db2.close()
        
        print("\n✅ Test PASSED: WriteThrough persistence works correctly")
        
    except Exception as e:
        print(f"\n❌ Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        cleanup_db_files(db_path)


def test_async_persistence_memory_mode():
    """Test AsyncDictSQLite with memory-only mode (no persistence)"""
    print("\n" + "="*60)
    print("Test 3: AsyncDictSQLite Memory-Only Mode")
    print("="*60)
    
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    try:
        print("Step 1: Creating AsyncDictSQLite with memory mode...")
        db1 = AsyncDictSQLite(db_path, capacity=1000, persist_mode="memory")
        
        print("Step 2: Writing test data...")
        db1.set_async("mem_key1", b"mem_value1")
        db1.set_async("mem_key2", b"mem_value2")
        
        print("Step 3: Verifying in-memory reads...")
        assert db1.get_async("mem_key1") == b"mem_value1"
        assert db1.get_async("mem_key2") == b"mem_value2"
        print("✓ In-memory reads successful")
        
        db1.close()
        
        print("\nStep 4: Creating new instance (data should NOT be persisted)...")
        db2 = AsyncDictSQLite(db_path, capacity=1000, persist_mode="memory")
        
        assert db2.get_async("mem_key1") is None, "Memory-only data should not persist"
        assert db2.get_async("mem_key2") is None, "Memory-only data should not persist"
        print("✓ Data correctly NOT persisted in memory mode")
        
        db2.close()
        
        print("\n✅ Test PASSED: Memory-only mode works correctly")
        
    except Exception as e:
        print(f"\n❌ Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        cleanup_db_files(db_path)


def test_async_batch_operations_with_persistence():
    """Test batch operations with persistence"""
    print("\n" + "="*60)
    print("Test 4: AsyncDictSQLite Batch Operations with Persistence")
    print("="*60)
    
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    try:
        print("Step 1: Creating AsyncDictSQLite...")
        db1 = AsyncDictSQLite(db_path, capacity=10000, persist_mode="lazy")
        
        print("Step 2: Batch writing 100 items...")
        items = [(f"batch_key_{i}", f"batch_value_{i}".encode()) for i in range(100)]
        db1.batch_set(items)
        
        print("Step 3: Batch reading...")
        keys = [f"batch_key_{i}" for i in range(100)]
        results = db1.batch_get(keys)
        
        assert len(results) == 100
        assert all(r is not None for r in results), "Some batch items not found"
        print("✓ Batch read successful")
        
        print("Step 4: Flushing and closing...")
        db1.flush()
        db1.close()
        
        print("Step 5: Verifying persistence...")
        db2 = AsyncDictSQLite(db_path, capacity=10000, persist_mode="lazy")
        results2 = db2.batch_get(keys[:10])  # Check first 10
        assert len(results2) == 10
        assert all(r is not None for r in results2), "Persisted batch items not found"
        print("✓ Batch persistence verified")
        
        db2.close()
        
        print("\n✅ Test PASSED: Batch operations with persistence work correctly")
        
    except Exception as e:
        print(f"\n❌ Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        cleanup_db_files(db_path)


def run_all_tests():
    """Run all AsyncDictSQLite persistence tests"""
    print("\n" + "="*60)
    print("AsyncDictSQLite Persistence Test Suite (Phase 1, Task 1.1)")
    print("="*60)
    
    tests = [
        ("Lazy Persistence", test_async_persistence_lazy_mode),
        ("WriteThrough Persistence", test_async_persistence_writethrough_mode),
        ("Memory-Only Mode", test_async_persistence_memory_mode),
        ("Batch Operations with Persistence", test_async_batch_operations_with_persistence),
    ]
    
    results = []
    for name, test_func in tests:
        result = test_func()
        results.append((name, result))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests PASSED! AsyncDictSQLite persistence is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) FAILED. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
