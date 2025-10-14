# DictSQLite v2 (v4.2) 技術仕様書

## 📋 概要

本文書は、DictSQLite v2 (バージョン4.2) の現在の実装仕様を詳細に記述した技術仕様書です。

**バージョン**: 2.0.4  
**実装言語**: Rust (PyO3バインディング経由でPythonに公開)  
**ライセンス**: MIT  
**対象Pythonバージョン**: Python 3.9+

---

## 🏗️ アーキテクチャ概要

DictSQLite v2は、Pythonの辞書インターフェースを持つ高性能な永続化ストレージシステムです。以下の3層アーキテクチャを採用しています：

### 3層ストレージアーキテクチャ

```
┌─────────────────────────────────────────────┐
│  Hot Tier (ホット層)                         │
│  - DashMap (ロックフリー並行HashMap)          │
│  - メモリ内のみ、最高速 (100M+ ops/sec)       │
│  - LRU追跡によるエビクション                   │
└─────────────────────────────────────────────┘
                    ↓ エビクション時
┌─────────────────────────────────────────────┐
│  Warm Tier (ウォーム層)                       │
│  - HashMap (メモリキャッシュ)                 │
│  - 頻繁にアクセスされるデータを保持            │
└─────────────────────────────────────────────┘
                    ↓ 永続化時
┌─────────────────────────────────────────────┐
│  Cold Tier (コールド層)                       │
│  - SQLite (ディスク永続化)                    │
│  - WALモード、最適化済みPRAGMA設定            │
└─────────────────────────────────────────────┘
```

### 主要コンポーネント

1. **DictSQLiteV4** - 同期版実装
2. **AsyncDictSQLite** - 非同期版実装
3. **TableProxy** - テーブル固有のアクセスプロキシ (同期版)
4. **AsyncTableProxy** - テーブル固有のアクセスプロキシ (非同期版)
5. **StorageEngine** - ストレージ層管理
6. **CryptoEngine** - AES-256-GCM暗号化
7. **SafePickleValidator** - Pickleセキュリティ検証

---

## 🔧 データ構造

### DictSQLiteV4 (同期版)

```rust
pub struct DictSQLiteV4 {
    /// ホット層: ロックフリー並行HashMap (メモリ内)
    hot_tier: Arc<DashMap<String, Vec<u8>>>,
    
    /// LRU追跡機構 (エビクション順序保護)
    access_tracker: Arc<Mutex<LruCache<String, ()>>>,
    
    /// ストレージエンジン (ウォーム層/コールド層管理)
    storage: Arc<Mutex<Option<StorageEngine>>>,
    
    /// 設定
    config: Config,
    
    /// 暗号化エンジン (オプション)
    crypto: Option<Arc<CryptoEngine>>,
    
    /// Safe Pickle検証器 (オプション)
    safe_pickle: Option<Arc<SafePickleValidator>>,
    
    /// 書き込みバッファ (v4.2最適化)
    write_buffer: Arc<Mutex<Vec<(String, Vec<u8>)>>>,
    
    /// バッファサイズ閾値
    buffer_size: usize,
}
```

### AsyncDictSQLite (非同期版)

```rust
pub struct AsyncDictSQLite {
    /// ロックフリー並行HashMap (コア数に応じたシャード数)
    cache: Arc<DashMap<String, Vec<u8>>>,
    
    /// ストレージエンジン (永続化用、オプション)
    storage: Arc<Mutex<Option<StorageEngine>>>,
    
    /// 設定
    config: Config,
    
    /// キャパシティ
    capacity: usize,
    
    /// 書き込みバッファ (v4.2最適化)
    write_buffer: Arc<Mutex<HashMap<String, Vec<u8>>>>,
    
    /// バッファサイズ閾値
    buffer_size: usize,
    
    /// Tokioランタイム (非同期処理用)
    runtime: Arc<Runtime>,
}
```

### Config (設定構造体)

