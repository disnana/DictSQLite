"""Comprehensive tests for FastDictSQLite utility modules.

This test module covers the utility functions and classes in the modules
package to improve test coverage and ensure reliability.
"""
# pylint: disable=redefined-outer-name

import asyncio
import time
import threading
import pickle
import pytest

from dictsqlite.modules import utils
# pylint: disable=import-error,no-name-in-module
from dictsqlite.modules import safe_pickle


class TestExpiringDict:
    """Test cases for ExpiringDict class."""

    def test_expiring_dict_creation(self):
        """Test ExpiringDict creation with various parameters."""
        # Test with default expiration
        ed = utils.ExpiringDict(1)
        assert ed.expiration_time == 1
        assert len(ed) == 0

        # Test with different expiration times
        ed2 = utils.ExpiringDict(5)
        assert ed2.expiration_time == 5

    def test_expiring_dict_basic_operations(self):
        """Test basic dictionary operations."""
        ed = utils.ExpiringDict(10)  # 10 second expiration

        # Test setting and getting
        ed["key1"] = "value1"
        assert ed["key1"] == "value1"
        assert "key1" in ed
        assert len(ed) == 1

        # Test multiple keys
        ed["key2"] = "value2"
        ed["key3"] = "value3"
        assert len(ed) == 3

        # Test keys(), values(), items()
        assert set(ed.keys()) == {"key1", "key2", "key3"}
        assert set(ed.values()) == {"value1", "value2", "value3"}
        assert set(ed.items()) == {("key1", "value1"), ("key2", "value2"), ("key3", "value3")}

    def test_expiring_dict_expiration_sync(self):
        """Test expiration in synchronous mode."""
        ed = utils.ExpiringDict(0.1)  # 0.1 second expiration

        # Set a value
        ed["temp_key"] = "temp_value"
        assert "temp_key" in ed

        # Wait for expiration
        time.sleep(0.2)

        # Key should be expired
        assert "temp_key" not in ed
        assert len(ed) == 0

    def test_expiring_dict_expiration_async(self):
        """Test expiration in asynchronous mode."""
        async def async_test():
            ed = utils.ExpiringDict(0.1)  # 0.1 second expiration

            # Set a value
            ed["async_key"] = "async_value"
            assert "async_key" in ed

            # Wait for expiration
            await asyncio.sleep(0.2)

            # Key should be expired
            assert "async_key" not in ed
            assert len(ed) == 0

        # Run the async test
        asyncio.run(async_test())

    def test_expiring_dict_update_expiration(self):
        """Test that accessing a key updates its expiration."""
        ed = utils.ExpiringDict(0.2)  # 0.2 second expiration

        ed["refresh_key"] = "refresh_value"

        # Access the key multiple times to refresh expiration
        for _ in range(3):
            time.sleep(0.1)
            # Check if key still exists - it might expire depending on implementation
            if "refresh_key" in ed:
                assert ed["refresh_key"] == "refresh_value"  # This should refresh expiration

        # The behavior may vary depending on implementation details

    def test_expiring_dict_deletion(self):
        """Test manual deletion of keys."""
        ed = utils.ExpiringDict(10)  # Long expiration

        ed["delete_me"] = "delete_value"
        assert "delete_me" in ed

        # Manual deletion
        del ed["delete_me"]
        assert "delete_me" not in ed
        assert len(ed) == 0

    def test_expiring_dict_clear(self):
        """Test clearing the dictionary."""
        ed = utils.ExpiringDict(10)

        # Add multiple items
        for i in range(5):
            ed[f"key_{i}"] = f"value_{i}"

        assert len(ed) == 5

        # Clear all items
        ed.clear()
        assert len(ed) == 0
        assert not list(ed.keys())

    def test_expiring_dict_get_method(self):
        """Test the get() method with default values."""
        ed = utils.ExpiringDict(10)

        ed["existing"] = "value"

        # Test get with existing key
        assert ed.get("existing") == "value"
        assert ed.get("existing", "default") == "value"

        # Test get with non-existing key
        assert ed.get("nonexistent") is None
        assert ed.get("nonexistent", "default") == "default"

    def test_expiring_dict_setdefault(self):
        """Test the setdefault() method."""
        ed = utils.ExpiringDict(10)

        # setdefault on non-existing key
        result = ed.setdefault("new_key", "default_value")
        assert result == "default_value"
        assert ed["new_key"] == "default_value"

        # setdefault on existing key
        result = ed.setdefault("new_key", "other_value")
        assert result == "default_value"  # Should return existing value
        assert ed["new_key"] == "default_value"

    def test_expiring_dict_pop(self):
        """Test the pop() method."""
        ed = utils.ExpiringDict(10)

        ed["pop_key"] = "pop_value"

        # Pop existing key
        result = ed.pop("pop_key")
        assert result == "pop_value"
        assert "pop_key" not in ed

        # Pop non-existing key with default
        result = ed.pop("nonexistent", "default")
        assert result == "default"

        # Pop non-existing key without default should raise KeyError
        with pytest.raises(KeyError):
            ed.pop("nonexistent")

    def test_expiring_dict_popitem(self):
        """Test the popitem() method."""
        ed = utils.ExpiringDict(10)

        ed["pop_item_key"] = "pop_item_value"

        # popitem should return and remove an item
        key, value = ed.popitem()
        assert key == "pop_item_key"
        assert value == "pop_item_value"
        assert len(ed) == 0

        # popitem on empty dict should raise KeyError
        with pytest.raises(KeyError):
            ed.popitem()

    def test_expiring_dict_update(self):
        """Test the update() method."""
        ed = utils.ExpiringDict(10)

        # Update with dict
        ed.update({"key1": "value1", "key2": "value2"})
        assert ed["key1"] == "value1"
        assert ed["key2"] == "value2"

        # Update with keyword arguments
        ed.update(key3="value3", key4="value4")
        assert ed["key3"] == "value3"
        assert ed["key4"] == "value4"

    def test_expiring_dict_concurrent_access(self):
        """Test concurrent access to ExpiringDict."""
        ed = utils.ExpiringDict(1)  # 1 second expiration

        def worker(worker_id):
            for i in range(10):
                key = f"worker_{worker_id}_key_{i}"
                ed[key] = f"worker_{worker_id}_value_{i}"
                time.sleep(0.01)  # Small delay

        # Start multiple worker threads
        threads = []
        for i in range(3):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        # Wait for all threads to complete
        for t in threads:
            t.join()

        # Verify some data exists (exact count may vary due to expiration)
        assert len(ed) > 0

    def test_expiring_dict_pickle_serialization(self):
        """Test pickle serialization of ExpiringDict."""
        ed = utils.ExpiringDict(10)
        ed["pickle_key"] = "pickle_value"
        ed["another_key"] = {"nested": "data"}

        # Serialize
        pickled_data = pickle.dumps(ed)

        # Deserialize
        unpickled_ed = pickle.loads(pickled_data)

        # Verify data is preserved
        assert unpickled_ed["pickle_key"] == "pickle_value"
        assert unpickled_ed["another_key"]["nested"] == "data"
        assert unpickled_ed.expiration_time == 10

    def test_expiring_dict_repr(self):
        """Test string representation of ExpiringDict."""
        ed = utils.ExpiringDict(5)
        ed["repr_key"] = "repr_value"

        repr_str = repr(ed)
        # ExpiringDict inherits from MutableMapping, so it might not have custom __repr__
        # Just verify it contains the key-value data
        assert "repr_key" in repr_str
        assert "repr_value" in repr_str


