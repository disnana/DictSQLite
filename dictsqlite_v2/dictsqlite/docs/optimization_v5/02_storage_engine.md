# StorageEngine 実装計画

## 概要
`StorageEngine` は DictSQLite の心臓部であり、ここでの変更がパフォーマンスに最も大きな影響を与えます。
主な変更点は、内部可変性（Interior Mutability）の活用による `&mut self` の排除と、I/O操作のバッファリングです。

## 変更詳細

### 1. 構造体の変更 (`src/storage.rs`)

```rust
pub struct StorageEngine {
    // 既存
    cold_pool: Pool<SqliteConnectionManager>,
    config: Config,
    db_path: String,

    // [変更] Mutex -> DashMap (ロックフリー化)
    warm_cache: Arc<DashMap<String, Vec<u8>>>,

    // [新規] アクセスカウントバッファ (Write-on-Read解消)
    // Key: (table_name, key), Value: count
    access_count_buffer: Arc<DashMap<String, u64>>,

    // [新規] テーブル存在キャッシュ (SQL削減)
    known_tables: Arc<DashSet<String>>,
}
```

### 2. メソッドシグネチャの変更
全てのメソッドから `&mut self` を排除し、`&self` に変更します。これにより、上位レイヤーでの `Mutex` が不要になります。

- `fn get(&self, ...)`
- `fn set(&self, ...)`
- `fn delete(&self, ...)`
- `fn bulk_insert(&self, ...)`

### 3. ロジックの変更

#### `get` / `get_with_table`
- **Before**: `UPDATE kv_store SET access_count ...` を実行。
- **After**: `access_count_buffer` をインクリメントするのみ。DB書き込みは行わない。

#### `flush_access_counts` (新規メソッド)
- バッファリングされたアクセスカウントをまとめてDBに書き込む。
- トランザクションを使用して一括更新。
- 定期的、または `close` 時に呼び出される。

#### `ensure_table_exists`
- **Before**: 毎回 `CREATE TABLE IF NOT EXISTS` を発行。
- **After**: `known_tables` をチェック。存在しなければSQL発行し、キャッシュに追加。

### 4. PRAGMA設定 (`new` メソッド)
- `PRAGMA synchronous = NORMAL;` に変更。
- `PRAGMA journal_mode = WAL;` (維持)

### 5. Zstd圧縮 (オプション)
- `Config` に `enable_compression` フラグを追加。
- `set`: データを圧縮して保存。
- `get`: データを展開して返却。
- マジックヘッダー等で圧縮済みかどうかを判別することを推奨。

## 難易度とリスク
- **難易度**: 中
- **リスク**: アクセスカウントのロスト（許容済み）。圧縮導入時の互換性（新規DBまたはマイグレーションが必要）。