```rust
pub struct Config {
    /// ホット層の最大容量 (エントリ数)
    pub hot_tier_capacity: usize,
    
    /// ウォーム層のサイズ (バイト数)
    pub warm_tier_size: usize,
    
    /// 非同期バックグラウンドフラッシュを有効化
    pub enable_async_flush: bool,
    
    /// フラッシュ間隔 (ミリ秒)
    pub flush_interval_ms: u64,
    
    /// 並行アクセス用シャード数
    pub num_shards: usize,
    
    /// 永続化モード
    pub persist_mode: PersistMode,
    
    /// 暗号化を有効化
    pub enable_encryption: bool,
    
    /// Safe Pickle検証を有効化
    pub enable_safe_pickle: bool,
    
    /// ストレージモード (シリアライゼーション方式)
    pub storage_mode: StorageMode,
    
    /// デフォルトテーブル名
    pub table_name: String,
}
```

#### デフォルト値

- `hot_tier_capacity`: 1,000,000
- `warm_tier_size`: 100MB (104,857,600 bytes)
- `enable_async_flush`: true
- `flush_interval_ms`: 1000
- `num_shards`: CPU コア数の次の2の累乗
- `persist_mode`: WriteThrough
- `enable_encryption`: false
- `enable_safe_pickle`: false
- `storage_mode`: Pickle
- `table_name`: "main"

---

## 📦 永続化モード (PersistMode)

データの永続化戦略を制御します。

### 1. Memory (メモリモード)

```rust
PersistMode::Memory
```

**特性**:
- 純粋なインメモリ動作
- ディスクへの書き込みなし
- 最高速: 100M+ ops/sec
- データ永続性: なし (プロセス終了で消失)

**用途**:
- 一時的なキャッシュ
- テスト環境
- 高速処理が必要で永続化不要な場合

### 2. Lazy (遅延永続化モード)

```rust
PersistMode::Lazy
```

**特性**:
- ホット層への書き込みは即座
- ディスクへの書き込みは`flush()`呼び出し時またはプロセス終了時
- 速度: 40-80M ops/sec
- データ永続性: 明示的なフラッシュ時のみ

**用途**:
- バッチ処理
- 定期的な永続化で十分な場合
- 書き込み性能優先の場合

### 3. WriteThrough (即時永続化モード)

```rust
PersistMode::WriteThrough
```

**特性**:
- 各書き込みを即座にディスクへ永続化
- v4.2の書き込みバッファリング最適化により43倍高速化
- 速度: 1-3M ops/sec (v4.2最適化後)
- データ永続性: 最高 (即座に保存)

**用途**:
- データ損失が許されないアプリケーション
- トランザクション的な動作が必要な場合
- デフォルトの推奨モード

---

## 🎨 ストレージモード (StorageMode)

データのシリアライゼーション形式を制御します。

### 1. Pickle (デフォルト)

```python
storage_mode="pickle"
```

**特性**:
- Pythonの標準pickleプロトコルを使用
- 任意のPythonオブジェクトをサポート
- クラス、関数、カスタムオブジェクトも保存可能
- バイナリ形式 (人間には読めない)

**対応型**: すべてのPythonオブジェクト

**用途**: 汎用的なPythonオブジェクト永続化

**セキュリティ**: Safe Pickle検証と併用可能

### 2. JSON (テキストJSON)

```python
storage_mode="json"
```

**特性**:
- 人間が読めるテキスト形式
- SQLiteブラウザで直接確認可能
- デバッグに便利
- JSON互換型のみサポート

**対応型**:
- `str`, `int`, `float`, `bool`, `None`
- `dict` (キーは文字列のみ)
- `list`

**用途**:
- データの可読性が重要な場合
- 他ツールとの相互運用
- デバッグ・開発時

### 3. JSONB (バイナリJSON / MessagePack)

```python
storage_mode="jsonb"
```

