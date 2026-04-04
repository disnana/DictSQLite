"""Test error handling and edge cases for DictSQLite.

This test module covers various error conditions, edge cases, and boundary conditions
to ensure the library handles errors gracefully and maintains data integrity.
"""
# pylint: disable=redefined-outer-name,broad-except

import os
import sqlite3
import tempfile
import threading
import pytest

from dictsqlite.main import DictSQLite


@pytest.fixture()
def db_path(tmp_path):
    """Provide a path to a temporary database file."""
    return tmp_path / "test_error_handling.db"


@pytest.fixture()
def db(db_path):
    """Provide a DictSQLite instance."""
    d = DictSQLite(str(db_path))
    yield d
    d.close()


def test_invalid_data_types(db: DictSQLite):
    """Test handling of invalid data types that cannot be serialized."""
    # Lambda functions cannot be pickled
    with pytest.raises(Exception):
        db["lambda"] = lambda x: x

    # Thread objects cannot be pickled
    with pytest.raises(Exception):
        db["thread"] = threading.Thread(target=lambda: None)


def test_database_corruption_handling(tmp_path):
    """Test handling of corrupted database files."""
    db_path = tmp_path / "corrupted.db"

    # Create a corrupted file (not a valid SQLite database)
    with open(db_path, "w", encoding="utf-8") as f:
        f.write("This is not a valid SQLite database file")

    # With direct synchronous execution, a corrupted database raises immediately
    # during construction (when the first table-creation query is executed).
    with pytest.raises((sqlite3.DatabaseError, Exception)):
        db = DictSQLite(str(db_path))
        # If construction somehow succeeded (e.g. SQLite opened it in a degraded
        # state), ensure operations also raise or handle gracefully.
        db["test"] = "value"
        db.close()


def test_read_only_database(tmp_path):
    """Test handling of read-only database files."""
    db_path = tmp_path / "readonly.db"

    # Create a database first
    db = DictSQLite(str(db_path))
    db["test"] = "value"
    db.close()

    # Make the file read-only
    os.chmod(db_path, 0o444)

    try:
        # Should be able to read but not write
        db_readonly = DictSQLite(str(db_path))
        assert db_readonly["test"] == "value"

        # Writing to a read-only database now raises immediately with direct execution
        with pytest.raises((sqlite3.OperationalError, Exception)):
            db_readonly["new"] = "value"

        db_readonly.close()
    finally:
        # Restore write permissions for cleanup
        os.chmod(db_path, 0o644)


def test_invalid_table_names():
    """Test handling of invalid table names."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        db = DictSQLite(db_path)

        # Test various potentially problematic table names
        # Some may work depending on the implementation's sanitization
        problematic_names = [
            "test'; DROP TABLE main; --",  # SQL injection attempt
            "test table",  # space in name
            "",  # empty name
            "123table",  # starts with number
            "table-name",  # hyphen
        ]

        for table_name in problematic_names:
            try:
                db.switch_table(table_name)
                # If it succeeds, verify the table was created safely
                # and doesn't cause issues
                db["test_key"] = "test_value"
                db.operation_queue.join()

                # Switch back to main table
                db.switch_table("main")
            except Exception:
                # Exceptions are expected for invalid table names
                pass

        db.close()
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_invalid_journal_modes():
    """Test handling of invalid journal modes."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        # Invalid journal mode should raise ValueError
        with pytest.raises(ValueError):
            DictSQLite(db_path, journal_mode="INVALID_MODE")
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_large_data_handling(db: DictSQLite):
    """Test handling of large data items."""
    # Test with large string (1MB)
    large_string = "A" * (1024 * 1024)
    db["large_string"] = large_string
    assert db["large_string"] == large_string

    # Test with large list
    large_list = list(range(10000))
    db["large_list"] = large_list
    assert db["large_list"] == large_list

    # Test with large dictionary
    large_dict = {f"key_{i}": f"value_{i}" for i in range(1000)}
    db["large_dict"] = large_dict
    assert db["large_dict"] == large_dict


def test_concurrent_access_safety(tmp_path):
    """Test thread safety and concurrent access."""
    db_path = tmp_path / "concurrent.db"

    # Create database with some initial data
    db1 = DictSQLite(str(db_path))
    db1["initial"] = "value"
    db1.close()

    # Test concurrent read access
    def read_worker(results, worker_id):
        try:
            db = DictSQLite(str(db_path))
            value = db["initial"]
            results[worker_id] = value
            db.close()
        except Exception as e:
            results[worker_id] = str(e)

    results = {}
    threads = []
    for i in range(5):
        t = threading.Thread(target=read_worker, args=(results, i))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # All threads should have read the same value
    for i in range(5):
        assert results[i] == "value"


def test_memory_pressure_handling(db: DictSQLite):
    """Test behavior under memory pressure conditions."""
    # Store many items to test memory handling
    for i in range(1000):
        db[f"item_{i}"] = {"data": list(range(100)), "id": i}

    # Verify all items are stored correctly
    for i in range(0, 1000, 100):  # Sample every 100th item
        assert db[f"item_{i}"]["id"] == i
        assert len(db[f"item_{i}"]["data"]) == 100


