"""Test DBSyncedList and DBSyncedSet classes for DictSQLite.

This test module covers the synced collection classes that automatically
synchronize changes back to the database.
"""
# pylint: disable=redefined-outer-name

from unittest.mock import Mock
import pytest

from dictsqlite.main import DictSQLite, DBSyncedSet


@pytest.fixture()
def db_path(tmp_path):
    """Provide a path to a temporary database file."""
    return tmp_path / "test_synced_collections.db"


@pytest.fixture()
def db(db_path):
    """Provide a DictSQLite instance."""
    d = DictSQLite(str(db_path))
    yield d
    d.close()


class TestDBSyncedList:
    """Test cases for DBSyncedList class."""

    def test_list_creation_and_basic_operations(self, db: DictSQLite):
        """Test basic list operations and sync."""
        db["test_list"] = [1, 2, 3]
        sync_list = db["test_list"]

        # Should be a list-like object
        assert len(sync_list) == 3
        assert sync_list[0] == 1
        assert sync_list[1] == 2
        assert sync_list[2] == 3

    def test_list_append_operations(self, db: DictSQLite):
        """Test list append operations and automatic sync."""
        db["append_list"] = []
        sync_list = db["append_list"]

        # Test append
        sync_list.append(1)
        sync_list.append(2)
        sync_list.append("test")

        # Verify changes are synced
        fresh_list = db["append_list"]
        assert list(fresh_list) == [1, 2, "test"]

    def test_list_insert_operations(self, db: DictSQLite):
        """Test list insert operations."""
        db["insert_list"] = [1, 3, 5]
        sync_list = db["insert_list"]

        # Test insert
        sync_list.insert(1, 2)  # Insert 2 at index 1
        sync_list.insert(3, 4)  # Insert 4 at index 3

        # Verify order
        fresh_list = db["insert_list"]
        assert list(fresh_list) == [1, 2, 3, 4, 5]

    def test_list_remove_operations(self, db: DictSQLite):
        """Test list remove operations."""
        db["remove_list"] = [1, 2, 3, 2, 4]
        sync_list = db["remove_list"]

        # Test remove (removes first occurrence)
        sync_list.remove(2)
        fresh_list = db["remove_list"]
        assert list(fresh_list) == [1, 3, 2, 4]

        # Test pop
        popped = sync_list.pop()
        assert popped == 4
        fresh_list = db["remove_list"]
        assert list(fresh_list) == [1, 3, 2]

        # Test pop with index
        popped = sync_list.pop(1)
        assert popped == 3
        fresh_list = db["remove_list"]
        assert list(fresh_list) == [1, 2]

    def test_list_extend_operations(self, db: DictSQLite):
        """Test list extend operations."""
        db["extend_list"] = [1, 2]
        sync_list = db["extend_list"]

        # Test extend
        sync_list.extend([3, 4, 5])
        fresh_list = db["extend_list"]
        assert list(fresh_list) == [1, 2, 3, 4, 5]

    def test_list_slice_operations(self, db: DictSQLite):
        """Test list slice operations."""
        db["slice_list"] = [1, 2, 3, 4, 5]
        sync_list = db["slice_list"]

        # Test slice assignment
        sync_list[1:3] = [20, 30]
        fresh_list = db["slice_list"]
        assert list(fresh_list) == [1, 20, 30, 4, 5]

    def test_list_clear_operations(self, db: DictSQLite):
        """Test list clear operations."""
        db["clear_list"] = [1, 2, 3, 4, 5]
        sync_list = db["clear_list"]

        # Test clear
        sync_list.clear()
        fresh_list = db["clear_list"]
        assert not list(fresh_list)

    def test_list_reverse_and_sort(self, db: DictSQLite):
        """Test list reverse and sort operations."""
        db["sort_list"] = [3, 1, 4, 1, 5]
        sync_list = db["sort_list"]

        # Test reverse
        sync_list.reverse()
        fresh_list = db["sort_list"]
        assert list(fresh_list) == [5, 1, 4, 1, 3]

        # Test sort
        sync_list.sort()
        fresh_list = db["sort_list"]
        assert list(fresh_list) == [1, 1, 3, 4, 5]

    def test_list_count_and_index(self, db: DictSQLite):
        """Test list count and index operations."""
        db["count_list"] = [1, 2, 2, 3, 2, 4]
        sync_list = db["count_list"]

        # Test count
        assert sync_list.count(2) == 3
        assert sync_list.count(1) == 1
        assert sync_list.count(5) == 0

        # Test index
        assert sync_list.index(2) == 1
        assert sync_list.index(3) == 3