**特性**:
- MessagePack形式 (高速バイナリJSON)
- JSONより10-20%高速
- JSONより20-30%コンパクト
- JSON互換型のみサポート

**対応型**: JSONモードと同じ

**用途**:
- JSON互換データで高速性が必要な場合
- ストレージサイズの削減が重要な場合
- **推奨**: パフォーマンスとコンパクト性の両立

### 4. Bytes (生バイト列)

```python
storage_mode="bytes"
```

**特性**:
- シリアライゼーションなし
- 生のバイト列を直接保存
- 最も高速
- アプリケーション側でシリアライゼーション管理が必要

**対応型**: `bytes` のみ

**用途**:
- カスタムシリアライゼーションを実装する場合
- すでにシリアライズ済みのデータを保存する場合

---

## 🔐 セキュリティ機能

### 1. AES-256-GCM暗号化

**実装**: `CryptoEngine`

**アルゴリズム**:
- 暗号化: AES-256-GCM (認証付き暗号化)
- 鍵導出: Argon2 または PBKDF2
- ハッシュ: SHA-256

**使用方法**:

```python
from dictsqlite import DictSQLiteV4

db = DictSQLiteV4(
    "encrypted.db",
    encryption_password="your_secure_password"
)
```

**特性**:
- 全データが暗号化されて保存
- 認証付き暗号化により改ざん検出
- パスワードベースの鍵導出
- 各エントリに個別のnonceを使用

### 2. Safe Pickle検証

**実装**: `SafePickleValidator` + Python `safe_pickle`モジュール

**目的**: 信頼できないpickleデータからの攻撃防止

**検証項目**:
- 許可されたモジュールのみインポート可能
- 許可された組み込み関数のみ使用可能
- 危険なグローバル変数の拒否
- 関数・クラスのホワイトリスト

**使用方法**:

```python
from dictsqlite import DictSQLiteV4

db = DictSQLiteV4(
    "safe.db",
    storage_mode="pickle",
    enable_safe_pickle=True,
    safe_pickle_allowed_modules=["myapp", "trusted_lib"]
)
```

**デフォルト拒否リスト**:
- `os`, `subprocess`, `socket`, `sys`
- `eval`, `exec`, `compile`
- その他の危険な組み込み関数

---

## 📊 テーブルサポート

v4.2で追加された機能。1つのデータベースで複数の名前空間（テーブル）を管理できます。

### 実装方式

**プレフィックスベース**: キーに `"table_name:key"` 形式のプレフィックスを付与

**パフォーマンス影響**: 1-2% (無視できる程度)

### 使用方法

#### 方法1: テーブルプロキシを取得

```python
from dictsqlite import DictSQLiteV4

db = DictSQLiteV4("app.db", storage_mode="jsonb")

# テーブルプロキシを取得
users = db.table("users")
posts = db.table("posts")

# 各テーブルで独立して操作
users["alice"] = {"name": "Alice", "age": 30}
posts["post1"] = {"title": "Hello", "author": "alice"}

# 読み取り
print(users["alice"])  # => {"name": "Alice", "age": 30}
print(posts["post1"])  # => {"title": "Hello", "author": "alice"}
```

#### 方法2: デフォルトテーブル名を指定

```python
from dictsqlite import DictSQLiteV4

# 初期化時にテーブル名を指定
users_db = DictSQLiteV4("app.db", table_name="users", storage_mode="jsonb")

# すべての操作は自動的に"users"テーブルに対して行われる
users_db["user1"] = {"name": "Alice", "age": 30}
print(users_db["user1"])
```

### TableProxy API

**同期版**: `TableProxy`  
**非同期版**: `AsyncTableProxy`

**サポートされる操作**:

```python
# 辞書風アクセス
table[key] = value      # 設定
value = table[key]      # 取得
del table[key]          # 削除
key in table            # 存在確認
len(table)              # 要素数

# メソッド
table.keys()            # キー一覧
table.values()          # 値一覧
table.items()           # (key, value) タプル一覧
table.get(key, default) # デフォルト値付き取得
table.clear()           # 全削除
```

