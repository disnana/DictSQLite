//! v5.1圧縮機能のテスト
//!
//! このモジュールはZstd圧縮機能の動作を検証します。
//! - 圧縮有効時のデータ圧縮/展開
//! - 非圧縮データとの後方互換性
//! - マジックバイトによる圧縮データ識別

use crate::{Config, StorageEngine};
use tempfile::tempdir;

/// 圧縮有効設定を作成
fn create_compression_config() -> Config {
    Config {
        enable_compression: true,
        compression_level: 3,
        ..Default::default()
    }
}

/// 圧縮無効設定を作成
fn create_no_compression_config() -> Config {
    Config {
        enable_compression: false,
        ..Default::default()
    }
}

#[test]
fn test_compression_set_and_get() {
    let dir = tempdir().unwrap();
    let db_path = dir.path().join("test_compression.db");
    let config = create_compression_config();

    let storage = StorageEngine::new(db_path.to_str().unwrap(), &config).unwrap();

    // テストデータ（圧縮効果が出やすい反復データ）
    let key = "test_key";
    let value = b"Hello World! ".repeat(100); // 1300バイトの反復データ

    // 保存と取得
    storage.set(key, &value).unwrap();
    let retrieved = storage.get(key).unwrap();

    assert!(retrieved.is_some());
    assert_eq!(retrieved.unwrap(), value);
}

#[test]
fn test_compression_small_data_not_compressed() {
    let dir = tempdir().unwrap();
    let db_path = dir.path().join("test_small.db");
    let config = create_compression_config();

    let storage = StorageEngine::new(db_path.to_str().unwrap(), &config).unwrap();

    // 小さいデータ（128バイト未満）は圧縮されない
    let key = "small_key";
    let value = b"Short data";

    storage.set(key, value).unwrap();
    let retrieved = storage.get(key).unwrap();

    assert!(retrieved.is_some());
    assert_eq!(retrieved.unwrap(), value);
}

#[test]
fn test_no_compression_backward_compatible() {
    let dir = tempdir().unwrap();
    let db_path = dir.path().join("test_no_compress.db");
    let config = create_no_compression_config();

    let storage = StorageEngine::new(db_path.to_str().unwrap(), &config).unwrap();

    // 圧縮無効の場合、そのまま保存・取得
    let key = "no_compress_key";
    let value = b"This data will not be compressed".repeat(50);

    storage.set(key, &value).unwrap();
    let retrieved = storage.get(key).unwrap();

    assert!(retrieved.is_some());
    assert_eq!(retrieved.unwrap(), value);
}

#[test]
fn test_compression_cross_config() {
    let dir = tempdir().unwrap();
    let db_path = dir.path().join("test_cross.db");

    // 圧縮有効で保存
    let config_compress = create_compression_config();
    {
        let storage = StorageEngine::new(db_path.to_str().unwrap(), &config_compress).unwrap();
        let value = b"Compressed data for cross-config test".repeat(50);
        storage.set("cross_key", &value).unwrap();
    }

    // 圧縮無効で読み取り（後方互換性テスト）
    let config_no_compress = create_no_compression_config();
    {
        let storage = StorageEngine::new(db_path.to_str().unwrap(), &config_no_compress).unwrap();
        let retrieved = storage.get("cross_key").unwrap();

        assert!(retrieved.is_some());
        let value = b"Compressed data for cross-config test".repeat(50);
        assert_eq!(retrieved.unwrap(), value);
    }
}

#[test]
fn test_compression_levels() {
    for level in [1, 3, 9] {
        let dir = tempdir().unwrap();
        let db_path = dir.path().join(format!("test_level_{}.db", level));
        let config = Config {
            enable_compression: true,
            compression_level: level,
            ..Default::default()
        };

        let storage = StorageEngine::new(db_path.to_str().unwrap(), &config).unwrap();

        let key = "level_test";
        let value = b"Testing compression level ".repeat(100);

        storage.set(key, &value).unwrap();
        let retrieved = storage.get(key).unwrap();

        assert!(retrieved.is_some());
        assert_eq!(
            retrieved.unwrap(),
            value,
            "Failed at compression level {}",
            level
        );
    }
}

#[test]
fn test_binary_data_compression() {
    let dir = tempdir().unwrap();
    let db_path = dir.path().join("test_binary.db");
    let config = create_compression_config();

    let storage = StorageEngine::new(db_path.to_str().unwrap(), &config).unwrap();

    // バイナリデータ（圧縮できない可能性あり）
    let key = "binary_key";
    let value: Vec<u8> = (0..=255).cycle().take(500).collect();

    storage.set(key, &value).unwrap();
    let retrieved = storage.get(key).unwrap();

    assert!(retrieved.is_some());
    assert_eq!(retrieved.unwrap(), value);
}
