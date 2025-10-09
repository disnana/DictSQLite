//! Unit tests for JSONB and table support

#[cfg(test)]
mod tests {
    use crate::{Config, StorageMode};
    use std::str::FromStr;

    #[test]
    fn test_storage_mode_from_str() {
        // Test valid storage modes
        assert_eq!(
            StorageMode::from_str("pickle").unwrap(),
            StorageMode::Pickle
        );
        assert_eq!(StorageMode::from_str("json").unwrap(), StorageMode::Json);
        assert_eq!(StorageMode::from_str("jsonb").unwrap(), StorageMode::JsonB);
        assert_eq!(StorageMode::from_str("bytes").unwrap(), StorageMode::Bytes);

        // Test case insensitivity
        assert_eq!(StorageMode::from_str("JSONB").unwrap(), StorageMode::JsonB);
        assert_eq!(StorageMode::from_str("Json").unwrap(), StorageMode::Json);

        // Test invalid mode
        assert!(StorageMode::from_str("invalid").is_err());
    }

    #[test]
    fn test_storage_mode_default() {
        let mode = StorageMode::default();
        assert_eq!(mode, StorageMode::Pickle);
    }

    #[test]
    fn test_config_defaults() {
        let config = Config::default();
        assert_eq!(config.storage_mode, StorageMode::Pickle);
        assert_eq!(config.table_name, "main");
    }

    #[test]
    fn test_messagepack_encoding() {
        // Test that MessagePack encoding works
        let data = serde_json::json!({
            "key": "value",
            "numbers": [1, 2, 3],
            "nested": {"inner": "data"}
        });

        let encoded = rmp_serde::to_vec(&data).unwrap();
        assert!(!encoded.is_empty());

        let decoded: serde_json::Value = rmp_serde::from_slice(&encoded).unwrap();
        assert_eq!(decoded, data);
    }

    #[test]
    fn test_messagepack_size_efficiency() {
        // Test that MessagePack is more compact than JSON
        let data = serde_json::json!({
            "users": [
                {"name": "Alice", "age": 30},
                {"name": "Bob", "age": 25},
                {"name": "Charlie", "age": 35}
            ]
        });

        let json_bytes = serde_json::to_vec(&data).unwrap();
        let msgpack_bytes = rmp_serde::to_vec(&data).unwrap();

        // MessagePack should be smaller
        assert!(msgpack_bytes.len() < json_bytes.len());
    }

    #[test]
    fn test_table_prefix_format() {
        // Test that table prefixing works as expected
        let table_name = "users";
        let key = "user1";
        let full_key = format!("{}:{}", table_name, key);

        assert_eq!(full_key, "users:user1");

        // Test extraction
        let parts: Vec<&str> = full_key.splitn(2, ':').collect();
        assert_eq!(parts.len(), 2);
        assert_eq!(parts[0], "users");
        assert_eq!(parts[1], "user1");
    }

    #[test]
    fn test_default_table_handling() {
        // Test that empty table name and "main" are treated the same
        let config = Config::default();
        assert_eq!(config.table_name, "main");

        // Keys without prefix should go to main table
        let key = "key1";
        let table_name = &config.table_name;

        let should_prefix = !table_name.is_empty() && table_name != "main";
        assert!(!should_prefix); // Should not prefix for "main"
    }

    #[test]
    fn test_json_serialization_basic_types() {
        // Test basic JSON types can be serialized/deserialized
        let test_cases = vec![
            serde_json::json!(null),
            serde_json::json!(true),
            serde_json::json!(false),
            serde_json::json!(42),
            serde_json::json!(3.14),
            serde_json::json!("hello"),
            serde_json::json!([1, 2, 3]),
            serde_json::json!({"key": "value"}),
        ];

        for original in test_cases {
            // JSON
            let json_bytes = serde_json::to_vec(&original).unwrap();
            let json_decoded: serde_json::Value = serde_json::from_slice(&json_bytes).unwrap();
            assert_eq!(json_decoded, original);

            // MessagePack
            let msgpack_bytes = rmp_serde::to_vec(&original).unwrap();
            let msgpack_decoded: serde_json::Value = rmp_serde::from_slice(&msgpack_bytes).unwrap();
            assert_eq!(msgpack_decoded, original);
        }
    }

    #[test]
    fn test_nested_structures() {
        let complex_data = serde_json::json!({
            "users": [
                {
                    "name": "Alice",
                    "age": 30,
                    "roles": ["admin", "user"],
                    "metadata": {
                        "created": "2024-01-01",
                        "active": true
                    }
                }
            ],
            "settings": {
                "theme": "dark",
                "notifications": {
                    "email": true,
                    "push": false
                }
            }
        });

        // Should serialize and deserialize correctly
        let msgpack = rmp_serde::to_vec(&complex_data).unwrap();
        let decoded: serde_json::Value = rmp_serde::from_slice(&msgpack).unwrap();
        assert_eq!(decoded, complex_data);
    }
}