### テーブル一覧取得

```python
db = DictSQLiteV4("app.db")
tables = db.tables()    # => ["main", "users", "posts", ...]
```

---

## 🚀 v4.2 最適化機能

### 1. 書き込みバッファリング (WriteThrough最適化)

**効果**: 43倍高速化 (29.79K ops/sec → 1.30M ops/sec)

**実装**:
```rust
/// 書き込みバッファ (v4.2最適化)
write_buffer: Arc<Mutex<Vec<(String, Vec<u8>)>>>,

/// バッファサイズ閾値
buffer_size: usize,  // デフォルト: 100
```

**動作**:
1. 書き込み時、即座にホット層に反映
2. データを書き込みバッファに追加
3. バッファが閾値に達したら、一括でSQLiteに書き込み
4. 個別INSERT → バッチINSERTによるI/O削減

**設定方法**:

```python
db = DictSQLiteV4(
    "optimized.db",
    persist_mode="writethrough",
    buffer_size=100  # 100件ごとにバッチ書き込み
)
```

### 2. 非同期書き込みバッファリング

**効果**: 300倍高速化 (30秒 → 0.1秒 for 1000件)

**実装**:
```rust
/// 書き込みバッファ (v4.2最適化)
write_buffer: Arc<Mutex<HashMap<String, Vec<u8>>>>,
```

**動作**:
- Mutexロック回数: 1000回 → 10回 (100倍削減)
- SQLトランザクション数: 1000回 → 10回 (100倍削減)
- 非同期フラッシュによるGIL競合の削減

**設定方法**:

```python
from dictsqlite import AsyncDictSQLite

db = AsyncDictSQLite(
    "async_optimized.db",
    persist_mode="writethrough",
    buffer_size=100  # 100件ごとにバッチ書き込み
)
```

### 3. バッチ読み込み最適化

**効果**: キャッシュミス時に5-10倍高速化

**実装**:
- キャッシュミス時の一括SQL読み込み
- SQLクエリ数: N回 → 1回
- Rayon並列処理によるデシリアライゼーション

---

## 🐍 Python API仕様

### DictSQLiteV4 (同期版)

#### コンストラクタ

```python
DictSQLiteV4(
    db_path: str,
    hot_capacity: int = 1_000_000,
    enable_async: bool = True,
    persist_mode: str = "writethrough",
    storage_mode: str = "pickle",
    table_name: str = "main",
    encryption_password: Optional[str] = None,
    enable_safe_pickle: bool = False,
    safe_pickle_allowed_modules: Optional[List[str]] = None,
    buffer_size: int = 100
)
```

**パラメータ**:

- `db_path`: データベースファイルのパス
- `hot_capacity`: ホット層の最大容量 (エントリ数)
- `enable_async`: 非同期バックグラウンドフラッシュを有効化 (現在未使用)
- `persist_mode`: `"memory"`, `"lazy"`, `"writethrough"`
- `storage_mode`: `"pickle"`, `"json"`, `"jsonb"`, `"bytes"`
- `table_name`: デフォルトテーブル名
- `encryption_password`: 暗号化パスワード (None = 暗号化なし)
- `enable_safe_pickle`: Safe Pickle検証を有効化
- `safe_pickle_allowed_modules`: 許可するモジュールのリスト
- `buffer_size`: 書き込みバッファサイズ (WriteThrough最適化用)

#### メソッド

**基本操作**:

```python
# 取得
value = db.get(key: str, default: Optional[bytes] = None) -> bytes

# 設定
db.set(key: str, value: bytes) -> None

# 削除
db.delete(key: str) -> None

# 存在確認
exists = db.contains(key: str) -> bool
```

**辞書風操作**:

