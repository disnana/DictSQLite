//! Unit tests for storage operations

#[cfg(test)]
mod tests {
    use crate::{Config, StorageEngine};
    use std::collections::HashMap;
    use tempfile::NamedTempFile;

    #[test]
    fn test_storage_engine_creation() {
        let temp_file = NamedTempFile::new().unwrap();
        let db_path = temp_file.path().to_str().unwrap();

        let config = Config::default();
        let storage = StorageEngine::new(db_path, &config);

        assert!(storage.is_ok());
    }

    #[test]
    fn test_storage_set_and_get() {
        let temp_file = NamedTempFile::new().unwrap();
        let db_path = temp_file.path().to_str().unwrap();

        let config = Config::default();
        let mut storage = StorageEngine::new(db_path, &config).unwrap();

        // Set a value
        let key = "test_key";
        let value = b"test_value";
        storage.set(key, value).unwrap();

        // Get the value
        let result = storage.get(key).unwrap();
        assert!(result.is_some());
        assert_eq!(result.unwrap(), value);
    }

    #[test]
    fn test_storage_bulk_insert() {
        let temp_file = NamedTempFile::new().unwrap();
        let db_path = temp_file.path().to_str().unwrap();

        let config = Config::default();
        let mut storage = StorageEngine::new(db_path, &config).unwrap();

        // Create bulk data
        let mut items = HashMap::new();
        for i in 0..100 {
            items.insert(format!("key_{}", i), vec![i as u8; 10]);
        }

        // Bulk insert
        storage.bulk_insert(&items).unwrap();

        // Verify all items
        for i in 0..100 {
            let result = storage.get(&format!("key_{}", i)).unwrap();
            assert!(result.is_some());
        }
    }

    #[test]
    fn test_storage_delete() {
        let temp_file = NamedTempFile::new().unwrap();
        let db_path = temp_file.path().to_str().unwrap();

        let config = Config::default();
        let mut storage = StorageEngine::new(db_path, &config).unwrap();

        // Set and then delete
        let key = "delete_test";
        let value = b"to_be_deleted";
        storage.set(key, value).unwrap();

        // Verify it exists
        assert!(storage.get(key).unwrap().is_some());

        // Delete it
        storage.delete(key).unwrap();

        // Verify it's gone
        assert!(storage.get(key).unwrap().is_none());
    }

    #[test]
    fn test_storage_persistence() {
        let temp_file = NamedTempFile::new().unwrap();
        let db_path = temp_file.path().to_str().unwrap();

        let config = Config::default();

        // Write data
        {
            let mut storage = StorageEngine::new(db_path, &config).unwrap();
            storage.set("persist_key", b"persist_value").unwrap();
        }

        // Read data in new instance
        {
            let storage = StorageEngine::new(db_path, &config).unwrap();
            let result = storage.get("persist_key").unwrap();
            assert!(result.is_some());
            assert_eq!(result.unwrap(), b"persist_value");
        }
    }

    #[test]
    fn test_storage_warm_tier_promotion() {
        let temp_file = NamedTempFile::new().unwrap();
        let db_path = temp_file.path().to_str().unwrap();

        let config = Config::default();
        let storage = StorageEngine::new(db_path, &config).unwrap();

        // Access the same key multiple times
        // (warm tier promotion logic would kick in based on access patterns)
        for _ in 0..5 {
            let _ = storage.get("frequent_key");
        }

        // This is primarily testing that the access tracking doesn't crash
        assert!(true);
    }
}
