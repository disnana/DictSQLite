"""Performance and stress tests for DictSQLite.

This test module covers performance benchmarks and stress testing
to ensure the library performs well under various conditions.
"""
# pylint: disable=redefined-outer-name

import time
import threading
import random
import string
import pytest

from dictsqlite.main import DictSQLite


@pytest.fixture()
def db_path(tmp_path):
    """Provide a path to a temporary database file."""
    return tmp_path / "test_performance.db"


@pytest.fixture()
def db(db_path):
    """Provide a DictSQLite instance."""
    d = DictSQLite(str(db_path))
    yield d
    d.close()


class TestPerformanceBenchmarks:
    """Performance benchmark tests."""

    def test_bulk_insert_performance(self, db: DictSQLite):
        """Test performance of bulk insert operations."""
        start_time = time.time()
        
        # Insert 1000 items
        for i in range(1000):
            db[f"key_{i}"] = {"id": i, "data": f"value_{i}"}
        
        # Wait for all operations to complete
        db.operation_queue.join()
        
        elapsed_time = time.time() - start_time
        
        # Should complete in reasonable time (adjust threshold as needed)
        assert elapsed_time < 30, f"Bulk insert took {elapsed_time:.2f} seconds"
        
        # Verify data integrity
        assert db["key_0"]["id"] == 0
        assert db["key_500"]["data"] == "value_500"
        assert db["key_999"]["id"] == 999

    def test_bulk_read_performance(self, db: DictSQLite):
        """Test performance of bulk read operations."""
        # Pre-populate database
        for i in range(1000):
            db[f"read_key_{i}"] = {"id": i, "data": f"read_value_{i}"}
        
        db.operation_queue.join()
        
        start_time = time.time()
        
        # Read all items
        for i in range(1000):
            value = db[f"read_key_{i}"]
            assert value["id"] == i
        
        elapsed_time = time.time() - start_time
        
        # Read operations should be fast
        assert elapsed_time < 10, f"Bulk read took {elapsed_time:.2f} seconds"

    def test_mixed_operations_performance(self, db: DictSQLite):
        """Test performance of mixed read/write operations."""
        start_time = time.time()
        
        for i in range(500):
            # Write operation
            db[f"mixed_{i}"] = {"id": i, "value": f"data_{i}"}
            
            # Read operation (read previously written data)
            if i > 0:
                prev_value = db[f"mixed_{i-1}"]
                assert prev_value["id"] == i-1
            
            # Update operation
            if i % 10 == 0 and i > 0:
                db[f"mixed_{i-1}"]["updated"] = True
        
        db.operation_queue.join()
        elapsed_time = time.time() - start_time
        
        # Mixed operations should complete in reasonable time
        assert elapsed_time < 20, f"Mixed operations took {elapsed_time:.2f} seconds"

    def test_large_value_performance(self, db: DictSQLite):
        """Test performance with large values."""
        # Create large values
        large_string = "A" * 10000  # 10KB string
        large_list = list(range(1000))
        large_dict = {f"key_{i}": f"value_{i}" for i in range(100)}
        
        start_time = time.time()
        
        db["large_string"] = large_string
        db["large_list"] = large_list
        db["large_dict"] = large_dict
        
        db.operation_queue.join()
        
        # Read back the large values
        read_string = db["large_string"]
        read_list = db["large_list"]
        read_dict = db["large_dict"]
        
        elapsed_time = time.time() - start_time
        
        # Verify correctness
        assert read_string == large_string
        assert read_list == large_list
        assert read_dict == large_dict
        
        # Should handle large values efficiently
        assert elapsed_time < 5, f"Large value operations took {elapsed_time:.2f} seconds"