```python
# アクセス
db[key] = value         # __setitem__
value = db[key]         # __getitem__ (自動デシリアライズ)
del db[key]             # __delitem__
key in db               # __contains__
len(db)                 # __len__
```

**バルク操作**:

```python
# 一括挿入
db.bulk_insert(items: Dict[str, bytes]) -> None

# 辞書から更新
db.update(items: Dict[str, Any]) -> None

# すべてのキー
keys = db.keys() -> List[str]

# すべての値
values = db.values() -> List[Any]

# すべてのアイテム
items = db.items() -> List[Tuple[str, Any]]
```

**ユーティリティ**:

```python
# pop with default
value = db.pop(key: str, default: Optional[bytes] = None) -> bytes

# setdefault
value = db.setdefault(key: str, default: bytes) -> bytes

# 全削除
db.clear() -> None

# フラッシュ (Lazy/WriteThrough)
db.flush() -> None

# クローズ (自動フラッシュ)
db.close() -> None

# 統計情報
stats = db.stats() -> Dict[str, Any]
```

**テーブル操作**:

```python
# テーブルプロキシ取得
table = db.table(table_name: str) -> TableProxy

# テーブル一覧
tables = db.tables() -> List[str]
```

### AsyncDictSQLite (非同期版)

#### コンストラクタ

```python
AsyncDictSQLite(
    db_path: str,
    capacity: int = 1_000_000,
    persist_mode: str = "lazy",
    storage_mode: str = "pickle",
    table_name: str = "main",
    buffer_size: int = 100
)
```

**パラメータ**:

- `db_path`: データベースファイルのパス
- `capacity`: キャッシュ容量
- `persist_mode`: `"memory"`, `"lazy"`, `"writethrough"`
- `storage_mode`: `"pickle"`, `"json"`, `"jsonb"`, `"bytes"`
- `table_name`: デフォルトテーブル名
- `buffer_size`: 書き込みバッファサイズ

#### 非同期メソッド

**基本操作** (Python awaitable):

```python
# 非同期取得
value = await db.aget(key: str) -> Optional[Any]

# 非同期設定
await db.aset(key: str, value: Any) -> None

# 非同期削除
await db.adelete(key: str) -> None

# 非同期存在確認
exists = await db.acontains(key: str) -> bool

# 非同期バッチ取得
values = await db.abatch_get(keys: List[str]) -> Dict[str, Any]

# 非同期バッチ設定
await db.abatch_set(items: Dict[str, Any]) -> None

# 非同期フラッシュ
await db.aflush() -> None

# 非同期クローズ
await db.aclose() -> None
```

**同期メソッド** (非awaitable):

```python
# 同期取得 (GILリリース、キャッシュのみ)
value = db.get_async(key: str) -> Optional[bytes]

# 同期設定 (GILリリース)
db.set_async(key: str, value: bytes) -> None
```

**テーブル操作**:

```python
# テーブルプロキシ取得
table = db.table(table_name: str) -> AsyncTableProxy

# テーブル一覧
tables = db.tables() -> List[str]
```

---

## ⚡ パフォーマンス特性

### 速度比較 (操作/秒)

| モード | 読み取り | 書き込み | 備考 |
|--------|----------|----------|------|
| Memory | 100M+ | 100M+ | 純粋メモリ、最速 |
| Lazy | 80M+ | 40-80M | フラッシュ時のみディスクI/O |
| WriteThrough (v4.1) | 50M+ | 29.79K | 各書き込みでディスクI/O |
| WriteThrough (v4.2) | 50M+ | 1.30M | バッファリング最適化 (43倍高速化) |

### 非同期版パフォーマンス

| 操作 | v4.1 | v4.2 | 向上率 |
|------|------|------|--------|
| 1000件書き込み | 30秒 | 0.1秒 | **300倍** |
| 並行書き込み (5000件) | 15秒 | 0.05秒 | **300倍** |

### ストレージモード比較

