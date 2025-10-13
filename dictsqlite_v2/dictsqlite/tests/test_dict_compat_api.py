#!/usr/bin/env python3
"""
Test Dictionary-Compatible API methods (Phase 2, Task 2.2)
"""
import os
import sys
import pytest
from .conftest import windows_safe_temp_db

# Import the built module
try:
    from dictsqlite import DictSQLiteV4
except ImportError:
    print("Error: dictsqlite module not found. Please build with 'maturin develop'")
    sys.exit(1)


def test_dict_items_values_methods():
    """Test items() and values() methods"""
    print("\n" + "="*60)
    print("Test 1: items() and values() Methods")
    print("="*60)
    
    with windows_safe_temp_db() as db_path:
        print("Step 1: Creating database and adding test data...")
        db = DictSQLiteV4(db_path, persist_mode="lazy", storage_mode="bytes")
        
        test_data = {
            "key1": b"value1",
            "key2": b"value2",
            "key3": b"value3",
        }
        
        for k, v in test_data.items():
            db[k] = v
        
        print("\nStep 2: Testing items() method...")
        items = db.items()
        items_dict = dict(items)
        
        assert len(items) == 3, f"Expected 3 items, got {len(items)}"
        for k, v in test_data.items():
            assert k in items_dict, f"{k} not found in items()"
            assert items_dict[k] == v, f"Value mismatch for {k}"
        print("✓ items() returns correct key-value pairs")
        
        print("\nStep 3: Testing values() method...")
        values = db.values()
        values_set = set(values)
        
        assert len(values) == 3, f"Expected 3 values, got {len(values)}"
        for v in test_data.values():
            assert v in values_set, f"{v} not found in values()"
        print("✓ values() returns correct values")
        
        print("\nStep 4: Testing keys() method...")
        keys = db.keys()
        keys_set = set(keys)
        
        assert len(keys) == 3, f"Expected 3 keys, got {len(keys)}"
        for k in test_data.keys():
            assert k in keys_set, f"{k} not found in keys()"
        print("✓ keys() returns correct keys")
        
        db.close()
        
        print("\n✅ Test PASSED: items(), values(), keys() work correctly")


def test_dict_update_method():
    """Test update() method"""
    print("\n" + "="*60)
    print("Test 2: update() Method")
    print("="*60)
    
    with windows_safe_temp_db() as db_path:
        print("Step 1: Creating database...")
        db = DictSQLiteV4(db_path, persist_mode="lazy", storage_mode="bytes")
        
        print("\nStep 2: Adding initial data...")
        db["existing_key"] = b"existing_value"
        
        print("\nStep 3: Using update() to add multiple items...")
        update_data = {
            "new_key1": b"new_value1",
            "new_key2": b"new_value2",
            "existing_key": b"updated_value",  # Should overwrite
        }
        db.update(update_data)
        
        print("\nStep 4: Verifying updated data...")
        assert db["new_key1"] == b"new_value1", "new_key1 not added"
        assert db["new_key2"] == b"new_value2", "new_key2 not added"
        assert db["existing_key"] == b"updated_value", "existing_key not updated"
        print("✓ update() adds and overwrites correctly")
        
        stats = db.stats()
        assert stats["hot_tier_size"] == 3, f"Expected 3 items, got {stats['hot_tier_size']}"
        print("✓ Item count is correct")
        
        db.close()
        
        print("\n✅ Test PASSED: update() works correctly")


def test_dict_pop_method():
    """Test pop() method with and without default"""
    print("\n" + "="*60)
    print("Test 3: pop() Method")
    print("="*60)
    
    with windows_safe_temp_db() as db_path:
        print("Step 1: Creating database and adding test data...")
        db = DictSQLiteV4(db_path, persist_mode="lazy", storage_mode="bytes")
        
        db["pop_key1"] = b"pop_value1"
        db["pop_key2"] = b"pop_value2"
        
        initial_count = db.stats()["hot_tier_size"]
        print(f"  Initial count: {initial_count}")
        
        print("\nStep 2: Testing pop() with existing key...")
        value = db.pop("pop_key1")
        assert value == b"pop_value1", "pop() returned wrong value"
        assert "pop_key1" not in db, "Key still exists after pop"
        print("✓ pop() removes and returns value")
        
        new_count = db.stats()["hot_tier_size"]
        assert new_count == initial_count - 1, "Item count not decremented"
        print("✓ Item count decremented correctly")
        
        print("\nStep 3: Testing pop() with non-existent key and default...")
        default_value = db.pop("nonexistent_key", b"default_value")
        assert default_value == b"default_value", "pop() didn't return default"
        print("✓ pop() returns default for non-existent key")
        
        print("\nStep 4: Testing pop() with non-existent key and no default...")
        try:
            db.pop("another_nonexistent_key")
            assert False, "pop() should raise KeyError when key doesn't exist and no default"
        except KeyError:
            print("✓ pop() raises KeyError when no default specified")
        
        db.close()
        
        print("\n✅ Test PASSED: pop() works correctly")