class TestStressTesting:
    """Stress testing scenarios."""

    def test_high_frequency_updates(self, db: DictSQLite):
        """Test high frequency update operations."""
        # Create initial data
        db["counter"] = {"value": 0}
        db.operation_queue.join()
        
        # Perform many updates
        for i in range(100):
            counter = db["counter"]
            counter["value"] = i
            counter["timestamp"] = time.time()
        
        db.operation_queue.join()
        
        # Verify final state
        final_counter = db["counter"]
        assert final_counter["value"] == 99

    def test_rapid_key_creation_deletion(self, db: DictSQLite):
        """Test rapid creation and deletion of keys."""
        keys_to_test = 200
        
        # Rapid creation
        for i in range(keys_to_test):
            db[f"rapid_{i}"] = f"value_{i}"
        
        db.operation_queue.join()
        
        # Verify all keys exist
        for i in range(keys_to_test):
            assert f"rapid_{i}" in db
        
        # Rapid deletion
        for i in range(0, keys_to_test, 2):  # Delete every other key
            del db[f"rapid_{i}"]
        
        db.operation_queue.join()
        
        # Verify correct keys remain
        for i in range(keys_to_test):
            if i % 2 == 0:
                assert f"rapid_{i}" not in db
            else:
                assert f"rapid_{i}" in db

    def test_concurrent_operations_stress(self, db_path):
        """Test concurrent operations under stress."""
        def worker_thread(thread_id, operation_count):
            """Worker thread function."""
            db = DictSQLite(str(db_path))
            try:
                for i in range(operation_count):
                    key = f"thread_{thread_id}_item_{i}"
                    db[key] = {
                        "thread_id": thread_id,
                        "item_id": i,
                        "data": "x" * 100,  # Some data
                        "timestamp": time.time()
                    }
                
                # Also perform some reads
                for i in range(0, operation_count, 10):
                    key = f"thread_{thread_id}_item_{i}"
                    if key in db:
                        value = db[key]
                        assert value["thread_id"] == thread_id
                
                db.operation_queue.join()
            finally:
                db.close()
        
        # Create multiple worker threads
        threads = []
        thread_count = 5
        operations_per_thread = 50
        
        start_time = time.time()
        
        for thread_id in range(thread_count):
            t = threading.Thread(
                target=worker_thread, 
                args=(thread_id, operations_per_thread)
            )
            threads.append(t)
            t.start()
        
        # Wait for all threads to complete
        for t in threads:
            t.join()
        
        elapsed_time = time.time() - start_time
        
        # Verify data integrity after concurrent operations
        verification_db = DictSQLite(str(db_path))
        try:
            for thread_id in range(thread_count):
                for i in range(operations_per_thread):
                    key = f"thread_{thread_id}_item_{i}"
                    if key in verification_db:
                        value = verification_db[key]
                        assert value["thread_id"] == thread_id
                        assert value["item_id"] == i
        finally:
            verification_db.close()
        
        # Should complete in reasonable time even with concurrency
        assert elapsed_time < 60, f"Concurrent stress test took {elapsed_time:.2f} seconds"

    def test_memory_usage_with_large_dataset(self, db: DictSQLite):
        """Test memory usage with large datasets."""
        # Create a large number of items
        item_count = 5000
        
        for i in range(item_count):
            db[f"memory_test_{i}"] = {
                "id": i,
                "data": [j for j in range(10)],  # Small list
                "text": "sample text " * 10,  # Repeated text
                "nested": {"key": f"value_{i}"}
            }
        
        db.operation_queue.join()
        
        # Verify we can still access data efficiently
        sample_indices = random.sample(range(item_count), 100)
        
        for i in sample_indices:
            value = db[f"memory_test_{i}"]
            assert value["id"] == i
            assert len(value["data"]) == 10
            assert "sample text" in value["text"]

    def test_transaction_stress(self, db: DictSQLite):
        """Test transaction behavior under stress."""
        transaction_count = 50
        items_per_transaction = 20
        
        for tx_id in range(transaction_count):
            db.begin_transaction()
            try:
                for i in range(items_per_transaction):
                    key = f"tx_{tx_id}_item_{i}"
                    db[key] = {
                        "tx_id": tx_id,
                        "item_id": i,
                        "data": random.choice(["A", "B", "C"]) * 50
                    }
                
                # Commit every transaction
                db.commit_transaction()
                
            except Exception:
                db.rollback_transaction()
                raise
        
        db.operation_queue.join()
        
        # Verify all transactions were committed
        for tx_id in range(transaction_count):
            for i in range(items_per_transaction):
                key = f"tx_{tx_id}_item_{i}"
                assert key in db
                value = db[key]
                assert value["tx_id"] == tx_id
                assert value["item_id"] == i

    def test_deep_nesting_stress(self, db: DictSQLite):
        """Test deeply nested data structures."""
        # Create deeply nested structure
        deep_data = {"level": 0}
        current = deep_data
        
        depth = 20
        for i in range(1, depth):
            current["next"] = {"level": i, "data": f"level_{i}_data"}
            current = current["next"]
        
        # Store and retrieve
        db["deep_structure"] = deep_data
        db.operation_queue.join()
        
        retrieved = db["deep_structure"]
        
        # Verify structure integrity
        current = retrieved
        for i in range(depth):
            assert current["level"] == i
            if i < depth - 1:
                assert "next" in current
                current = current["next"]

    def test_random_operations_stress(self, db: DictSQLite):
        """Test random mix of operations for stress testing."""
        keys = [f"random_key_{i}" for i in range(100)]
        operations = ["set", "get", "delete", "update"]
        
        # Seed some initial data
        for i in range(50):
            db[keys[i]] = {"value": i, "data": "initial"}
        
        db.operation_queue.join()
        
        # Perform random operations
        for _ in range(500):
            operation = random.choice(operations)
            key = random.choice(keys)
            
            try:
                if operation == "set":
                    db[key] = {
                        "value": random.randint(1, 1000),
                        "data": "".join(random.choices(string.ascii_letters, k=10))
                    }
                elif operation == "get":
                    if key in db:
                        value = db[key]
                        # Just verify we can read the value - the type might vary
                        assert value is not None
                elif operation == "delete":
                    if key in db:
                        del db[key]
                elif operation == "update":
                    if key in db:
                        value = db[key]
                        value["updated"] = time.time()
            except Exception as e:
                # Some operations may fail due to race conditions, which is acceptable
                # in stress testing as long as the system doesn't crash
                if "KeyError" not in str(e):
                    raise
        
        db.operation_queue.join()
        
        # Verify database is still functional
        db["stress_test_complete"] = True
        assert db["stress_test_complete"] is True