| モード | 読み取り速度 | 書き込み速度 | サイズ | 可読性 |
|--------|--------------|--------------|--------|--------|
| Pickle | 最速 | 最速 | 中 | ✗ |
| JSONB | 高速 | 高速 | 小 (70-80%) | ✗ |
| JSON | 中速 | 中速 | 大 (100%) | ✓ |
| Bytes | 最速 | 最速 | 最小 | ✗ |

---

## 🗄️ SQLite最適化設定

StorageEngineは以下のPRAGMA設定でSQLiteを最適化しています：

```sql
PRAGMA journal_mode=WAL;           -- Write-Ahead Logging (並行性向上)
PRAGMA synchronous=NORMAL;          -- 同期レベル (パフォーマンス優先)
PRAGMA cache_size=-64000;           -- 64MBのキャッシュ
PRAGMA temp_store=MEMORY;           -- 一時テーブルをメモリに
PRAGMA mmap_size=30000000000;       -- 30GBのmmap (高速I/O)
PRAGMA page_size=4096;              -- 4KBページサイズ
PRAGMA auto_vacuum=INCREMENTAL;     -- インクリメンタルバキューム
```

### テーブルスキーマ

```sql
CREATE TABLE kv_store (
    key TEXT PRIMARY KEY,
    value BLOB NOT NULL,
    tier INTEGER DEFAULT 2,
    access_count INTEGER DEFAULT 0,
    last_access INTEGER DEFAULT 0
);

CREATE INDEX idx_access 
ON kv_store(access_count DESC, last_access DESC);
```

---

## 🔄 データフロー

### 読み取りフロー

```
1. db[key] 呼び出し
   ↓
2. ホット層 (DashMap) をチェック
   - 見つかった場合 → 即座に返却 (最速パス)
   ↓
3. ウォーム層 (HashMap) をチェック (Memoryモード以外)
   - 見つかった場合 → ホット層に昇格して返却
   ↓
4. コールド層 (SQLite) をチェック (Memoryモード以外)
   - 見つかった場合 → ホット層に昇格して返却
   ↓
5. KeyError (見つからない場合)
```

### 書き込みフロー (WriteThrough v4.2)

```
1. db[key] = value 呼び出し
   ↓
2. Safe Pickle検証 (有効な場合)
   ↓
3. 暗号化 (有効な場合)
   ↓
4. ホット層 (DashMap) に即座に書き込み
   ↓
5. LRU追跡を更新
   ↓
6. 書き込みバッファに追加
   ↓
7. バッファが閾値に達した場合
   → バッチでSQLiteに書き込み (フラッシュ)
   ↓
8. ホット層が容量超過した場合
   → LRUエビクション (最も古いエントリをウォーム層へ)
```

### 書き込みフロー (Lazy)

```
1. db[key] = value 呼び出し
   ↓
2. ホット層に即座に書き込み
   ↓
3. LRU追跡を更新
   ↓
4. ディスクへの書き込みは保留
   ↓
5. flush() または close() 呼び出し時
   → すべてのホット層データをSQLiteに書き込み
```

---

## 🛡️ 依存関係

### Rustクレート

```toml
[dependencies]
pyo3 = { version = "0.24.1", features = ["extension-module", "abi3-py39", "experimental-async"] }
dashmap = "5.5"              # ロックフリー並行HashMap
papaya = "0.1"               # 超低レイテンシ並行HashMap
lru = "0.12"                 # LRUキャッシュ
rusqlite = { version = "0.31", features = ["bundled", "backup", "blob", "hooks"] }
tokio = { version = "1.35", features = ["full"] }
async-trait = "0.1"
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
bincode = "1.3"
rmp-serde = "1.1"            # MessagePack (JSONB用)
crossbeam = "0.8"
parking_lot = "0.12"
rayon = "1.8"                # データ並列処理
ahash = "0.8"                # 高速ハッシュ
aes-gcm = "0.10"             # AES-256-GCM暗号化
argon2 = "0.5"               # パスワードハッシュ
pbkdf2 = { version = "0.12", features = ["simple"] }
sha2 = "0.10"                # SHA-256
base64 = "0.21"
rand = "0.8"
num_cpus = "1.16"
thiserror = "1.0"
anyhow = "1.0"
tracing = "0.1"
tracing-subscriber = "0.3"
```