def test_dict_setdefault_method():
    """Test setdefault() method"""
    print("\n" + "="*60)
    print("Test 4: setdefault() Method")
    print("="*60)
    
    with windows_safe_temp_db() as db_path:
        print("Step 1: Creating database...")
        db = DictSQLiteV4(db_path, persist_mode="lazy", storage_mode="bytes")
        
        print("\nStep 2: Using setdefault() on non-existent key...")
        value = db.setdefault("new_key", b"default_value")
        assert value == b"default_value", "setdefault() didn't return default"
        assert db["new_key"] == b"default_value", "Key not set with default value"
        print("✓ setdefault() sets and returns default for new key")
        
        print("\nStep 3: Using setdefault() on existing key...")
        db["existing_key"] = b"existing_value"
        value = db.setdefault("existing_key", b"should_not_be_set")
        assert value == b"existing_value", "setdefault() didn't return existing value"
        assert db["existing_key"] == b"existing_value", "Existing value was overwritten"
        print("✓ setdefault() returns existing value without overwriting")
        
        print("\nStep 4: Verifying final state...")
        assert db.stats()["hot_tier_size"] == 2, "Wrong number of items"
        print("✓ Item count is correct")
        
        db.close()
        
        print("\n✅ Test PASSED: setdefault() works correctly")


def test_dict_compatibility_with_persistence():
    """Test that dict methods work correctly with persistence"""
    print("\n" + "="*60)
    print("Test 5: Dict Methods with Persistence")
    print("="*60)
    
    with windows_safe_temp_db() as db_path:
        print("Step 1: Creating database and using dict methods...")
        db1 = DictSQLiteV4(db_path, persist_mode="lazy", storage_mode="bytes")
        
        # Use various dict methods
        db1.update({"key1": b"value1", "key2": b"value2"})
        db1.setdefault("key3", b"value3")
        db1["key4"] = b"value4"
        
        print(f"  Added {db1.stats()['hot_tier_size']} items")
        
        print("\nStep 2: Flushing and closing...")
        db1.flush()
        db1.close()
        
        print("\nStep 3: Reopening and verifying all methods work...")
        db2 = DictSQLiteV4(db_path, persist_mode="lazy", storage_mode="bytes")
        
        # Test items()
        items = dict(db2.items())
        assert len(items) == 4, f"Expected 4 items, got {len(items)}"
        print("✓ items() works after persistence")
        
        # Test values()
        values = db2.values()
        assert len(values) == 4, f"Expected 4 values, got {len(values)}"
        print("✓ values() works after persistence")
        
        # Test pop()
        popped = db2.pop("key1")
        assert popped == b"value1", "Couldn't pop persisted key"
        print("✓ pop() works on persisted data")
        
        # Test setdefault() on persisted key
        value = db2.setdefault("key2", b"should_not_replace")
        assert value == b"value2", "setdefault() didn't return persisted value"
        print("✓ setdefault() works on persisted data")
        
        db2.close()
        
        print("\n✅ Test PASSED: Dict methods work correctly with persistence")


def run_all_tests():
    """Run all dictionary-compatible API tests"""
    print("\n" + "="*60)
    print("Dictionary-Compatible API Test Suite (Phase 2, Task 2.2)")
    print("="*60)
    
    tests = [
        ("items/values/keys methods", test_dict_items_values_methods),
        ("update() method", test_dict_update_method),
        ("pop() method", test_dict_pop_method),
        ("setdefault() method", test_dict_setdefault_method),
        ("Dict methods with persistence", test_dict_compatibility_with_persistence),
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
        print("\n🎉 All tests PASSED! Dictionary-compatible API is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) FAILED. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