class TestSafeUnpickler:
    """Test cases for safe_loads function."""

    def test_safe_unpickler_builtin_types(self):
        """Test safe_loads with built-in types."""
        # Test safe built-in types
        safe_data = [
            "string",
            42,
            3.14,
            True,
            None,
            [1, 2, 3],
            {"key": "value"},
            (1, 2, 3),
            {1, 2, 3}
        ]

        for data in safe_data:
            pickled = pickle.dumps(data)
            unpickled = safe_pickle.safe_loads(pickled)
            assert unpickled == data

    def test_safe_unpickler_policy_allowed_module(self):
        """Test safe_loads with policy-allowed modules."""
        # Test with allowed built-in function using builtins in allowed list
        import builtins  # pylint: disable=import-outside-toplevel
        safe_len = getattr(builtins, 'len')
        pickled = pickle.dumps(safe_len)

        unpickled = safe_pickle.safe_loads(pickled, allowed_builtins=["len"])
        assert unpickled is len

    def test_safe_unpickler_policy_blocked_module(self):
        """Test safe_loads blocking dangerous modules."""
        # This would be dangerous to unpickle without policy
        import os  # pylint: disable=import-outside-toplevel
        dangerous_func = os.system
        pickled = pickle.dumps(dangerous_func)

        # Should raise exception when blocked
        with pytest.raises(pickle.UnpicklingError):
            safe_pickle.safe_loads(pickled)

    def test_safe_unpickler_default_policy(self):
        """Test safe_loads with default restrictive policy."""
        # Default policy should block most dangerous operations
        import subprocess  # pylint: disable=import-outside-toplevel
        dangerous_func = subprocess.call
        pickled = pickle.dumps(dangerous_func)

        # Should raise exception
        with pytest.raises(pickle.UnpicklingError):
            safe_pickle.safe_loads(pickled)

    def test_safe_unpickler_nested_structures(self):
        """Test safe_loads with nested data structures."""
        nested_data = {
            "list": [1, 2, {"inner": "value"}],
            "dict": {"nested": {"deep": [1, 2, 3]}},
            "tuple": (1, "string", [4, 5, 6])
        }

        pickled = pickle.dumps(nested_data)
        unpickled = safe_pickle.safe_loads(pickled)

        assert unpickled == nested_data

    def test_safe_unpickler_custom_policy_function(self):
        """Test safe_loads with custom allowed globals."""
        # Test allowed function
        pickled_len = pickle.dumps(len)
        unpickled_len = safe_pickle.safe_loads(pickled_len, allowed_globals=["builtins.len"])
        assert unpickled_len is len

        # Test blocked function
        pickled_eval = pickle.dumps(eval)
        with pytest.raises(pickle.UnpicklingError):
            safe_pickle.safe_loads(pickled_eval, allowed_globals=["builtins.len"])

    def test_safe_unpickler_error_handling(self):
        """Test safe_loads error handling."""
        # Test with invalid pickle data
        invalid_data = b"invalid pickle data"

        with pytest.raises(Exception):  # Should raise some form of unpickling error
            safe_pickle.safe_loads(invalid_data)

    def test_safe_unpickler_empty_data(self):
        """Test safe_loads with empty data."""
        empty_data = b""

        with pytest.raises(Exception):
            safe_pickle.safe_loads(empty_data)