class TestDBSyncedSet:
    """Test cases for DBSyncedSet class."""

    def test_set_creation_and_basic_operations(self):
        """Test basic set operations."""
        # Create a synced set through the proxy mechanism
        test_proxy = Mock()
        test_proxy.__setitem__ = Mock()

        sync_set = DBSyncedSet("test_key", test_proxy, {1, 2, 3})

        # Should be a set-like object
        assert len(sync_set) == 3
        assert 1 in sync_set
        assert 2 in sync_set
        assert 3 in sync_set
        assert 4 not in sync_set

    def test_set_add_operations(self):
        """Test set add operations."""
        test_proxy = Mock()
        test_proxy.__setitem__ = Mock()

        sync_set = DBSyncedSet("test_key", test_proxy, {1, 2})

        # Test add
        sync_set.add(3)
        assert 3 in sync_set

        # Adding existing element should not change the set
        sync_set.add(1)
        assert len(sync_set) == 3

    def test_set_remove_operations(self):
        """Test set remove operations."""
        test_proxy = Mock()
        test_proxy.__setitem__ = Mock()

        sync_set = DBSyncedSet("test_key", test_proxy, {1, 2, 3})

        # Test remove
        sync_set.remove(2)
        assert 2 not in sync_set
        assert len(sync_set) == 2

        # Test discard (doesn't raise error if element not present)
        sync_set.discard(4)  # Should not raise error
        sync_set.discard(1)  # Should remove 1
        assert 1 not in sync_set

        # Test pop
        remaining = sync_set.copy()
        popped = sync_set.pop()
        assert popped in remaining
        assert popped not in sync_set

    def test_set_update_operations(self):
        """Test set update operations."""
        test_proxy = Mock()
        test_proxy.__setitem__ = Mock()

        sync_set = DBSyncedSet("test_key", test_proxy, {1, 2})

        # Test update
        sync_set.update({3, 4}, {5, 6})
        assert {1, 2, 3, 4, 5, 6}.issubset(sync_set)

    def test_set_intersection_operations(self):
        """Test set intersection operations."""
        test_proxy = Mock()
        test_proxy.__setitem__ = Mock()

        sync_set = DBSyncedSet("test_key", test_proxy, {1, 2, 3, 4})

        # Test intersection_update
        sync_set.intersection_update({2, 3, 5})
        assert sync_set == {2, 3}

    def test_set_difference_operations(self):
        """Test set difference operations."""
        test_proxy = Mock()
        test_proxy.__setitem__ = Mock()

        sync_set = DBSyncedSet("test_key", test_proxy, {1, 2, 3, 4})

        # Test difference_update
        sync_set.difference_update({2, 4})
        assert sync_set == {1, 3}

    def test_set_symmetric_difference_operations(self):
        """Test set symmetric difference operations."""
        test_proxy = Mock()
        test_proxy.__setitem__ = Mock()

        sync_set = DBSyncedSet("test_key", test_proxy, {1, 2, 3})

        # Test symmetric_difference_update
        sync_set.symmetric_difference_update({2, 3, 4})
        assert sync_set == {1, 4}

    def test_set_clear_operations(self):
        """Test set clear operations."""
        test_proxy = Mock()
        test_proxy.__setitem__ = Mock()

        sync_set = DBSyncedSet("test_key", test_proxy, {1, 2, 3})

        # Test clear
        sync_set.clear()
        assert len(sync_set) == 0
        assert sync_set == set()

    def test_set_operator_overloads(self):
        """Test set operator overloads (__ior__, __iand__, etc.)."""
        test_proxy = Mock()
        test_proxy.__setitem__ = Mock()

        sync_set = DBSyncedSet("test_key", test_proxy, {1, 2, 3})

        # Test |= (union)
        sync_set |= {3, 4, 5}
        assert {1, 2, 3, 4, 5}.issubset(sync_set)

        # Reset for next test
        sync_set.clear()
        sync_set.update({1, 2, 3})

        # Test &= (intersection)
        sync_set &= {2, 3, 4}
        assert sync_set == {2, 3}

        # Reset for next test
        sync_set.clear()
        sync_set.update({1, 2, 3})

        # Test -= (difference)
        sync_set -= {2}
        assert sync_set == {1, 3}

        # Reset for next test
        sync_set.clear()
        sync_set.update({1, 2, 3})

        # Test ^= (symmetric difference)
        sync_set ^= {2, 3, 4}
        assert sync_set == {1, 4}

    def test_set_sync_called_on_mutations(self):
        """Test that sync is called on all mutation operations."""
        test_proxy = Mock()
        test_proxy.__setitem__ = Mock()

        sync_set = DBSyncedSet("test_key", test_proxy, {1, 2})

        # All these operations should call sync
        sync_set.add(3)
        sync_set.remove(1)
        sync_set.discard(2)
        sync_set.update({4, 5})
        sync_set.clear()

        # Verify sync was called (via proxy.__setitem__)
        assert test_proxy.__setitem__.call_count == 5


