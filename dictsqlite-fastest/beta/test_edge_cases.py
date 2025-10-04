#!/usr/bin/env python3
"""
Edge case and reliability tests for AsyncDictSQLiteFastestBeta.

Tests for proper cleanup, error handling, and various usage patterns.
"""
import asyncio
import tempfile
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from dictsqlite_fastest_beta import AsyncDictSQLiteFastestBeta


async def test_multiple_sequential_opens():
    """Test opening and closing the same database multiple times."""
    print("\n=== Test: Multiple Sequential Opens ===")
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, 'test.db')
    
    try:
        # First open
        async with AsyncDictSQLiteFastestBeta(db_path) as db:
            await db.aset('key1', 'value1')
            result = await db.aget('key1')
            assert result == 'value1', "First open failed"
        
        # Second open - should work fine
        async with AsyncDictSQLiteFastestBeta(db_path) as db:
            result = await db.aget('key1')
            assert result == 'value1', "Second open failed to read data"
            await db.aset('key2', 'value2')
        
        # Third open - verify all data
        async with AsyncDictSQLiteFastestBeta(db_path) as db:
            result1 = await db.aget('key1')
            result2 = await db.aget('key2')
            assert result1 == 'value1', "Third open failed for key1"
            assert result2 == 'value2', "Third open failed for key2"
        
        print("  ✅ Multiple sequential opens work correctly")
        return True
    
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False
    
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
        os.rmdir(temp_dir)


async def test_without_context_manager_cleanup():
    """Test manual cleanup without context manager."""
    print("\n=== Test: Manual Cleanup (Without Context Manager) ===")
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, 'test.db')
    
    try:
        # First instance
        db = AsyncDictSQLiteFastestBeta(db_path)
        await db.aset('key1', 'value1')
        result = await db.aget('key1')
        assert result == 'value1', "Write/read failed"
        await db.aclose()
        
        # Second instance - should be able to access same data
        db = AsyncDictSQLiteFastestBeta(db_path)
        result = await db.aget('key1')
        assert result == 'value1', "Second instance failed to read"
        await db.aset('key2', 'value2')
        await db.aclose()
        
        print("  ✅ Manual cleanup works correctly")
        return True
    
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False
    
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
        os.rmdir(temp_dir)


async def test_concurrent_operations_stress():
    """Stress test with many concurrent operations."""
    print("\n=== Test: Concurrent Operations Stress (1000 operations) ===")
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, 'test.db')
    
    try:
        async with AsyncDictSQLiteFastestBeta(db_path) as db:
            # Create 1000 concurrent write tasks
            tasks = []
            for i in range(1000):
                tasks.append(db.aset(f'key_{i}', f'value_{i}'))
            
            await asyncio.gather(*tasks)
            
            # Verify a sample
            for i in [0, 100, 500, 999]:
                result = await db.aget(f'key_{i}')
                assert result == f'value_{i}', f"Data mismatch for key_{i}"
        
        print("  ✅ 1000 concurrent operations completed successfully")
        return True
    
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False
    
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
        os.rmdir(temp_dir)


async def test_mixed_operations():
    """Test mixing reads, writes, and deletes concurrently."""
    print("\n=== Test: Mixed Operations (Read/Write/Delete) ===")
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, 'test.db')
    
    try:
        async with AsyncDictSQLiteFastestBeta(db_path) as db:
            # Pre-populate
            for i in range(100):
                await db.aset(f'key_{i}', f'value_{i}')
            
            # Mix operations
            tasks = []
            
            # 50 reads
            for i in range(0, 50):
                tasks.append(db.aget(f'key_{i}'))
            
            # 30 writes (updates)
            for i in range(50, 80):
                tasks.append(db.aset(f'key_{i}', f'updated_{i}'))
            
            # 20 deletes
            for i in range(80, 100):
                tasks.append(db.adelete(f'key_{i}'))
            
            results = await asyncio.gather(*tasks)
            
            # Verify results
            # First 50 should be original values
            for i in range(50):
                assert results[i] == f'value_{i}', f"Read failed for key_{i}"
            
            # Verify updates
            for i in range(50, 80):
                result = await db.aget(f'key_{i}')
                assert result == f'updated_{i}', f"Update failed for key_{i}"
            
            # Verify deletes
            for i in range(80, 100):
                result = await db.aget(f'key_{i}', 'DELETED')
                assert result == 'DELETED', f"Delete failed for key_{i}"
        
        print("  ✅ Mixed operations work correctly")
        return True
    
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False
    
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
        os.rmdir(temp_dir)


