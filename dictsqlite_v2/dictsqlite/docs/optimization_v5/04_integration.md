# Integration & Dependencies 実装計画

## 概要
ライブラリの依存関係と、データ変換ロジックの最適化を行います。

## 変更詳細

### 1. Cargo.toml の更新

```toml
[dependencies]
# [新規] JSON変換高速化
pythonize = "0.21"

# [新規] 圧縮
zstd = "0.13"

# [新規] Runtime管理
once_cell = "1.19" # または std::sync::OnceLock (Rust 1.70+)

# 既存の依存関係もバージョン確認・更新
```

### 2. JSON変換の置換 (`src/lib.rs`)

既存の `pyobject_to_json_value` および `json_value_to_pyobject` 関数を削除し、`pythonize` クレートを使用します。

```rust
use pythonize::{depythonize, pythonize};

// 使用例
let json_value: serde_json::Value = depythonize(obj.bind(py))?;
let py_obj = pythonize(py, &json_value)?;
```

これにより、コード量が大幅に削減され、変換速度も向上します。

### 3. Zstd圧縮の実装 (`src/storage.rs` への統合)

```rust
// 圧縮
let compressed = zstd::encode_all(original_data, 3)?; // レベル3推奨

// 展開
let decoded = zstd::decode_all(compressed_data)?;
```

## 難易度とリスク
- **難易度**: 低
- **リスク**: `pythonize` の挙動が既存の手動実装と完全に一致するか確認が必要（特にエッジケース）。