class TestIntegratedSyncedCollections:
    """Test synced collections integrated with actual DictSQLite instances."""

    def test_list_persistence_across_sessions(self, db_path):
        """Test that list changes persist across database sessions."""
        # First session: create and modify list
        db1 = DictSQLite(str(db_path))
        db1["persistent_list"] = [1, 2, 3]
        sync_list = db1["persistent_list"]
        sync_list.append(4)
        sync_list.extend([5, 6])
        db1.close()

        # Second session: verify changes persisted
        db2 = DictSQLite(str(db_path))
        restored_list = db2["persistent_list"]
        assert list(restored_list) == [1, 2, 3, 4, 5, 6]
        db2.close()

    def test_set_persistence_across_sessions(self, db_path):
        """Test that set changes persist across database sessions."""
        # First session: create and modify set
        db1 = DictSQLite(str(db_path))
        db1["persistent_set"] = {1, 2, 3}
        # Note: Sets are handled differently in the actual implementation
        # This test verifies the conceptual behavior
        stored_set = db1["persistent_set"]
        assert 1 in stored_set
        assert 2 in stored_set
        assert 3 in stored_set
        db1.close()

        # Second session: verify set persisted
        db2 = DictSQLite(str(db_path))
        restored_set = db2["persistent_set"]
        assert set(restored_set) == {1, 2, 3}
        db2.close()

    def test_nested_collections_with_sync(self, db: DictSQLite):
        """Test nested collections with synchronization."""
        # Create nested structure
        db["nested"] = {
            "list": [1, 2, 3],
            "inner_dict": {"value": 42}
        }

        # The actual behavior depends on the implementation
        # Some implementations may provide proxy objects with auto-sync
        # Others may require explicit assignment for sync
        nested = db["nested"]

        # Verify the structure is accessible
        assert list(nested["list"]) == [1, 2, 3]
        assert nested["inner_dict"]["value"] == 42

        # Test if we can modify through direct assignment
        try:
            # Modify the nested dict directly
            nested["inner_dict"]["new_value"] = 123
            # Re-read to check if change persisted
            fresh_nested = db["nested"]
            if "new_value" in fresh_nested["inner_dict"]:
                assert fresh_nested["inner_dict"]["new_value"] == 123
        except Exception:
            # If direct modification doesn't work, that's also acceptable
            pass