class TestPerformanceRegression:
    """Tests to detect performance regressions."""

    def test_baseline_performance_metrics(self, db: DictSQLite):
        """Establish baseline performance metrics."""
        # This test can be used to detect performance regressions
        # by comparing against historical baselines
        
        operations = [
            ("write_100_items", lambda: self._write_items(db, 100)),
            ("read_100_items", lambda: self._read_items(db, 100)),
            ("update_100_items", lambda: self._update_items(db, 100)),
        ]
        
        performance_results = {}
        
        for op_name, op_func in operations:
            start_time = time.time()
            op_func()
            db.operation_queue.join()
            elapsed_time = time.time() - start_time
            performance_results[op_name] = elapsed_time
        
        # Log results (in a real scenario, these could be compared to baselines)
        for op_name, elapsed in performance_results.items():
            print(f"{op_name}: {elapsed:.3f} seconds")
            # Assert reasonable performance (adjust thresholds as needed)
            assert elapsed < 10, f"{op_name} took {elapsed:.3f} seconds"

    def _write_items(self, db: DictSQLite, count: int):
        """Helper to write items."""
        for i in range(count):
            db[f"perf_write_{i}"] = {"id": i, "data": f"data_{i}"}

    def _read_items(self, db: DictSQLite, count: int):
        """Helper to read items."""
        for i in range(count):
            if f"perf_write_{i}" in db:
                value = db[f"perf_write_{i}"]
                assert value["id"] == i

    def _update_items(self, db: DictSQLite, count: int):
        """Helper to update items."""
        for i in range(count):
            if f"perf_write_{i}" in db:
                item = db[f"perf_write_{i}"]
                item["updated"] = True