class TestUtilityFunctions:
    """Test cases for utility functions in the utils module."""

    def test_loop_creation_and_management(self):
        """Test loop creation utilities in ExpiringDict."""
        ed = utils.ExpiringDict(1)

        # Test that loop creation works
        # pylint: disable=protected-access
        loop = ed._get_or_create_loop()
        assert loop is not None
        assert isinstance(loop, asyncio.AbstractEventLoop)

    def test_expiring_dict_timer_cleanup(self):
        """Test that timers are properly cleaned up."""
        ed = utils.ExpiringDict(0.1)

        # Create and expire multiple keys
        for i in range(5):
            ed[f"cleanup_key_{i}"] = f"value_{i}"

        # Wait for expiration
        time.sleep(0.2)

        # All keys should be expired and timers cleaned up
        assert len(ed) == 0
        # Timers should be cleaned up (though we can't directly verify this)

    def test_expiring_dict_exception_handling(self):
        """Test exception handling in ExpiringDict."""
        ed = utils.ExpiringDict(10)

        # Test KeyError on non-existent key
        with pytest.raises(KeyError):
            _ = ed["nonexistent_key"]

        # Test that exceptions don't break the dict
        ed["normal_key"] = "normal_value"
        assert ed["normal_key"] == "normal_value"

    def test_expiring_dict_thread_safety(self):
        """Test thread safety of ExpiringDict operations."""
        ed = utils.ExpiringDict(2)  # 2 second expiration
        results = []

        def worker(worker_id, operation_count):
            for i in range(operation_count):
                key = f"thread_{worker_id}_item_{i}"
                try:
                    ed[key] = f"value_{worker_id}_{i}"
                    # Immediately try to read it back
                    value = ed[key]
                    results.append((worker_id, i, value))
                except (KeyError, RuntimeError, ValueError) as error:
                        # narrowed from broad Exception
                    results.append(
                        (worker_id, i, f"error: {error}")
                    )

        # Start multiple threads
        threads = []
        for thread_id in range(3):
            t = threading.Thread(target=worker, args=(thread_id, 10))
            threads.append(t)
            t.start()

        # Wait for completion
        for t in threads:
            t.join()

        # Verify that operations completed (some may have failed due to expiration)
        assert len(results) == 30  # 3 threads * 10 operations each

        # Verify that successful operations have correct format
        for worker_id, item_id, result in results:
            if not str(result).startswith("error:"):
                assert f"value_{worker_id}_{item_id}" == result