### Pythonモジュール

- `dictsqlite.modules.safe_pickle` - Safe Pickle検証 (Pythonで実装)

---

## 📐 設計原則

### 1. ゼロコピー設計

可能な限りデータコピーを避け、Arc/参照を活用。

### 2. ロックフリー並行性

ホット層はDashMap (ロックフリー並行HashMap) を使用し、読み取りでのロック競合を排除。

### 3. GILリリース

非同期版では`py.allow_threads()`を使用してGILをリリースし、並行性を最大化。

### 4. 段階的フラッシュ

書き込みバッファリングにより、I/O操作をバッチ化して効率化。

### 5. LRUエビクション

メモリ制約下での自動的なデータ移動 (ホット層 → ウォーム層 → コールド層)。

---

## 🧪 テスト

### テストカバレッジ

- 基本CRUD操作
- 辞書風インターフェース
- 永続化モード (Memory, Lazy, WriteThrough)
- ストレージモード (Pickle, JSON, JSONB, Bytes)
- テーブルサポート
- 暗号化機能
- Safe Pickle検証
- 非同期操作
- エッジケース・エラーハンドリング
- パフォーマンステスト

### テスト総数

約290+テスト (v4.2時点)

---

## 🔧 ビルド設定

### リリースビルド最適化

```toml
[profile.release]
opt-level = 3              # 最大最適化
lto = "fat"                # Link-Time Optimization (完全)
codegen-units = 1          # 単一コード生成ユニット (最適化優先)
panic = "abort"            # パニック時はアボート (サイズ削減)
strip = true               # シンボル削除 (サイズ削減)
```

### Maturin設定

```toml
[package.metadata.maturin]
name = "dictsqlite"
long-description-file = "Pypi.md"
```

Python配布パッケージ名: `dictsqlite`

---

## 📝 使用例

### 基本的な使用

```python
from dictsqlite import DictSQLiteV4

# データベース作成
db = DictSQLiteV4("myapp.db")

# 書き込み (自動でpickle化)
db["user:alice"] = {"name": "Alice", "age": 30}
db["user:bob"] = {"name": "Bob", "age": 25}

# 読み取り (自動でデシリアライズ)
alice = db["user:alice"]
print(alice)  # => {"name": "Alice", "age": 30}

# 削除
del db["user:bob"]

# 存在確認
if "user:alice" in db:
    print("Alice exists!")

# クローズ (自動フラッシュ)
db.close()
```

### JSONBモードとテーブル

```python
from dictsqlite import DictSQLiteV4

db = DictSQLiteV4("app.db", storage_mode="jsonb")

# テーブル取得
users = db.table("users")
posts = db.table("posts")

# JSONBで保存 (高速・コンパクト)
users["alice"] = {"name": "Alice", "email": "alice@example.com"}
posts["post1"] = {"title": "Hello World", "author": "alice"}

# 読み取り
print(users["alice"])
print(posts["post1"])
```

### 暗号化

```python
from dictsqlite import DictSQLiteV4

# 暗号化DB作成
db = DictSQLiteV4(
    "secure.db",
    encryption_password="my_secure_password"
)

# データは自動的に暗号化されて保存
db["secret"] = {"api_key": "sk-1234567890"}

# 読み取り時に自動復号化
secret = db["secret"]
```

### 非同期版

