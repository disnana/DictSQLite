//! v6.0 API移行とpythonize統合のテスト
//!
//! このモジュールはv6.0の変更を検証します:
//! - PyO3 0.27 API移行 (Py<PyAny>)
//! - pythonize統合 (フォールバック付き)
//! - 圧縮機能の継続動作

use crate::{Config, StorageEngine};
use tempfile::tempdir;

/// Config構造体のデフォルト値テスト
#[test]
fn test_config_defaults() {
    let config = Config::default();

    assert_eq!(config.hot_tier_capacity, 1_000_000);
    assert_eq!(config.pool_size, 32); // v7.0: 高負荷対応
    assert!(!config.enable_compression);
    assert_eq!(config.compression_level, 3);
}

/// 圧縮設定を有効にしたConfigテスト
#[test]
fn test_config_with_compression() {
    let config = Config {
        enable_compression: true,
        compression_level: 9,
        ..Default::default()
    };

    assert!(config.enable_compression);
    assert_eq!(config.compression_level, 9);
}

/// StorageEngine基本動作テスト
#[test]
fn test_storage_engine_basic_operations() {
    let dir = tempdir().unwrap();
    let db_path = dir.path().join("test_v6.db");
    let config = Config::default();

    let storage = StorageEngine::new(db_path.to_str().unwrap(), &config).unwrap();

    // 基本的なset/get
    let key = "test_key";
    let value = b"test_value";

    storage.set(key, value).unwrap();
    let result = storage.get(key).unwrap();

    assert!(result.is_some());
    assert_eq!(result.unwrap(), value);
}

/// StorageEngine削除テスト
#[test]
fn test_storage_engine_delete() {
    let dir = tempdir().unwrap();
    let db_path = dir.path().join("test_delete.db");
    let config = Config::default();

    let storage = StorageEngine::new(db_path.to_str().unwrap(), &config).unwrap();

    let key = "delete_key";
    let value = b"to_be_deleted";

    storage.set(key, value).unwrap();
    assert!(storage.get(key).unwrap().is_some());

    storage.delete(key).unwrap();
    assert!(storage.get(key).unwrap().is_none());
}

/// バルクインサートテスト
#[test]
fn test_storage_engine_bulk_insert() {
    use std::collections::HashMap;

    let dir = tempdir().unwrap();
    let db_path = dir.path().join("test_bulk.db");
    let config = Config::default();

    let storage = StorageEngine::new(db_path.to_str().unwrap(), &config).unwrap();

    let mut items = HashMap::new();
    for i in 0..100 {
        items.insert(format!("key_{}", i), format!("value_{}", i).into_bytes());
    }

    storage.bulk_insert(&items).unwrap();

    // 確認
    for i in 0..100 {
        let result = storage.get(&format!("key_{}", i)).unwrap();
        assert!(result.is_some());
        assert_eq!(result.unwrap(), format!("value_{}", i).into_bytes());
    }
}

/// 圧縮とバルク操作の組み合わせテスト
#[test]
fn test_compression_with_bulk() {
    use std::collections::HashMap;

    let dir = tempdir().unwrap();
    let db_path = dir.path().join("test_compress_bulk.db");
    let config = Config {
        enable_compression: true,
        compression_level: 3,
        ..Default::default()
    };

    let storage = StorageEngine::new(db_path.to_str().unwrap(), &config).unwrap();

    let mut items = HashMap::new();
    // 圧縮効果が出る繰り返しデータ
    for i in 0..50 {
        items.insert(
            format!("bulk_key_{}", i),
            format!("repeated_value_{}_", i).repeat(100).into_bytes(),
        );
    }

    storage.bulk_insert(&items).unwrap();

    // 確認
    for i in 0..50 {
        let result = storage.get(&format!("bulk_key_{}", i)).unwrap();
        assert!(result.is_some());
        let expected = format!("repeated_value_{}_", i).repeat(100).into_bytes();
        assert_eq!(result.unwrap(), expected);
    }
}

/// ウォームキャッシュのプロモーションテスト
#[test]
fn test_warm_cache_promotion() {
    let dir = tempdir().unwrap();
    let db_path = dir.path().join("test_warm.db");
    let config = Config::default();

    let storage = StorageEngine::new(db_path.to_str().unwrap(), &config).unwrap();

    let key = "warm_key";
    let value = b"warm_value_repeated".repeat(20);

    storage.set(key, &value).unwrap();

    // 複数回アクセスでウォームキャッシュにプロモート
    for _ in 0..5 {
        let result = storage.get(key).unwrap();
        assert!(result.is_some());
    }

    // ウォームキャッシュから取得
    let cached = storage.get(key).unwrap();
    assert!(cached.is_some());
    assert_eq!(cached.unwrap(), value);
}