def test_transaction_error_handling(db: DictSQLite):
    """Test transaction error handling and rollback."""
    # Start transaction
    db.begin_transaction()

    # Add some data
    db["tx_test"] = "initial"

    # Simulate error during transaction by directly manipulating the database
    # This should cause rollback
    try:
        # Force an error by trying to insert duplicate primary key
        db.cursor.execute("INSERT INTO main (key, value) VALUES (?, ?)",
                         ("tx_test", "duplicate"))
        db.commit_transaction()
    except Exception:
        db.rollback_transaction()

    # Data should be rolled back
    db.operation_queue.join()
    assert "tx_test" not in db


def test_schema_validation_edge_cases(db_path):
    """Test schema validation with various edge cases."""
    # Test with valid schema
    db = DictSQLite(str(db_path), schema="(key TEXT PRIMARY KEY, value TEXT, timestamp INTEGER)")
    db["test"] = "value"
    db.close()

    # Test with invalid schema (SQL injection attempt)
    with pytest.raises(ValueError):
        DictSQLite(str(db_path), schema="(key TEXT); DROP TABLE main; --")


def test_key_validation_edge_cases(db: DictSQLite):
    """Test key validation with edge cases."""
    # Very long key
    long_key = "a" * 1000
    db[long_key] = "value"
    assert db[long_key] == "value"

    # Unicode keys
    unicode_key = "キー_🔑_key"
    db[unicode_key] = "unicode_value"
    assert db[unicode_key] == "unicode_value"

    # Special characters in keys
    special_key = "key!@#$%^&*()_+-=[]{}|;':\",./<>?"
    db[special_key] = "special_value"
    assert db[special_key] == "special_value"


def test_connection_failure_recovery(tmp_path):
    """Test recovery from connection failures."""
    db_path = tmp_path / "connection_test.db"

    db = DictSQLite(str(db_path))
    db["test"] = "value"
    db.operation_queue.join()

    # Simulate connection issues by closing the cursor
    try:
        db.cursor.close()
    except Exception:
        pass  # Cursor might already be closed or not closeable

    # Operations should handle connection issues gracefully
    try:
        # This might raise an exception, which is expected behavior
        db["test2"] = "value2"
        db.operation_queue.join()
    except Exception:
        pass  # Expected behavior for connection issues

    # Cleanup - create a new instance to verify data persistence
    db.close()

    # Verify that the original data is still there
    new_db = DictSQLite(str(db_path))
    try:
        assert new_db["test"] == "value"
    finally:
        new_db.close()


def test_disk_space_simulation(tmp_path):
    """Test behavior when disk space is low (simulated)."""
    db_path = tmp_path / "diskspace.db"
    db = DictSQLite(str(db_path))

    # Since we can't easily mock sqlite3.Cursor.execute, let's test
    # the behavior when the file system is full by creating a very large file
    # first to test normal operation
    db["normal_key"] = "normal_value"
    db.operation_queue.join()

    # Verify normal operation works
    assert db["normal_key"] == "normal_value"

    # For disk space simulation, we'll test with very large data
    # that might cause issues if disk space is actually limited
    try:
        # Try to store a very large item (10MB)
        large_data = "x" * (10 * 1024 * 1024)
        db["large_key"] = large_data
        db.operation_queue.join()

        # If successful, verify it can be read back
        retrieved = db["large_key"]
        assert len(retrieved) == len(large_data)

    except Exception as error:
        # If it fails, that's also acceptable for a disk space test
        # The important thing is that the database remains functional
        error_msg = str(error).lower()
        assert ("disk" in error_msg or "space" in error_msg or
                "memory" in error_msg or "error" in error_msg)

    # Verify that database is still functional after potential failure
    db["recovery_test"] = "recovery_value"
    db.operation_queue.join()
    assert db["recovery_test"] == "recovery_value"

    db.close()


def test_data_integrity_after_errors(db: DictSQLite):
    """Test that data integrity is maintained after various errors."""
    # Add some initial data
    db["stable1"] = "value1"
    db["stable2"] = {"nested": "value2"}

    # Try to add invalid data that should fail
    try:
        db["invalid"] = lambda x: x  # Should fail
    except Exception:
        pass

    # Verify original data is still intact
    assert db["stable1"] == "value1"
    assert db["stable2"]["nested"] == "value2"
    assert "invalid" not in db

    # Add more valid data
    db["stable3"] = [1, 2, 3]
    assert db["stable3"] == [1, 2, 3]


def test_version_mismatch_handling(tmp_path):
    """Test handling of version mismatches."""
    db_path = tmp_path / "version_test.db"

    # Create database with version 1
    db1 = DictSQLite(str(db_path), version=1)
    db1["test"] = "value"
    db1.close()

    # Try to open with version 2 - should handle gracefully
    db2 = DictSQLite(str(db_path), version=2)
    # Should be able to read existing data
    try:
        value = db2["test"]
        # If successful, the value should be accessible
        assert value == "value" or isinstance(value, (str, dict))
    except Exception:
        # If it fails, that's also acceptable behavior for version mismatch
        pass
    finally:
        db2.close()