```python
import asyncio
from dictsqlite import AsyncDictSQLite

async def main():
    db = AsyncDictSQLite("async.db", storage_mode="jsonb")
    
    # 非同期書き込み
    await db.aset("key1", {"data": "value1"})
    await db.aset("key2", {"data": "value2"})
    
    # 非同期バッチ書き込み
    await db.abatch_set({
        "key3": {"data": "value3"},
        "key4": {"data": "value4"},
    })
    
    # 非同期読み取り
    value = await db.aget("key1")
    print(value)
    
    # 非同期バッチ読み取り
    values = await db.abatch_get(["key1", "key2", "key3"])
    print(values)
    
    # クローズ
    await db.aclose()

asyncio.run(main())
```

---

## 🎯 推奨設定

### 用途別推奨設定

#### 1. 高速一時キャッシュ

```python
db = DictSQLiteV4(
    ":memory:",
    persist_mode="memory",
    hot_capacity=10_000_000
)
```

#### 2. 汎用永続化 (デフォルト)

```python
db = DictSQLiteV4(
    "app.db",
    persist_mode="writethrough",
    storage_mode="pickle",
    buffer_size=100
)
```

#### 3. JSONデータの高速永続化

```python
db = DictSQLiteV4(
    "data.db",
    persist_mode="writethrough",
    storage_mode="jsonb",
    buffer_size=100
)
```

#### 4. セキュアな永続化

```python
db = DictSQLiteV4(
    "secure.db",
    persist_mode="writethrough",
    storage_mode="pickle",
    encryption_password="your_password",
    enable_safe_pickle=True
)
```

#### 5. 高並行非同期処理

```python
db = AsyncDictSQLite(
    "async.db",
    persist_mode="writethrough",
    storage_mode="jsonb",
    buffer_size=1000,
    capacity=10_000_000
)
```

---

## 🚨 制限事項

### 1. テーブルプレフィックス

- テーブル名に `:` (コロン) を含めることはできません
- キー名に `:` を含む場合、テーブル分離が正しく動作しない可能性があります

### 2. ストレージモード制限

- **JSON/JSONB**: JSON互換型のみサポート (カスタムクラス不可)
- **Bytes**: `bytes`型のみサポート

### 3. Safe Pickle

- Pickleモードでのみ有効
- パフォーマンスへの影響あり (検証処理)

### 4. 暗号化

- 全データを暗号化するため、パフォーマンスへの影響あり
- パスワードを忘れるとデータ復元不可能

### 5. 並行アクセス

- 同一プロセス内での並行アクセスは安全
- 複数プロセスからの同時アクセスは、SQLiteのWALモードにより一定の並行性あり
- ただし、ホット層キャッシュはプロセス間で共有されない

---

## 📚 関連ドキュメント

- [README_V4.2_JP.md](./README_V4.2_JP.md) - v4.2の概要
- [DOCUMENTATION_INDEX_JP.md](./DOCUMENTATION_INDEX_JP.md) - ドキュメント索引
- [MIGRATION_GUIDE_V4.2_JP.md](./MIGRATION_GUIDE_V4.2_JP.md) - 移行ガイド
- [PERFORMANCE_OPTIMIZATION_GUIDE_JP.md](./PERFORMANCE_OPTIMIZATION_GUIDE_JP.md) - パフォーマンス最適化
- [DEVELOPER_GUIDE_JP.md](./DEVELOPER_GUIDE_JP.md) - 開発者ガイド
- [IMPLEMENTATION_COMPLETION_REPORT.md](./IMPLEMENTATION_COMPLETION_REPORT.md) - v4.2実装レポート
- [JSONB_TABLE_IMPLEMENTATION_SUMMARY_JP.md](./JSONB_TABLE_IMPLEMENTATION_SUMMARY_JP.md) - JSONB/テーブル実装サマリー

---

## 📄 ライセンス

MIT License

---

## ✍️ 著者

Disnana <support@disnana.com>

---

**文書バージョン**: 1.0  
**最終更新日**: 2025-10-14  
**対象バージョン**: DictSQLite v2.0.4 (v4.2)
