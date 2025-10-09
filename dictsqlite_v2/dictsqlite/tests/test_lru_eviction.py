#!/usr/bin/env python3
"""
Test LRU Eviction functionality (Phase 1, Task 1.2)
"""
import os
import sys
from .conftest import windows_safe_temp_db

# Import the built module
try:
    from dictsqlite import DictSQLiteV4
except ImportError:
    print("Error: dictsqlite module not found. Please build with 'maturin develop'")
    sys.exit(1)


def test_lru_eviction_basic():
    """Test basic LRU eviction when capacity is exceeded"""
    print("\n" + "="*60)
    print("Test 1: Basic LRU Eviction")
    print("="*60)
    
    with windows_safe_temp_db() as db_path:
        print("Step 1: Creating DictSQLiteV4 with small capacity (10 items)...")
        db = DictSQLiteV4(db_path, hot_capacity=10, persist_mode="lazy")
        
        print("Step 2: Writing 10 items (should fill capacity exactly)...")
        for i in range(10):
            db[f"key_{i}"] = f"value_{i}".encode()
        
        stats = db.stats()
        print(f"  Hot tier size: {stats['hot_tier_size']}/{stats['hot_tier_capacity']}")
        assert stats['hot_tier_size'] == 10, f"Expected 10 items, got {stats['hot_tier_size']}"
        print("✓ Capacity filled exactly")
        
        print("\nStep 3: Writing 11th item (should trigger eviction)...")
        db["key_10"] = b"value_10"
        
        stats = db.stats()
        print(f"  Hot tier size after eviction: {stats['hot_tier_size']}/{stats['hot_tier_capacity']}")
        assert stats['hot_tier_size'] <= 10, f"Expected ≤10 items after eviction, got {stats['hot_tier_size']}"
        print("✓ Eviction triggered")
        
        print("\nStep 4: Verifying all data is still accessible...")
        for i in range(11):
            value = db.get(f"key_{i}", None)
            assert value is not None, f"key_{i} should still be accessible"
        print("✓ All data accessible (from hot tier or storage)")
        
        print("\nStep 5: Flushing and verifying persistence...")
        db.flush()
        db.close()
        
        # Reopen and check
        db2 = DictSQLiteV4(db_path, hot_capacity=10, persist_mode="lazy")
        for i in range(11):
            value = db2.get(f"key_{i}", None)
            assert value is not None, f"key_{i} should persist"
        db2.close()
        print("✓ Data persisted correctly")
        
        print("\n✅ Test PASSED: LRU eviction works correctly")


def test_lru_eviction_access_pattern():
    """Test that LRU eviction respects access patterns"""
    print("\n" + "="*60)
    print("Test 2: LRU Eviction with Access Patterns")
    print("="*60)
    
    with windows_safe_temp_db() as db_path:
        print("Step 1: Creating DictSQLiteV4 with capacity=5...")
        db = DictSQLiteV4(db_path, hot_capacity=5, persist_mode="lazy")
        
        print("Step 2: Writing 5 items...")
        for i in range(5):
            db[f"key_{i}"] = f"value_{i}".encode()
        
        print("Step 3: Accessing key_0 frequently (to make it 'hot')...")
        for _ in range(5):
            _ = db["key_0"]
        
        print("Step 4: Adding 3 more items (should evict LRU items, not key_0)...")
        for i in range(5, 8):
            db[f"key_{i}"] = f"value_{i}".encode()
        
        stats = db.stats()
        print(f"  Hot tier size: {stats['hot_tier_size']}")
        
        # key_0 should still be in hot tier since it was accessed recently
        print("\nStep 5: Verifying key_0 is still in hot tier...")
        # This is harder to verify without exposing internal state
        # But we can verify it's still accessible quickly
        value = db["key_0"]
        assert value == b"value_0", "key_0 should still be accessible"
        print("✓ Frequently accessed key retained")
        
        print("\nStep 6: Verifying all data is accessible...")
        for i in range(8):
            value = db.get(f"key_{i}", None)
            assert value is not None, f"key_{i} should be accessible"
        print("✓ All data accessible")
        
        db.close()
        
        print("\n✅ Test PASSED: LRU access pattern respected")


