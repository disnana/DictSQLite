# Async Layer 実装計画

## 概要
`AsyncDictSQLite` は Python と Rust の境界を担当します。
ここでの最大の変更は、グローバルロックの排除とリソース管理の効率化です。

## 変更詳細

### 1. 構造体の変更 (`src/async_ops.rs`)

```rust
#[pyclass]
pub struct AsyncDictSQLite {
    // 既存
    cache: Arc<DashMap<String, Vec<u8>>>,
    config: Config,
    capacity: usize,
    write_buffer: Arc<Mutex<HashMap<String, Vec<u8>>>>,
    buffer_size: usize,

    // [変更] Mutex<Option<...>> -> Option<...>
    // StorageEngine自体がスレッドセーフになったため、ロック不要
    storage: Arc<Option<StorageEngine>>,

    // [変更] Arc<Runtime> -> &'static Runtime (またはGlobal参照)
    // インスタンスごとのRuntime保持を廃止
}
```

### 2. グローバル Tokio Runtime
`src/lib.rs` または `src/async_ops.rs` にグローバルランタイムを定義します。

```rust
use std::sync::OnceLock;
use tokio::runtime::Runtime;

static RUNTIME: OnceLock<Runtime> = OnceLock::new();

pub fn get_runtime() -> &'static Runtime {
    RUNTIME.get_or_init(|| {
        Runtime::new()
            .expect("Failed to create Tokio runtime")
    })
}
```

### 3. メソッドの実装変更

#### `aget`, `aset`, `adelete` 等
- `storage.lock().unwrap()` を削除。
- 直接 `storage.get(...)` 等を呼び出す。
- これにより、複数のPythonスレッド/タスクが同時にDB操作を行えるようになる。

#### バックグラウンドフラッシュ
- `tokio::spawn` を使用して、定期的に `storage.flush_access_counts()` を呼び出すタスクを起動することを検討（または `flush` 時に実行）。

## 難易度とリスク
- **難易度**: 中
- **リスク**: グローバルランタイムのシャットダウン挙動（Pythonプロセス終了時にどう振る舞うか）。通常はOSに任せて問題ないが、明示的なクリーンアップが必要な場合は `atexit` フックを検討。