async def test_bulk_operations_reliability():
    """Test bulk operations for reliability."""
    print("\n=== Test: Bulk Operations Reliability ===")
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, 'test.db')
    
    try:
        async with AsyncDictSQLiteFastestBeta(db_path) as db:
            # Large bulk insert
            bulk_data = {f'bulk_{i}': {'id': i, 'data': f'data_{i}'} for i in range(5000)}
            await db.abulk_insert(bulk_data)
            
            # Verify sample
            samples = [0, 1000, 2500, 4999]
            for i in samples:
                result = await db.aget(f'bulk_{i}')
                assert result['id'] == i, f"Bulk insert failed for bulk_{i}"
                assert result['data'] == f'data_{i}', f"Data mismatch for bulk_{i}"
            
            # Bulk get
            keys = [f'bulk_{i}' for i in samples]
            results = await db.abulk_get(keys)
            assert len(results) == len(samples), "Bulk get returned wrong count"
        
        print("  ✅ Bulk operations are reliable")
        return True
    
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False
    
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
        os.rmdir(temp_dir)


async def test_error_recovery():
    """Test error recovery and handling."""
    print("\n=== Test: Error Recovery ===")
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, 'test.db')
    
    try:
        async with AsyncDictSQLiteFastestBeta(db_path) as db:
            # Valid operation
            await db.aset('key1', 'value1')
            
            # Try to get non-existent key (should not crash)
            result = await db.aget('nonexistent', 'default')
            assert result == 'default', "Default value not returned"
            
            # Continue with normal operations
            await db.aset('key2', 'value2')
            result = await db.aget('key2')
            assert result == 'value2', "Recovery failed after error"
        
        print("  ✅ Error recovery works correctly")
        return True
    
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False
    
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
        os.rmdir(temp_dir)


async def test_flush_reliability():
    """Test flush operations for reliability."""
    print("\n=== Test: Flush Reliability ===")
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, 'test.db')
    
    try:
        async with AsyncDictSQLiteFastestBeta(db_path) as db:
            # Write data
            for i in range(100):
                await db.aset(f'key_{i}', f'value_{i}')
            
            # Explicit flush
            await db.aflush()
            
            # Continue operations
            for i in range(100, 200):
                await db.aset(f'key_{i}', f'value_{i}')
            
            # Another flush
            await db.aflush()
            
            # Verify data
            samples = [0, 50, 100, 150, 199]
            for i in samples:
                result = await db.aget(f'key_{i}')
                assert result == f'value_{i}', f"Data lost after flush for key_{i}"
        
        print("  ✅ Flush operations are reliable")
        return True
    
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False
    
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
        os.rmdir(temp_dir)


async def main():
    """Run all edge case tests."""
    print("=" * 80)
    print("Edge Case and Reliability Tests")
    print("=" * 80)
    
    tests = [
        ("Multiple Sequential Opens", test_multiple_sequential_opens),
        ("Manual Cleanup", test_without_context_manager_cleanup),
        ("Concurrent Stress (1000 ops)", test_concurrent_operations_stress),
        ("Mixed Operations", test_mixed_operations),
        ("Bulk Operations", test_bulk_operations_reliability),
        ("Error Recovery", test_error_recovery),
        ("Flush Reliability", test_flush_reliability),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results[test_name] = result
        except Exception as e:
            print(f"\n  ❌ Test '{test_name}' crashed: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print("\n" + "=" * 80)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 80)
    
    if passed == total:
        print("\n🎉 All edge case tests passed!")
        print("✅ No issues detected with WITH/WITHOUT context manager usage")
        print("✅ All operations are reliable and stable")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
    
    print()
    
    return passed == total


if __name__ == '__main__':
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
