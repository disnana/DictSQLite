#!/usr/bin/env python3
"""
Test AsyncDictSQLite true async/await functionality
Tests the new awaitable async methods (aget, aset, abatch_get, abatch_set)
"""
import asyncio
import tempfile
import os
import sys
import time
import pytest

# Add the parent directory to path to import the wrapper
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the Python wrapper (not the native module directly)
try:
    import __init__ as wrapper_module
    AsyncDictSQLite = wrapper_module.AsyncDictSQLite
except ImportError as e:
    print(f"Error importing wrapper: {e}")
    print("Trying direct import...")
    try:
        from dictsqlite import AsyncDictSQLite
        print("Warning: Using native AsyncDictSQLite directly (async context manager not available)")
    except ImportError:
        print("Error: Could not import AsyncDictSQLite")
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


@pytest.mark.asyncio
async def test_async_get_set():
    """Test basic async get/set operations"""
    print("\n" + "="*60)
    print("Test 1: Async Get/Set (Awaitable)")
    print("="*60)
    
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    try:
        async with AsyncDictSQLite(db_path, capacity=1000, persist_mode="lazy") as db:
            print("Step 1: Testing async set...")
            await db.aset("key1", b"value1")
            await db.aset("key2", b"value2")
            await db.aset("key3", b"value3")
            print("✓ Async set successful")
            
            print("Step 2: Testing async get...")
            result1 = await db.aget("key1")
            result2 = await db.aget("key2")
            result3 = await db.aget("key3")
            
            assert result1 == b"value1", f"Expected b'value1', got {result1}"
            assert result2 == b"value2", f"Expected b'value2', got {result2}"
            assert result3 == b"value3", f"Expected b'value3', got {result3}"
            print("✓ Async get successful")
            
            print("Step 3: Testing async get for missing key...")
            result_missing = await db.aget("nonexistent")
            assert result_missing is None, f"Expected None, got {result_missing}"
            print("✓ Missing key returns None")
        
        print("\n✅ Test PASSED: Async get/set works correctly")
        return True
        
    except Exception as e:
        print(f"\n❌ Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        cleanup_db_files(db_path)


@pytest.mark.asyncio
async def test_async_batch_operations():
    """Test async batch operations"""
    print("\n" + "="*60)
    print("Test 2: Async Batch Operations (Awaitable)")
    print("="*60)
    
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    try:
        async with AsyncDictSQLite(db_path, capacity=1000, persist_mode="lazy") as db:
            print("Step 1: Testing async batch set...")
            items = [
                ("batch_key1", b"batch_value1"),
                ("batch_key2", b"batch_value2"),
                ("batch_key3", b"batch_value3"),
                ("batch_key4", b"batch_value4"),
                ("batch_key5", b"batch_value5"),
            ]
            await db.abatch_set(items)
            print("✓ Async batch set successful")
            
            print("Step 2: Testing async batch get...")
            keys = ["batch_key1", "batch_key2", "batch_key3", "batch_key4", "batch_key5"]
            results = await db.abatch_get(keys)
            
            assert len(results) == 5, f"Expected 5 results, got {len(results)}"
            assert results[0] == b"batch_value1", f"Expected b'batch_value1', got {results[0]}"
            assert results[1] == b"batch_value2", f"Expected b'batch_value2', got {results[1]}"
            assert results[2] == b"batch_value3", f"Expected b'batch_value3', got {results[2]}"
            print("✓ Async batch get successful")
            
            print("Step 3: Testing async batch get with missing keys...")
            mixed_keys = ["batch_key1", "nonexistent", "batch_key3"]
            mixed_results = await db.abatch_get(mixed_keys)
            
            assert len(mixed_results) == 3, f"Expected 3 results, got {len(mixed_results)}"
            assert mixed_results[0] == b"batch_value1", f"Result mismatch"
            assert mixed_results[1] is None, f"Expected None for missing key"
            assert mixed_results[2] == b"batch_value3", f"Result mismatch"
            print("✓ Mixed batch get successful")
        
        print("\n✅ Test PASSED: Async batch operations work correctly")
        return True
        
    except Exception as e:
        print(f"\n❌ Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        cleanup_db_files(db_path)


@pytest.mark.asyncio
async def test_concurrent_async_operations():
    """Test concurrent async operations"""
    print("\n" + "="*60)
    print("Test 3: Concurrent Async Operations")
    print("="*60)
    
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    try:
        async with AsyncDictSQLite(db_path, capacity=10000, persist_mode="lazy") as db:
            print("Step 1: Running 100 concurrent async writes...")
            
            # Create 100 concurrent write tasks
            write_tasks = [
                db.aset(f"concurrent_key_{i}", f"concurrent_value_{i}".encode())
                for i in range(100)
            ]
            await asyncio.gather(*write_tasks)
            print("✓ 100 concurrent writes completed")
            
            print("Step 2: Running 100 concurrent async reads...")
            
            # Create 100 concurrent read tasks
            read_tasks = [
                db.aget(f"concurrent_key_{i}")
                for i in range(100)
            ]
            results = await asyncio.gather(*read_tasks)
            
            # Verify all results
            for i, result in enumerate(results):
                expected = f"concurrent_value_{i}".encode()
                assert result == expected, f"Key {i}: Expected {expected}, got {result}"
            print("✓ 100 concurrent reads completed and verified")
        
        print("\n✅ Test PASSED: Concurrent async operations work correctly")
        return True
        
    except Exception as e:
        print(f"\n❌ Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        cleanup_db_files(db_path)


@pytest.mark.asyncio
async def test_async_persistence():
    """Test async operations with persistence"""
    print("\n" + "="*60)
    print("Test 4: Async Operations with Persistence")
    print("="*60)
    
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    try:
        # Write data
        print("Step 1: Writing data with async methods...")
        async with AsyncDictSQLite(db_path, capacity=1000, persist_mode="lazy") as db:
            await db.aset("persist_key1", b"persist_value1")
            await db.aset("persist_key2", b"persist_value2")
            await db.aset("persist_key3", b"persist_value3")
            db.flush()
        print("✓ Data written and flushed")
        
        # Read data in new instance
        print("Step 2: Reading persisted data with async methods...")
        async with AsyncDictSQLite(db_path, capacity=1000, persist_mode="lazy") as db:
            result1 = await db.aget("persist_key1")
            result2 = await db.aget("persist_key2")
            result3 = await db.aget("persist_key3")
            
            assert result1 == b"persist_value1", f"Persistence failed for key1"
            assert result2 == b"persist_value2", f"Persistence failed for key2"
            assert result3 == b"persist_value3", f"Persistence failed for key3"
        print("✓ Persisted data read successfully")
        
        print("\n✅ Test PASSED: Async persistence works correctly")
        return True
        
    except Exception as e:
        print(f"\n❌ Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        cleanup_db_files(db_path)


@pytest.mark.asyncio
async def test_backward_compatibility():
    """Test that synchronous methods still work for backward compatibility"""
    print("\n" + "="*60)
    print("Test 5: Backward Compatibility (Sync Methods)")
    print("="*60)
    
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    try:
        async with AsyncDictSQLite(db_path, capacity=1000, persist_mode="lazy") as db:
            print("Step 1: Testing synchronous set...")
            db.set("sync_key1", b"sync_value1")
            db.set("sync_key2", b"sync_value2")
            print("✓ Synchronous set successful")
            
            print("Step 2: Testing synchronous get...")
            result1 = db.get("sync_key1")
            result2 = db.get("sync_key2")
            
            assert result1 == b"sync_value1", f"Expected b'sync_value1', got {result1}"
            assert result2 == b"sync_value2", f"Expected b'sync_value2', got {result2}"
            print("✓ Synchronous get successful")
            
            print("Step 3: Testing batch operations...")
            db.batch_set([("batch_sync1", b"value1"), ("batch_sync2", b"value2")])
            results = db.batch_get(["batch_sync1", "batch_sync2"])
            
            assert results[0] == b"value1", f"Batch get failed"
            assert results[1] == b"value2", f"Batch get failed"
            print("✓ Batch operations successful")
        
        print("\n✅ Test PASSED: Backward compatibility maintained")
        return True
        
    except Exception as e:
        print(f"\n❌ Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        cleanup_db_files(db_path)


async def main():
    """Run all async tests"""
    print("\n" + "="*70)
    print("AsyncDictSQLite Awaitable Methods Test Suite")
    print("="*70)
    
    tests = [
        test_async_get_set,
        test_async_batch_operations,
        test_concurrent_async_operations,
        test_async_persistence,
        test_backward_compatibility,
    ]
    
    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result)
        except Exception as e:
            print(f"\n❌ Test crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    # Summary
    print("\n" + "="*70)
    print("Test Summary")
    print("="*70)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    print(f"Failed: {total - passed}/{total}")
    
    if all(results):
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed")
        return 1


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