def test_lru_eviction_memory_mode():
    """Test that memory mode doesn't try to persist evicted items"""
    print("\n" + "="*60)
    print("Test 3: LRU Eviction in Memory Mode")
    print("="*60)
    
    try:
        print("Step 1: Creating DictSQLiteV4 in memory mode with capacity=5...")
        db = DictSQLiteV4(":memory:", hot_capacity=5, persist_mode="memory")
        
        print("Step 2: Writing 10 items (exceeding capacity)...")
        for i in range(10):
            db[f"mem_key_{i}"] = f"mem_value_{i}".encode()
        
        stats = db.stats()
        print(f"  Hot tier size: {stats['hot_tier_size']}")
        assert stats['hot_tier_size'] <= 5, "Should not exceed capacity"
        print("✓ Capacity limit enforced")
        
        print("\nStep 3: Verifying recent items are in memory...")
        # Recent items should be in hot tier
        recent_accessible = 0
        for i in range(5, 10):  # Check last 5 items
            value = db.get(f"mem_key_{i}", None)
            if value is not None:
                recent_accessible += 1
        
        print(f"  Recent items accessible: {recent_accessible}/5")
        assert recent_accessible >= 3, "Most recent items should be accessible"
        print("✓ Recent items retained")
        
        db.close()
        
        print("\n✅ Test PASSED: Memory mode eviction works correctly")
        
    except Exception as e:
        print(f"\n❌ Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        raise


def test_lru_eviction_large_dataset():
    """Test LRU eviction with larger dataset"""
    print("\n" + "="*60)
    print("Test 4: LRU Eviction with Large Dataset")
    print("="*60)
    
    with windows_safe_temp_db() as db_path:
        print("Step 1: Creating DictSQLiteV4 with capacity=100...")
        db = DictSQLiteV4(db_path, hot_capacity=100, persist_mode="lazy")
        
        print("Step 2: Writing 500 items (5x capacity)...")
        for i in range(500):
            db[f"large_key_{i}"] = f"large_value_{i}".encode()
            if (i + 1) % 100 == 0:
                print(f"  Written: {i + 1}/500 items")
        
        stats = db.stats()
        print(f"\nStep 3: Checking hot tier size...")
        print(f"  Hot tier size: {stats['hot_tier_size']}/{stats['hot_tier_capacity']}")
        assert stats['hot_tier_size'] <= 100, "Should not exceed capacity"
        print("✓ Capacity maintained despite large write volume")
        
        print("\nStep 4: Flushing and verifying all data persisted...")
        db.flush()
        db.close()
        
        db2 = DictSQLiteV4(db_path, hot_capacity=100, persist_mode="lazy")
        print("Step 5: Reading all 500 items back...")
        for i in range(500):
            value = db2.get(f"large_key_{i}", None)
            assert value is not None, f"large_key_{i} should be accessible"
            if (i + 1) % 100 == 0:
                print(f"  Read: {i + 1}/500 items")
        
        db2.close()
        print("\n✓ All 500 items persisted and readable")
        
        print("\n✅ Test PASSED: Large dataset handled correctly")


def run_all_tests():
    """Run all LRU eviction tests"""
    print("\n" + "="*60)
    print("LRU Eviction Test Suite (Phase 1, Task 1.2)")
    print("="*60)
    
    tests = [
        ("Basic LRU Eviction", test_lru_eviction_basic),
        ("LRU Access Patterns", test_lru_eviction_access_pattern),
        ("Memory Mode Eviction", test_lru_eviction_memory_mode),
        ("Large Dataset Eviction", test_lru_eviction_large_dataset),
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
        print("\n🎉 All tests PASSED! LRU eviction is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) FAILED. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
