# DictSQLite v4.2 - JSONモードとテーブルサポートの実装可能性調査

**Issue対応**: DictSQLite v4.2について - JSONモードとテーブルの実装検討

## 📋 目次

1. [概要](#概要)
2. [JSONモードの実装可能性](#jsonモードの実装可能性)
3. [テーブルサポートの実装可能性](#テーブルサポートの実装可能性)
4. [パフォーマンス影響分析](#パフォーマンス影響分析)
5. [実装推奨事項](#実装推奨事項)
6. [代替アプローチ](#代替アプローチ)

---

## 🎯 概要

DictSQLite v4.2は、Rust実装により大幅なパフォーマンス向上（5〜300倍）を実現していますが、以下の機能は現在サポートされていません：

- **JSONモード**: v1.8.8では`storage_mode='json'`でサポート
- **複数テーブル**: v1.8.8では`table_name`パラメータでサポート

本ドキュメントでは、これらの機能をv4.2に実装する場合の：
- **技術的実装可能性**
- **パフォーマンス影響**
- **推奨実装方法**
- **代替アプローチ**

について詳細に検討します。

---

## 📄 JSONモードの実装可能性

### 現状分析

#### v1.8.8のJSONモード実装

v1.8.8では、データの保存形式を2つのモードで選択できます：

```python
# Pickleモード（デフォルト）
db = DictSQLite('data.db', storage_mode='pickle')
db['config'] = {'theme': 'dark', 'lang': 'ja'}  # pickle化されて保存

# JSONモード
db_json = DictSQLite('data.db', storage_mode='json')
db_json['config'] = {'theme': 'dark', 'lang': 'ja'}  # JSON文字列として保存
```

**JSONモードの特徴（v1.8.8）:**

1. **エンコーディング**
   - `json.dumps()`でJSON文字列に変換
   - カスタムエンコーダで`set`型をサポート
   - UTF-8テキストとして保存（暗号化時はバイナリ）

2. **デコーディング**
   - `json.loads()`でPythonオブジェクトに復元
   - カスタムデコーダで`set`型を復元
   - 互換性のため、JSONデコード失敗時はpickleを試行

3. **サポートされる型**
   - JSON標準型: `dict`, `list`, `str`, `int`, `float`, `bool`, `None`
   - 拡張型: `set`（カスタムエンコーダ経由）
   - 制限: 任意のPythonオブジェクトは不可（Pickleモードが必要）

#### v4.2の現在の実装

v4.2では、すべてのデータを**bytes型**として扱います：

```rust
// Rust実装（src/lib.rs）
pub struct DictSQLiteV4 {
    hot_tier: Arc<DashMap<String, Vec<u8>>>,  // バイトデータとして保存
    // ...
}
```

**現在のデータフロー:**

```
Python → bytes → 暗号化（オプション） → Rustホットティア → SQLite
         ↓
    自動変換（文字列のみ）
```

### 実装方法

#### アプローチ1: ストレージモード列挙型の追加（推奨★★★★★）

**実装概要:**

```rust
// src/lib.rs に追加
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
pub enum StorageMode {
    /// Pickle形式（デフォルト、任意のPythonオブジェクト対応）
    Pickle,
    
    /// JSON形式（JSON互換型のみ、可読性重視）
    Json,
    
    /// Bytes形式（生バイナリデータ）
    Bytes,
}

impl FromStr for StorageMode {
    type Err = String;
    
    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s.to_lowercase().as_str() {
            "pickle" => Ok(StorageMode::Pickle),
            "json" => Ok(StorageMode::Json),
            "bytes" => Ok(StorageMode::Bytes),
            _ => Err(format!("Invalid storage_mode: {}", s)),
        }
    }
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Config {
    // 既存フィールド...
    
    /// ストレージモード（新規追加）
    pub storage_mode: StorageMode,
}
```

**Pythonインターフェース:**

```python
from dictsqlite_v4 import DictSQLiteV4

# JSONモードで初期化
db = DictSQLiteV4(
    'data.db',
    storage_mode='json'  # 新規パラメータ
)

# JSON互換データの保存
db['config'] = {'theme': 'dark', 'lang': 'ja'}
db['users'] = ['alice', 'bob', 'charlie']
db['count'] = 42

# 読み込み（自動的にJSON→Pythonオブジェクト変換）
config = db['config']  # {'theme': 'dark', 'lang': 'ja'}
```

**実装の詳細:**

1. **エンコーディング処理（`__setitem__`）**

```rust
fn __setitem__(&self, key: String, value: PyObject, py: Python) -> PyResult<()> {
    let data: Vec<u8> = match self.config.storage_mode {
        StorageMode::Json => {
            // PythonオブジェクトをJSON文字列に変換
            let json_str: String = py.eval(
                "import json; json.dumps(obj, ensure_ascii=False, separators=(',', ':'))",
                Some([("obj", value)].into_py_dict(py)),
                None
            )?.extract()?;
            
            json_str.as_bytes().to_vec()
        },
        StorageMode::Pickle => {
            // 既存のPickle処理
            // ...
        },
        StorageMode::Bytes => {
            // 既存のBytes処理
            // ...
        }
    };
    
    // 暗号化とキャッシュ処理（既存コードと同じ）
    // ...
}
```

2. **デコーディング処理（`__getitem__`）**

```rust
fn __getitem__(&self, key: String, py: Python) -> PyResult<PyObject> {
    // データ取得（既存コードと同じ）
    let data: Vec<u8> = /* ... */;
    
    // ストレージモードに応じてデコード
    match self.config.storage_mode {
        StorageMode::Json => {
            let json_str = std::str::from_utf8(&data)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    format!("Invalid UTF-8 in JSON data: {}", e)
                ))?;
            
            // JSON文字列をPythonオブジェクトに変換
            py.eval(
                "import json; json.loads(s)",
                Some([("s", json_str)].into_py_dict(py)),
                None
            )?.extract()
        },
        StorageMode::Pickle => {
            // 既存のPickle処理
            // ...
        },
        StorageMode::Bytes => {
            // 既存のBytes処理
            // ...
        }
    }
}
```

3. **互換性のための自動判定**

v1.8.8との互換性のため、読み込み時にデータ形式を自動判定：

```rust
fn __getitem__(&self, key: String, py: Python) -> PyResult<PyObject> {
    let data: Vec<u8> = /* データ取得 */;
    
    // 現在の設定がJSONモードの場合でも、pickleデータを読み込めるようにする
    if self.config.storage_mode == StorageMode::Json {
        // まずJSONとして試行
        if let Ok(json_str) = std::str::from_utf8(&data) {
            if let Ok(result) = py.eval(
                "import json; json.loads(s)",
                Some([("s", json_str)].into_py_dict(py)),
                None
            ) {
                return Ok(result.to_object(py));
            }
        }
        
        // JSON失敗時はPickleとして試行（後方互換性）
        // ...
    }
    
    // Pickleモードの場合...
}
```

#### アプローチ2: メタデータフラグ方式

各キーごとにストレージモードを記録する方式：

```rust
// SQLiteテーブルにmode列を追加
CREATE TABLE IF NOT EXISTS kv_store (
    key TEXT PRIMARY KEY,
    value BLOB NOT NULL,
    mode TEXT DEFAULT 'pickle'  -- 'pickle', 'json', 'bytes'
);
```

**メリット:**
- キーごとに異なるストレージモードを使用可能
- 柔軟性が高い

**デメリット:**
- 複雑性が増加
- パフォーマンスオーバーヘッド（メタデータ読み込み）
- v4.2の設計思想（シンプルさ）に反する

### パフォーマンス影響（JSONモード）

#### 測定予測

**書き込み性能:**

| モード | 予測スループット | オーバーヘッド | 備考 |
|--------|-----------------|---------------|------|
| Bytes（現在） | 100% | - | ベースライン |
| Pickle | 95-98% | 2-5% | pickle.dumps()のオーバーヘッド |
| JSON | 85-90% | 10-15% | json.dumps() + UTF-8エンコード |

**読み込み性能:**

| モード | 予測スループット | オーバーヘッド | 備考 |
|--------|-----------------|---------------|------|
| Bytes（現在） | 100% | - | ベースライン |
| Pickle | 95-98% | 2-5% | pickle.loads()のオーバーヘッド |
| JSON | 80-85% | 15-20% | json.loads() + UTF-8デコード |

**メモリ使用量:**

| モード | 予測メモリ使用量 | 備考 |
|--------|-----------------|------|
| Bytes | 100% | ベースライン |
| Pickle | 80-120% | データ型による |
| JSON | 90-110% | テキスト表現のため若干増加 |

#### パフォーマンス低下の理由

1. **シリアライゼーションコスト**
   - JSON: テキスト形式への変換オーバーヘッド
   - Pickle: バイナリプロトコルだが、型情報も保存

2. **Python-Rust境界のコスト**
   - JSONモード: PyO3経由で`json`モジュールを呼び出し
   - 追加の関数呼び出しとオブジェクト変換

3. **UTF-8エンコーディング**
   - JSON: 必ずUTF-8文字列として処理
   - Bytes: そのままバイナリとして処理

#### 最適化戦略

**1. RustネイティブなJSON処理**

```rust
// serde_jsonを使用（既にCargo.tomlに含まれている）
use serde_json;

fn __setitem__(&self, key: String, value: PyObject, py: Python) -> PyResult<()> {
    let data: Vec<u8> = match self.config.storage_mode {
        StorageMode::Json => {
            // PyObjectをRustのserde_json::Valueに変換
            let json_value = pythonobj_to_serde_value(value, py)?;
            
            // serde_jsonで高速シリアライズ
            serde_json::to_vec(&json_value)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?
        },
        // ...
    };
    // ...
}
```

この最適化により、**オーバーヘッドを5-10%程度に削減可能**です。

**2. JSON専用の高速パス**

```rust
impl DictSQLiteV4 {
    // JSON専用の最適化された実装
    fn set_json(&self, key: String, json_str: String) -> PyResult<()> {
        // JSON文字列を直接保存（パース不要）
        let data = json_str.as_bytes().to_vec();
        // 既存のキャッシュ＋永続化ロジック
        // ...
    }
    
    fn get_json(&self, key: String) -> PyResult<String> {
        // バイトデータを直接UTF-8文字列として返す
        let data: Vec<u8> = /* 取得 */;
        String::from_utf8(data)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))
    }
}
```

**使用例:**

```python
import json

db = DictSQLiteV4('data.db', storage_mode='json')

# 高速パスを使用
config = {'theme': 'dark', 'lang': 'ja'}
db.set_json('config', json.dumps(config))  # Python側でJSON化

# 読み込み
config_str = db.get_json('config')
config = json.loads(config_str)  # Python側でパース
```

この方法では、**オーバーヘッドを1-2%程度まで削減可能**です。

**3. JSONB方式（バイナリJSON）- 最高性能 ★★★★★**

PostgreSQLのJSONBのように、JSONをバイナリ形式で保存する方式：

**概要:**

JSONBは、JSON文字列をパースして効率的なバイナリ表現に変換する形式です：

- **利点**: 
  - テキストJSONより高速（パース不要、直接アクセス可能）
  - メモリ効率が良い（圧縮されたバイナリ形式）
  - インデックス作成が可能（将来の拡張）
  
- **PostgreSQL JSONB特徴**:
  - キーの重複を自動的に削除
  - キーの順序を保持しない（高速化のため）
  - 数値は効率的にエンコード
  - 文字列は長さプレフィックス付き

**Rust実装例（MessagePackまたはBincodeを使用）:**

```rust
// Option A: MessagePack使用（標準的なJSONB風フォーマット）
use rmp_serde;  // MessagePack for Rust

fn __setitem__(&self, key: String, value: PyObject, py: Python) -> PyResult<()> {
    let data: Vec<u8> = match self.config.storage_mode {
        StorageMode::JsonB => {
            // PyObjectをRustのserde_json::Valueに変換
            let json_value = pythonobj_to_serde_value(value, py)?;
            
            // MessagePackでバイナリシリアライズ（JSONB風）
            rmp_serde::to_vec(&json_value)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?
        },
        // ...
    };
    // ...
}

fn __getitem__(&self, key: String, py: Python) -> PyResult<PyObject> {
    let data: Vec<u8> = /* 取得 */;
    
    match self.config.storage_mode {
        StorageMode::JsonB => {
            // MessagePackからデシリアライズ
            let json_value: serde_json::Value = rmp_serde::from_slice(&data)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;
            
            // serde_json::ValueをPyObjectに変換
            serde_value_to_pythonobj(json_value, py)
        },
        // ...
    }
}
```

**パフォーマンス比較:**

| 形式 | 書き込み速度 | 読み込み速度 | サイズ | 互換性 | 可読性 |
|------|------------|------------|--------|--------|--------|
| JSON (text) | 85-90% | 80-85% | 100% | ★★★★★ | ★★★★★ |
| JSONB (MessagePack) | **95-98%** | **95-98%** | 70-80% | ★★★★☆ | ☆☆☆☆☆ |
| Pickle | 95-98% | 95-98% | 80-120% | ★★★☆☆ | ☆☆☆☆☆ |

**推奨実装: MessagePack（rmp-serde）**

```toml
# Cargo.toml に追加
[dependencies]
rmp-serde = "1.1"  # MessagePack implementation
```

**メリット:**

1. **高速性**: テキストJSONより5-15%高速
2. **メモリ効率**: 20-30%サイズ削減
3. **標準形式**: MessagePackは業界標準（多言語対応）
4. **JSON互換**: JSON構造をそのまま保持
5. **ほぼPickle並みの性能**: Pickleとほぼ同等の速度

**デメリット:**

1. **バイナリ形式**: 直接読めない（ツールが必要）
2. **依存関係**: 追加ライブラリが必要

**推奨実装戦略:**

```rust
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
pub enum StorageMode {
    /// Pickle形式（デフォルト、任意のPythonオブジェクト対応）
    Pickle,
    
    /// JSON形式（可読性重視、標準的なJSON文字列）
    Json,
    
    /// JSONB形式（性能重視、MessagePackバイナリ） ★推奨★
    JsonB,
    
    /// Bytes形式（生バイナリデータ）
    Bytes,
}
```

**使用例:**

```python
from dictsqlite_v4 import DictSQLiteV4

# JSONBモード（推奨：高速 + JSON互換）
db = DictSQLiteV4('data.db', storage_mode='jsonb')
db['config'] = {'theme': 'dark', 'lang': 'ja', 'version': 1}
db['users'] = ['alice', 'bob', 'charlie']

# 自動的にMessagePack形式で保存・復元
config = db['config']  # {'theme': 'dark', 'lang': 'ja', 'version': 1}

# JSONモード（可読性重視）
db_json = DictSQLiteV4('data.db', storage_mode='json')
# テキスト形式で保存されるため、SQLiteブラウザで直接確認可能
```

**パフォーマンス予測（JSONB使用時）:**

| 操作 | v1.8.8 | v4.2 + JSONB | 改善倍率 |
|-----|--------|-------------|---------|
| 単発書込 | ~150,000 ops/s | **1,440,000 ops/s** | **9.6倍** |
| バルク書込 | ~1,500,000 ops/s | **21,800,000 ops/s** | **14.5倍** |
| 単発読込 | ~200,000 ops/s | **2,060,000 ops/s** | **10.3倍** |

**結論:**

- **JSONBモード**: テキストJSONより5-15%高速、サイズも20-30%削減
- **推奨**: MessagePack（rmp-serde）を使用したJSONB実装
- **v1.8.8比**: 依然として**9-14倍高速**を維持
- **オーバーヘッド**: わずか2-5%（Pickle並み）

この方式により、**JSON互換性を保ちつつPickle並みの性能**を実現できます。

---

## 📊 テーブルサポートの実装可能性

### 現状分析

#### v1.8.8のテーブルサポート

```python
db = DictSQLite('app.db', table_name='users')
db['user1'] = {'name': 'Alice', 'age': 30}

# または
users = db.table('users')
users['user1'] = {'name': 'Alice', 'age': 30}
```

**v1.8.8の実装:**

- 単一SQLiteファイル内に複数のテーブルを作成
- 各テーブルは独立したネームスペース
- テーブル名はSQL識別子としてエスケープ処理

#### v4.2の制約

v4.2は**単一テーブル専用**で設計されています：

```rust
// src/storage.rs
impl StorageEngine {
    pub fn new(db_path: &str, config: &Config) -> Result<Self> {
        // ...
        conn.execute(
            "CREATE TABLE IF NOT EXISTS kv_store (
                key TEXT PRIMARY KEY,
                value BLOB NOT NULL
            )",
            [],
        )?;
        // 単一テーブル "kv_store" のみ
    }
}
```

**制約の理由:**

1. **パフォーマンス最適化**: 単一テーブルに特化したクエリとインデックス
2. **シンプルさ**: コードの複雑性を最小化
3. **LRUキャッシュ**: テーブル境界を考慮しない統一キャッシュ

### 実装方法

#### アプローチ1: テーブル名プレフィックス方式（推奨★★★★☆）

**概要:**

テーブル名をキーのプレフィックスとして扱う方式：

```python
# 内部的な変換
table='users', key='user1'  →  実際のキー: 'users:user1'
table='posts', key='post1'  →  実際のキー: 'posts:post1'
```

**実装:**

```rust
#[pyclass]
pub struct DictSQLiteV4 {
    // 既存フィールド...
    
    /// デフォルトテーブル名（新規追加）
    default_table: String,
}

#[pymethods]
impl DictSQLiteV4 {
    #[new]
    #[pyo3(signature = (db_path, table_name="default", ...))]
    fn new(
        db_path: String,
        table_name: &str,
        // 他のパラメータ...
    ) -> PyResult<Self> {
        // ...
        Ok(DictSQLiteV4 {
            default_table: table_name.to_string(),
            // ...
        })
    }
    
    fn __setitem__(&self, key: String, value: PyObject, py: Python) -> PyResult<()> {
        // キーにテーブルプレフィックスを追加
        let full_key = format!("{}:{}", self.default_table, key);
        
        // 既存の処理を full_key で実行
        // ...
    }
    
    // テーブルプロキシの作成
    fn table(&self, table_name: String) -> PyResult<TableProxy> {
        Ok(TableProxy {
            db: self.clone(),  // Arc参照なので効率的
            table_name,
        })
    }
}

#[pyclass]
pub struct TableProxy {
    db: Arc<DictSQLiteV4>,
    table_name: String,
}

#[pymethods]
impl TableProxy {
    fn __setitem__(&self, key: String, value: PyObject, py: Python) -> PyResult<()> {
        let full_key = format!("{}:{}", self.table_name, key);
        self.db.__setitem__(full_key, value, py)
    }
    
    fn __getitem__(&self, key: String, py: Python) -> PyResult<PyObject> {
        let full_key = format!("{}:{}", self.table_name, key);
        self.db.__getitem__(full_key, py)
    }
    
    // 他のメソッドも同様に実装...
}
```

**使用例:**

```python
from dictsqlite_v4 import DictSQLiteV4

# 方法1: 初期化時にテーブル指定
users_db = DictSQLiteV4('app.db', table_name='users')
users_db['user1'] = {'name': 'Alice', 'age': 30}

# 方法2: tableメソッドでプロキシ取得
db = DictSQLiteV4('app.db')
users = db.table('users')
users['user1'] = {'name': 'Alice', 'age': 30}

posts = db.table('posts')
posts['post1'] = {'title': 'Hello', 'content': '...'}
```

**メリット:**

- ✅ 実装が比較的簡単
- ✅ 既存のストレージエンジンを変更不要
- ✅ パフォーマンスへの影響が最小限（文字列結合のみ）
- ✅ LRUキャッシュがそのまま使える

**デメリット:**

- ⚠️ テーブル境界を越えたキャッシュ（メモリ効率はやや低下）
- ⚠️ テーブル削除が困難（プレフィックス一致の全キー削除が必要）
- ⚠️ テーブル一覧の取得が非効率（全キーをスキャン必要）

#### アプローチ2: 物理的な複数テーブル方式

**概要:**

SQLiteに実際に複数のテーブルを作成する方式：

```sql
CREATE TABLE IF NOT EXISTS tbl_users (
    key TEXT PRIMARY KEY,
    value BLOB NOT NULL
);

CREATE TABLE IF NOT EXISTS tbl_posts (
    key TEXT PRIMARY KEY,
    value BLOB NOT NULL
);
```

**実装の概要:**

```rust
pub struct StorageEngine {
    conn: rusqlite::Connection,
    table_name: String,  // 動的テーブル名
}

impl StorageEngine {
    pub fn new(db_path: &str, table_name: &str, config: &Config) -> Result<Self> {
        // テーブル名の検証とエスケープ
        let safe_table_name = Self::validate_table_name(table_name)?;
        
        // 動的にテーブル作成
        conn.execute(
            &format!(
                "CREATE TABLE IF NOT EXISTS {} (
                    key TEXT PRIMARY KEY,
                    value BLOB NOT NULL
                )",
                safe_table_name
            ),
            [],
        )?;
        
        Ok(StorageEngine {
            conn,
            table_name: safe_table_name,
        })
    }
    
    fn validate_table_name(name: &str) -> Result<String, String> {
        // SQLインジェクション対策
        if !name.chars().all(|c| c.is_alphanumeric() || c == '_') {
            return Err("Invalid table name".to_string());
        }
        Ok(format!("tbl_{}", name))
    }
}
```

**メリット:**

- ✅ テーブルごとに完全に独立したネームスペース
- ✅ テーブル削除が簡単（`DROP TABLE`）
- ✅ テーブル一覧の取得が容易（`sqlite_master`クエリ）
- ✅ テーブルごとのキャッシュ管理が可能

**デメリット:**

- ❌ 実装の複雑性が大幅に増加
- ❌ StorageEngineのインスタンスがテーブルごとに必要
- ❌ マルチテーブルアクセス時のリソース消費増加
- ❌ LRUキャッシュの管理が複雑化

#### アプローチ3: マルチデータベースファイル方式

**概要:**

各テーブルを別のSQLiteファイルとして扱う：

```python
users = DictSQLiteV4('app_users.db')
posts = DictSQLiteV4('app_posts.db')
```

**メリット:**

- ✅ 実装変更不要（既存のv4.2をそのまま使用）
- ✅ 完全に独立したリソース管理
- ✅ ファイルレベルでのバックアップ・削除が容易

**デメリット:**

- ❌ ファイル数が増加（管理が煩雑）
- ❌ トランザクションがファイル境界を越えられない
- ❌ v1.8.8のAPI互換性がない

### パフォーマンス影響（テーブルサポート）

#### プレフィックス方式の影響

**書き込み:**

```
オーバーヘッド: 1-2%
理由: 文字列結合 "table:key" のみ
```

**読み込み:**

```
オーバーヘッド: 1-2%
理由: 同上
```

**メモリ:**

```
増加量: +10-20バイト/キー
理由: プレフィックス文字列の分
```

**総合評価:**

- ✅ パフォーマンスへの影響は無視できるレベル（1-2%）
- ✅ v4.2の高速性は維持される

#### 物理テーブル方式の影響

**ストレージエンジン:**

```
コネクション数: テーブル数に比例
メモリ使用量: +5-10MB/テーブル（概算）
```

**LRUキャッシュ:**

```
選択肢A: 統合キャッシュ（現在と同じ）
選択肢B: テーブルごとのキャッシュ
  → Bの場合、メモリ使用量が大幅増加
```

**総合評価:**

- ⚠️ リソース消費が増加
- ⚠️ 複雑性の増加によるバグリスク
- ⚠️ メンテナンスコストの増加

---

## 📊 パフォーマンス影響分析

### 総合的なパフォーマンス予測

#### ケース1: JSONモード + プレフィックス方式テーブル

**予測スループット（WriteThrough モード）:**

| 操作 | v4.2現在 | JSON+Table | 低下率 |
|-----|---------|-----------|--------|
| 単発書込 | 1,475,659 ops/s | 1,255,000 ops/s | 15% |
| バルク書込 | 22,387,293 ops/s | 19,000,000 ops/s | 15% |
| 単発読込 | 2,101,379 ops/s | 1,680,000 ops/s | 20% |

**予測スループット（Lazy モード）:**

| 操作 | v4.2現在 | JSON+Table | 低下率 |
|-----|---------|-----------|--------|
| 単発書込 | ~100M ops/s | ~85M ops/s | 15% |
| バルク書込 | ~100M ops/s | ~85M ops/s | 15% |

**結論:**

- ✅ 15-20%のオーバーヘッドは許容範囲
- ✅ 依然としてv1.8.8の**4-250倍高速**
- ✅ 実用上問題なし

#### ケース2: Pickleモード + プレフィックス方式テーブル

**予測スループット（WriteThrough モード）:**

| 操作 | v4.2現在 | Pickle+Table | 低下率 |
|-----|---------|-------------|--------|
| 単発書込 | 1,475,659 ops/s | 1,400,000 ops/s | 5% |
| バルク書込 | 22,387,293 ops/s | 21,200,000 ops/s | 5% |
| 単発読込 | 2,101,379 ops/s | 1,990,000 ops/s | 5% |

**結論:**

- ✅ 5%のオーバーヘッドは極めて小さい
- ✅ ほぼ現在と同等のパフォーマンス

#### ケース3: JSONBモード（MessagePack） + プレフィックス方式テーブル ★推奨★

**予測スループット（WriteThrough モード）:**

| 操作 | v4.2現在 | JSONB+Table | 低下率 |
|-----|---------|------------|--------|
| 単発書込 | 1,475,659 ops/s | 1,440,000 ops/s | 2.5% |
| バルク書込 | 22,387,293 ops/s | 21,800,000 ops/s | 2.5% |
| 単発読込 | 2,101,379 ops/s | 2,060,000 ops/s | 2% |

**予測スループット（Lazy モード）:**

| 操作 | v4.2現在 | JSONB+Table | 低下率 |
|-----|---------|------------|--------|
| 単発書込 | ~100M ops/s | ~97M ops/s | 3% |
| バルク書込 | ~100M ops/s | ~97M ops/s | 3% |

**結論:**

- ✅ 2-3%のオーバーヘッドは極めて小さい
- ✅ ほぼPickleモードと同等のパフォーマンス
- ✅ JSON互換性を保ちつつ高速性を実現
- ⭐ **最も推奨されるアプローチ**

#### 全モード比較表

**v1.8.8との比較（WriteThrough モード）:**

| モード | 単発書込 | v1.8.8比 | バルク書込 | v1.8.8比 | 単発読込 | v1.8.8比 |
|--------|---------|---------|-----------|---------|---------|---------|
| v4.2 現在 | 1,475,659 | **9.8倍** | 22,387,293 | **14.9倍** | 2,101,379 | **10.5倍** |
| Pickle+Table | 1,400,000 | **9.3倍** | 21,200,000 | **14.1倍** | 1,990,000 | **10.0倍** |
| **JSONB+Table** | **1,440,000** | **9.6倍** | **21,800,000** | **14.5倍** | **2,060,000** | **10.3倍** |
| JSON+Table | 1,255,000 | **8.4倍** | 19,000,000 | **12.7倍** | 1,680,000 | **8.4倍** |

**推奨:**

1. **最優先**: JSONB（MessagePack）+ テーブルサポート
   - JSON互換性 + Pickle並みの性能
   - オーバーヘッド: わずか2-3%
   
2. **可読性重視**: JSON（text）+ テーブルサポート
   - SQLiteブラウザで直接確認可能
   - オーバーヘッド: 15-20%（許容範囲内）

3. **最高性能**: Pickle + テーブルサポート
   - 現在と同等のパフォーマンス
   - 任意のPythonオブジェクト対応

### ベンチマーク計画

実装後、以下のベンチマークで検証：

```python
import time
from dictsqlite_v4 import DictSQLiteV4

# テスト1: JSONモード
db_json = DictSQLiteV4('bench.db', storage_mode='json', table_name='test')
data = {'x': 1, 'y': [1, 2, 3], 'z': 'hello'}

start = time.perf_counter()
for i in range(100_000):
    db_json[f'key_{i}'] = data
elapsed = time.perf_counter() - start
print(f"JSON write: {100_000 / elapsed:.0f} ops/s")

# テスト2: JSONBモード（推奨）
db_jsonb = DictSQLiteV4('bench_jsonb.db', storage_mode='jsonb', table_name='test')

start = time.perf_counter()
for i in range(100_000):
    db_jsonb[f'key_{i}'] = data
elapsed = time.perf_counter() - start
print(f"JSONB write: {100_000 / elapsed:.0f} ops/s")

# テスト3: Pickleモード
db_pickle = DictSQLiteV4('bench2.db', storage_mode='pickle', table_name='test')

start = time.perf_counter()
for i in range(100_000):
    db_pickle[f'key_{i}'] = data
elapsed = time.perf_counter() - start
print(f"Pickle write: {100_000 / elapsed:.0f} ops/s")

# テスト4: テーブル切り替え
users = db_jsonb.table('users')
posts = db_jsonb.table('posts')

start = time.perf_counter()
for i in range(50_000):
    users[f'user_{i}'] = {'name': f'User{i}'}
    posts[f'post_{i}'] = {'title': f'Post{i}'}
elapsed = time.perf_counter() - start
print(f"Multi-table write: {100_000 / elapsed:.0f} ops/s")
```

---

## 💡 実装推奨事項

### 推奨実装戦略

#### フェーズ1: JSONBモード（MessagePack）実装（優先度: 最高 ★★★★★）

**理由:**

1. **最適なバランス**: JSON互換性 + Pickle並みの性能
2. **低オーバーヘッド**: わずか2-5%の性能低下
3. **実装が容易**: `rmp-serde`を使用するだけ
4. **業界標準**: MessagePackは多言語対応の標準フォーマット
5. **サイズ削減**: 20-30%のストレージ削減

**実装計画:**

```
1. Cargo.tomlに rmp-serde 依存関係追加 (5分)
2. StorageMode列挙型に JsonB 追加 (30分)
3. MessagePack encode/decode処理の実装 (2時間)
4. 互換性レイヤーの追加（自動判定） (1時間)
5. テストケースの作成 (2時間)
6. ベンチマークの実施と調整 (2時間)

合計: 7.5時間
```

**実装コード例:**

```rust
// Cargo.toml に追加
[dependencies]
rmp-serde = "1.1"  // MessagePack for Rust

// src/lib.rs に追加

/// Storage mode for data serialization
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
pub enum StorageMode {
    Pickle,
    Json,
    JsonB,  // ★推奨: MessagePack (JSONB-like binary JSON)
    Bytes,
}

impl FromStr for StorageMode {
    type Err = String;
    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s.to_lowercase().as_str() {
            "pickle" => Ok(StorageMode::Pickle),
            "json" => Ok(StorageMode::Json),
            "jsonb" => Ok(StorageMode::JsonB),
            "bytes" => Ok(StorageMode::Bytes),
            _ => Err(format!("Invalid storage_mode: {}. Choose from ['pickle', 'json', 'jsonb', 'bytes']", s)),
        }
    }
}

impl Default for StorageMode {
    fn default() -> Self {
        StorageMode::Pickle  // 後方互換性
    }
}

// エンコード処理
fn __setitem__(&self, key: String, value: PyObject, py: Python) -> PyResult<()> {
    let data: Vec<u8> = match self.config.storage_mode {
        StorageMode::JsonB => {
            // PyObjectをserde_json::Valueに変換
            let json_value = pythonobj_to_serde_value(value, py)?;
            
            // MessagePackでバイナリシリアライズ
            rmp_serde::to_vec(&json_value)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    format!("MessagePack serialization error: {}", e)
                ))?
        },
        StorageMode::Json => {
            // テキストJSON（既存の実装）
            let json_value = pythonobj_to_serde_value(value, py)?;
            serde_json::to_vec(&json_value)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?
        },
        StorageMode::Pickle => {
            // 既存のPickle処理
            // ...
        },
        StorageMode::Bytes => {
            // 既存のBytes処理
            // ...
        }
    };
    
    // 暗号化とキャッシュ処理（既存コードと同じ）
    // ...
}

// デコード処理
fn __getitem__(&self, key: String, py: Python) -> PyResult<PyObject> {
    let data: Vec<u8> = /* データ取得 */;
    
    match self.config.storage_mode {
        StorageMode::JsonB => {
            // MessagePackからデシリアライズ
            let json_value: serde_json::Value = rmp_serde::from_slice(&data)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    format!("MessagePack deserialization error: {}", e)
                ))?;
            
            // serde_json::ValueをPyObjectに変換
            serde_value_to_pythonobj(json_value, py)
        },
        StorageMode::Json => {
            // テキストJSON（既存の実装）
            let json_value: serde_json::Value = serde_json::from_slice(&data)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;
            serde_value_to_pythonobj(json_value, py)
        },
        // Pickle, Bytes の既存処理...
    }
}
```

#### フェーズ1-B: テキストJSONモード実装（優先度: 中 ★★★☆☆）

JSONBと同時または直後に実装（可読性が必要な場合のため）。

**理由:**

1. **可読性**: SQLiteブラウザで直接確認可能
2. **デバッグ**: 開発時のデバッグが容易
3. **互換性**: 他ツールとの相互運用

**実装計画:**

```
1. JSON encode/decode処理の実装 (1時間)
   ※ JSONBと同じ変換関数を使用
2. テストケースの追加 (1時間)
3. ベンチマーク追加 (30分)

合計: 2.5時間
```
    Bytes,
}

impl Default for StorageMode {
    fn default() -> Self {
        StorageMode::Pickle  // 後方互換性
    }
}

impl FromStr for StorageMode {
    type Err = String;
    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s.to_lowercase().as_str() {
            "pickle" => Ok(StorageMode::Pickle),
            "json" => Ok(StorageMode::Json),
            "bytes" => Ok(StorageMode::Bytes),
            _ => Err(format!("Invalid storage_mode: {}. Choose from ['pickle', 'json', 'bytes']", s)),
        }
    }
}

// Configに追加
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Config {
    // 既存フィールド...
    pub storage_mode: StorageMode,
}

impl Default for Config {
    fn default() -> Self {
        Config {
            // 既存のデフォルト値...
            storage_mode: StorageMode::Pickle,
        }
    }
}

// DictSQLiteV4の__new__に追加
#[new]
#[pyo3(signature = (
    db_path,
    hot_capacity=1_000_000,
    enable_async=true,
    persist_mode="writethrough",
    storage_mode="pickle",  // 新規追加
    encryption_password=None,
    enable_safe_pickle=false,
    safe_pickle_allowed_modules=None,
    buffer_size=100
))]
fn new(
    db_path: String,
    hot_capacity: usize,
    enable_async: bool,
    persist_mode: &str,
    storage_mode: &str,  // 新規追加
    encryption_password: Option<String>,
    enable_safe_pickle: bool,
    safe_pickle_allowed_modules: Option<Vec<String>>,
    buffer_size: usize,
) -> PyResult<Self> {
    let storage_mode_parsed = StorageMode::from_str(storage_mode)
        .map_err(PyErr::new::<pyo3::exceptions::PyValueError, _>)?;
    
    let config = Config {
        storage_mode: storage_mode_parsed,
        // 他の設定...
    };
    
    // ...
}
```

#### フェーズ2: テーブルサポート（優先度: 中）

**理由:**

1. **プレフィックス方式なら実装が容易**
2. **パフォーマンス影響が最小限**（1-2%）
3. **v1.8.8との互換性向上**

**実装計画:**

```
1. TableProxyクラスの実装 (2時間)
2. プレフィックス処理の追加 (1時間)
3. table()メソッドの実装 (1時間)
4. テーブル一覧取得の実装 (1時間)
5. テストケースの作成 (2時間)
6. ベンチマークの実施 (1時間)

合計: 8時間
```

**実装コード例:**

```rust
// src/lib.rs に追加

#[pyclass]
pub struct TableProxy {
    db: Py<DictSQLiteV4>,
    table_name: String,
}

#[pymethods]
impl TableProxy {
    fn __setitem__(&self, key: String, value: PyObject, py: Python) -> PyResult<()> {
        let full_key = format!("{}:{}", self.table_name, key);
        let db = self.db.borrow(py);
        db.__setitem__(full_key, value, py)
    }
    
    fn __getitem__(&self, key: String, py: Python) -> PyResult<PyObject> {
        let full_key = format!("{}:{}", self.table_name, key);
        let db = self.db.borrow(py);
        db.__getitem__(full_key, py)
    }
    
    fn __delitem__(&self, key: String, py: Python) -> PyResult<()> {
        let full_key = format!("{}:{}", self.table_name, key);
        let db = self.db.borrow(py);
        db.__delitem__(full_key, py)
    }
    
    fn __contains__(&self, key: String, py: Python) -> PyResult<bool> {
        let full_key = format!("{}:{}", self.table_name, key);
        let db = self.db.borrow(py);
        db.__contains__(full_key, py)
    }
    
    fn keys(&self, py: Python) -> PyResult<Vec<String>> {
        let db = self.db.borrow(py);
        let all_keys = db.keys(py)?;
        let prefix = format!("{}:", self.table_name);
        
        Ok(all_keys.into_iter()
            .filter(|k| k.starts_with(&prefix))
            .map(|k| k[prefix.len()..].to_string())
            .collect())
    }
    
    // values(), items(), clear() なども同様に実装
}

// DictSQLiteV4に追加
#[pymethods]
impl DictSQLiteV4 {
    // 既存メソッド...
    
    /// テーブルプロキシを取得
    fn table(slf: PyRef<Self>, table_name: String) -> PyResult<TableProxy> {
        Ok(TableProxy {
            db: slf.into(),
            table_name,
        })
    }
    
    /// テーブル一覧を取得
    fn tables(&self, py: Python) -> PyResult<Vec<String>> {
        let all_keys = self.keys(py)?;
        let mut tables: std::collections::HashSet<String> = std::collections::HashSet::new();
        
        for key in all_keys {
            if let Some(pos) = key.find(':') {
                tables.insert(key[..pos].to_string());
            }
        }
        
        Ok(tables.into_iter().collect())
    }
}
```

### APIデザイン

#### v4.2 with JSON mode + Table support

```python
from dictsqlite_v4 import DictSQLiteV4

# 基本的な使用（デフォルトテーブル、Pickleモード）
db = DictSQLiteV4('app.db')
db['key1'] = {'complex': 'object'}

# JSONモード
db_json = DictSQLiteV4('data.db', storage_mode='json')
db_json['config'] = {'theme': 'dark', 'lang': 'ja'}

# テーブル指定（初期化時）
users_db = DictSQLiteV4('app.db', table_name='users', storage_mode='json')
users_db['user1'] = {'name': 'Alice', 'age': 30}

# テーブルプロキシ（動的）
db = DictSQLiteV4('app.db', storage_mode='json')
users = db.table('users')
users['user1'] = {'name': 'Alice', 'age': 30}

posts = db.table('posts')
posts['post1'] = {'title': 'Hello', 'content': 'World'}

# テーブル一覧
print(db.tables())  # ['users', 'posts']

# テーブル内のキー一覧
print(users.keys())  # ['user1']
```

#### v1.8.8からの移行例

**Before (v1.8.8):**

```python
from dictsqlite import DictSQLite

db = DictSQLite('app.db', table_name='users', storage_mode='json')
db['user1'] = {'name': 'Alice', 'age': 30}
```

**After (v4.2 with features):**

```python
from dictsqlite_v4 import DictSQLiteV4

# 完全互換
db = DictSQLiteV4('app.db', table_name='users', storage_mode='json')
db['user1'] = {'name': 'Alice', 'age': 30}

# または、tableメソッド使用
db = DictSQLiteV4('app.db', storage_mode='json')
users = db.table('users')
users['user1'] = {'name': 'Alice', 'age': 30}
```

---

## 🔄 代替アプローチ

### アプローチ1: Pythonラッパーレイヤー

v4.2のRust実装は変更せず、Pythonラッパーで機能を追加：

```python
# dictsqlite_v4_wrapper.py

from dictsqlite_v4 import DictSQLiteV4
import json
import pickle

class DictSQLiteV4WithJSON:
    def __init__(self, db_path, storage_mode='pickle', table_name='default', **kwargs):
        self._db = DictSQLiteV4(db_path, **kwargs)
        self._storage_mode = storage_mode
        self._table_name = table_name
    
    def __setitem__(self, key, value):
        full_key = f"{self._table_name}:{key}"
        
        if self._storage_mode == 'json':
            # JSON文字列に変換してからbytesに
            json_str = json.dumps(value, ensure_ascii=False, separators=(',', ':'))
            data = json_str.encode('utf-8')
        else:
            # Pickle
            data = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
        
        self._db[full_key] = data
    
    def __getitem__(self, key):
        full_key = f"{self._table_name}:{key}"
        data = self._db[full_key]
        
        if self._storage_mode == 'json':
            json_str = data.decode('utf-8')
            return json.loads(json_str)
        else:
            return pickle.loads(data)
    
    def table(self, table_name):
        new_wrapper = DictSQLiteV4WithJSON.__new__(DictSQLiteV4WithJSON)
        new_wrapper._db = self._db
        new_wrapper._storage_mode = self._storage_mode
        new_wrapper._table_name = table_name
        return new_wrapper
```

**メリット:**

- ✅ Rust実装の変更不要
- ✅ 迅速なプロトタイピング可能
- ✅ Pythonユーザーが実装・カスタマイズ可能

**デメリット:**

- ❌ パフォーマンスがやや低下（Python層の追加オーバーヘッド）
- ❌ 公式実装ではない（メンテナンスが別途必要）

### アプローチ2: v1.8.8の改良版を並行提供

v4.2とは別に、v1.8.8の改良版を提供：

```
- dictsqlite (v1.8.x系): Pythonネイティブ、全機能サポート
- dictsqlite-v4 (v4.x系): Rust実装、高速性重視
```

**使い分け:**

| 要件 | 推奨バージョン |
|-----|--------------|
| 最高速度が必要 | v4.2 |
| JSONモード必須 | v1.8.x |
| 複数テーブル必須 | v1.8.x |
| ピュアPython環境 | v1.8.x |
| 暗号化+高速性 | v4.2 |

**メリット:**

- ✅ それぞれの強みを活かせる
- ✅ ユーザーが用途に応じて選択可能

**デメリット:**

- ❌ メンテナンスコストが2倍
- ❌ ユーザーが混乱する可能性

### アプローチ3: プラグインアーキテクチャ

拡張可能なプラグイン方式：

```rust
// src/plugins/mod.rs

pub trait StoragePlugin: Send + Sync {
    fn encode(&self, value: PyObject, py: Python) -> PyResult<Vec<u8>>;
    fn decode(&self, data: &[u8], py: Python) -> PyResult<PyObject>;
}

pub struct JsonPlugin;
impl StoragePlugin for JsonPlugin {
    fn encode(&self, value: PyObject, py: Python) -> PyResult<Vec<u8>> {
        // JSON エンコード処理
    }
    
    fn decode(&self, data: &[u8], py: Python) -> PyResult<PyObject> {
        // JSON デコード処理
    }
}

// DictSQLiteV4に追加
pub struct DictSQLiteV4 {
    storage_plugin: Arc<dyn StoragePlugin>,
    // ...
}
```

**メリット:**

- ✅ 高い拡張性
- ✅ サードパーティプラグインのサポート可能

**デメリット:**

- ❌ 実装の複雑性が大幅に増加
- ❌ v4.2の設計思想（シンプルさ）に反する

---

## 📝 まとめ

### JSONモードの実装

**結論: 実装推奨 ★★★★★**

- **実装可能性**: ✅ 高い（8時間程度で実装可能）
- **パフォーマンス影響**: 15-20%のオーバーヘッド（許容範囲内）
- **ユーザーメリット**: 可読性、データ互換性の大幅向上
- **推奨実装方法**: StorageMode列挙型 + serde_json最適化

**予測パフォーマンス:**

```
JSON書き込み: 1,255,000 ops/s (v1.8.8の約8倍)
JSON読み込み: 1,680,000 ops/s (v1.8.8の約11倍)
```

### テーブルサポートの実装

**結論: 実装推奨 ★★★★☆**

- **実装可能性**: ✅ 高い（プレフィックス方式で8時間程度）
- **パフォーマンス影響**: 1-2%のオーバーヘッド（ほぼ無視可能）
- **ユーザーメリット**: v1.8.8との互換性向上、ネームスペース管理
- **推奨実装方法**: プレフィックス方式 + TableProxyクラス

**予測パフォーマンス:**

```
テーブル込み書き込み: 1,400,000 ops/s (v1.8.8の約9倍)
テーブル込み読み込み: 1,990,000 ops/s (v1.8.8の約13倍)
```

### 総合評価

両機能を実装した場合：

**パフォーマンス比較:**

| 操作 | v1.8.8 | v4.2現在 | v4.2 + JSON + Table | 改善倍率 |
|-----|--------|---------|-------------------|---------|
| 単発書込 | ~150,000 | 1,475,659 | 1,255,000 | **8.4倍** |
| バルク書込 | ~1,500,000 | 22,387,293 | 19,000,000 | **12.7倍** |
| 単発読込 | ~200,000 | 2,101,379 | 1,680,000 | **8.4倍** |

**結論:**

✅ **両機能の実装は実行可能かつ推奨される**

- パフォーマンス低下は許容範囲内（15-20%）
- 依然としてv1.8.8より**8-12倍高速**
- ユーザーエクスペリエンスの大幅向上
- v1.8.8からの移行が容易に

### 実装ロードマップ

```
Phase 1: JSONモード (Week 1)
  ├─ Day 1-2: StorageMode実装
  ├─ Day 3: エンコード/デコード処理
  ├─ Day 4: テストとベンチマーク
  └─ Day 5: ドキュメント更新

Phase 2: テーブルサポート (Week 2)
  ├─ Day 1-2: TableProxy実装
  ├─ Day 3: プレフィックス処理
  ├─ Day 4: テストとベンチマーク
  └─ Day 5: ドキュメント更新

Phase 3: 統合とリリース (Week 3)
  ├─ Day 1-2: 統合テスト
  ├─ Day 3: パフォーマンス最適化
  ├─ Day 4: 移行ガイド作成
  └─ Day 5: リリース準備
```

### 参考リンク

- [v4.2 Migration Guide](./MIGRATION_GUIDE_V4.2_JP.md)
- [v1.8.8 Release Notes](../../release-notes/v1.8.8.md)
- [v4.2 Performance Test Results](./PERFORMANCE_TEST_RESULTS.md)

---

**最終更新**: 2025年1月
**作成者**: DictSQLite開発チーム
**Issue対応**: JSONモードとテーブルサポートの実装可能性調査
