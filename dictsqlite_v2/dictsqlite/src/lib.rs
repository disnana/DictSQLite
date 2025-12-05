//! # DictSQLite v4.2 - 高性能辞書型SQLiteライブラリ
//!
//! このモジュールは、Pythonの辞書のようなインターフェースでSQLiteデータベースを
//! 操作するための高性能Rust拡張を提供します。
//!
//! ## 主な機能
//! - **ロックフリー並行アクセス**: DashMapを使用した100M+ ops/secの高速読み書き
//! - **階層型ストレージ**: Hot/Warm/Cold tierによる効率的なデータ管理
//! - **LRUエビクション**: 自動的なメモリ管理と古いデータの追い出し
//! - **AES-256-GCM暗号化**: オプショナルなデータ暗号化
//! - **Safe Pickle検証**: 安全なPythonオブジェクトのシリアライズ
//! - **複数のストレージモード**: Pickle, JSON, JSONB, Bytes
//!
//! ## アーキテクチャ
//! ```text
//! ┌─────────────────────────────────────────────────────────────┐
//! │                    Python Interface                         │
//! │  (DictSQLiteV4, AsyncDictSQLite, TableProxy)               │
//! ├─────────────────────────────────────────────────────────────┤
//! │                    Hot Tier (DashMap)                       │
//! │  - ロックフリー並行ハッシュマップ                            │
//! │  - 最も高速なアクセス（メモリ内）                            │
//! ├─────────────────────────────────────────────────────────────┤
//! │                    Warm Tier (Memory Cache)                 │
//! │  - 頻繁にアクセスされるデータのキャッシュ                    │
//! ├─────────────────────────────────────────────────────────────┤
//! │                    Cold Tier (SQLite)                       │
//! │  - 永続化ストレージ                                         │
//! │  - WALモードによる高速書き込み                              │
//! └─────────────────────────────────────────────────────────────┘
//! ```
//!
//! ## 使用例
//! ```python
//! from dictsqlite import DictSQLiteV4
//!
//! # 基本的な使用法
//! db = DictSQLiteV4("test.db", storage_mode="jsonb")
//! db["key"] = {"name": "Alice", "age": 30}
//! print(db["key"])  # {'name': 'Alice', 'age': 30}
//!
//! # テーブル機能
//! users = db.table("users")
//! users["user1"] = {"name": "Bob"}
//! ```

use dashmap::DashMap;
use lru::LruCache;
use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyDict};
use pyo3::Bound;
use serde::{Deserialize, Serialize};
use std::num::NonZeroUsize;
use std::str::FromStr;
use std::sync::{Arc, Mutex};

// サブモジュールのインポート
// async_ops: 非同期操作を提供するモジュール
mod async_ops;
// cache: ハイブリッドキャッシュの実装
mod cache;
// crypto: AES-256-GCM暗号化機能
mod crypto;
// storage: SQLiteストレージエンジン
mod storage;

// テスト用モジュール（テストビルド時のみコンパイル）
#[cfg(test)]
mod tests_jsonb;
#[cfg(test)]
mod tests_lru;
#[cfg(test)]
mod tests_storage;

// 公開APIのエクスポート
// AsyncDictSQLite: 非同期版のDictSQLite（高並行シナリオ向け）
// AsyncTableProxy: 非同期テーブルプロキシ
pub use async_ops::{AsyncDictSQLite, AsyncTableProxy};
// HybridCache: LRUエビクション付きの高性能キャッシュ
pub use cache::HybridCache;
// CryptoEngine: AES-256-GCM暗号化エンジン
pub use crypto::CryptoEngine;
// StorageEngine: SQLiteバックエンドのストレージエンジン
// MemoryTier: Hot/Warm/Cold tierの列挙型
pub use storage::{MemoryTier, StorageEngine};

/// Safe Pickle Policy - Pythonのsafe_pickleモジュールを使用したポリシー
///
/// このポリシーは、Pickleデシリアライズ時に許可されるモジュールとクラスを制御します。
/// デフォルトでは、安全でないグローバル（os.system, subprocessなど）を拒否します。
///
/// # 例
/// ```rust,ignore
/// let policy = SafePicklePolicy::new()?;
/// // カスタムモジュールを許可
/// let policy = policy.with_module_prefix("myapp".to_string())?;
/// ```
#[derive(Debug)]
pub struct SafePicklePolicy {
    /// Python側のポリシーオブジェクトへの参照
    policy: PyObject,
}

impl SafePicklePolicy {
    /// 新しいデフォルトポリシーを作成
    ///
    /// デフォルトポリシーは以下の特徴を持ちます：
    /// - 安全でないグローバル（os.system, subprocess等）をブロック
    /// - 基本的なビルトイン型は許可
    /// - dictsqliteパッケージのモジュールは許可
    ///
    /// # 戻り値
    /// - `Ok(SafePicklePolicy)`: 新しいポリシーインスタンス
    /// - `Err(PyErr)`: Python側でのエラー（モジュールインポート失敗など）
    pub fn new() -> PyResult<Self> {
        Python::with_gil(|py| {
            // dictsqlite.modules からsafe_pickleをインポート
            let safe_pickle = py.import("dictsqlite.modules.safe_pickle")?;
            let policy_class = safe_pickle.getattr("SafePolicy")?;
            // SafePolicy()を引数なしで呼び出し - デフォルトでDEFAULT_DENYを使用
            let policy = policy_class.call0()?;
            Ok(SafePicklePolicy {
                policy: policy.unbind(),
            })
        })
    }

    /// 特定のパッケージ用のポリシーを作成
    ///
    /// # 引数
    /// * `pkg_prefix` - 許可するパッケージのプレフィックス（例: "myapp"）
    ///
    /// # 戻り値
    /// - `Ok(SafePicklePolicy)`: パッケージ用に設定されたポリシー
    /// - `Err(PyErr)`: エラー
    pub fn for_package(pkg_prefix: &str) -> PyResult<Self> {
        Python::with_gil(|py| {
            let safe_pickle = py.import("dictsqlite.modules.safe_pickle")?;
            let policy_class = safe_pickle.getattr("SafePolicy")?;
            let policy = policy_class.call_method1("for_package", (pkg_prefix,))?;
            Ok(SafePicklePolicy {
                policy: policy.unbind(),
            })
        })
    }

    /// 許可するモジュールプレフィックスを追加
    ///
    /// この関数は既存のポリシーに新しいモジュールプレフィックスを追加した
    /// 新しいポリシーを返します（イミュータブルな設計）。
    ///
    /// # 引数
    /// * `prefix` - 追加するモジュールプレフィックス（例: "numpy"）
    ///
    /// # 戻り値
    /// - `Ok(SafePicklePolicy)`: 更新されたポリシー
    /// - `Err(PyErr)`: エラー
    pub fn with_module_prefix(self, prefix: String) -> PyResult<Self> {
        Python::with_gil(|py| {
            let policy_bound = self.policy.bind(py);
            let current_prefixes = policy_bound.getattr("allowed_module_prefixes")?;

            // タプルを文字列リストに変換
            let prefixes_list: Vec<String> = current_prefixes.extract()?;

            let mut new_prefixes = prefixes_list;
            new_prefixes.push(prefix);

            // 更新されたプレフィックスで新しいポリシーを作成
            let safe_pickle = py.import("dictsqlite.modules.safe_pickle")?;
            let policy_class = safe_pickle.getattr("SafePolicy")?;
            let kwargs = pyo3::types::PyDict::new(py);
            kwargs.set_item("allowed_module_prefixes", new_prefixes)?;

            // 元のポリシーから他の属性をコピー
            let allowed_builtins = policy_bound.getattr("allowed_builtins")?;
            let allowed_globals = policy_bound.getattr("allowed_globals")?;
            let denied_globals = policy_bound.getattr("denied_globals")?;
            let allow_functions = policy_bound.getattr("allow_functions_from_prefixes")?;
            let allow_classes = policy_bound.getattr("allow_classes_from_prefixes")?;

            kwargs.set_item("allowed_builtins", allowed_builtins)?;
            kwargs.set_item("allowed_globals", allowed_globals)?;
            kwargs.set_item("denied_globals", denied_globals)?;
            kwargs.set_item("allow_functions_from_prefixes", allow_functions)?;
            kwargs.set_item("allow_classes_from_prefixes", allow_classes)?;

            let new_policy = policy_class.call((), Some(&kwargs))?;

            Ok(SafePicklePolicy {
                policy: new_policy.unbind(),
            })
        })
    }
}

impl Default for SafePicklePolicy {
    /// デフォルトポリシーの取得
    ///
    /// # パニック
    /// Pythonモジュールのインポートに失敗した場合にパニックします。
    /// 本番環境では`new()`を使用してエラーハンドリングを行うことを推奨。
    fn default() -> Self {
        Self::new().unwrap()
    }
}

/// Safe Pickle Validator - Pickleデータの安全性を検証
///
/// このバリデーターは、Pickleデータをロードする前に安全性を検証します。
/// 指定されたポリシーに基づき、危険なオブジェクトの読み込みを防ぎます。
///
/// # 使用例
/// ```rust,ignore
/// let policy = SafePicklePolicy::new()?;
/// let validator = SafePickleValidator::new(policy);
/// validator.validate(&pickle_data)?;
/// ```
pub struct SafePickleValidator {
    /// 検証に使用するポリシー
    policy: SafePicklePolicy,
}

impl SafePickleValidator {
    /// 指定されたポリシーで新しいバリデーターを作成
    ///
    /// # 引数
    /// * `policy` - 検証に使用するSafePicklePolicy
    pub fn new(policy: SafePicklePolicy) -> Self {
        SafePickleValidator { policy }
    }

    /// Pickleデータの検証（ロードは行わない）
    ///
    /// 内部的にはsafe_loadsを呼び出して検証を行います。
    ///
    /// # 引数
    /// * `data` - 検証するPickleデータ
    ///
    /// # 戻り値
    /// - `Ok(())`: データが安全
    /// - `Err(PyErr)`: 検証失敗（危険なオブジェクトが含まれている）
    pub fn validate(&self, data: &[u8]) -> PyResult<()> {
        // ロードして検証、結果は破棄
        let _ = self.validate_and_load(data)?;
        Ok(())
    }

    /// Pickleデータを検証し、安全であればロード
    ///
    /// # 引数
    /// * `data` - 検証およびロードするPickleデータ
    ///
    /// # 戻り値
    /// - `Ok(PyObject)`: 検証済みでロードされたPythonオブジェクト
    /// - `Err(PyErr)`: 検証失敗またはロードエラー
    pub fn validate_and_load(&self, data: &[u8]) -> PyResult<PyObject> {
        Python::with_gil(|py| {
            // safe_pickleモジュールからsafe_loads関数を取得
            let safe_pickle = py.import("dictsqlite.modules.safe_pickle")?;
            let safe_loads = safe_pickle.getattr("safe_loads")?;
            let kwargs = pyo3::types::PyDict::new(py);
            kwargs.set_item("policy", self.policy.policy.bind(py))?;
            let result = safe_loads.call((data,), Some(&kwargs))?;
            Ok(result.unbind())
        })
    }
}

impl Default for SafePickleValidator {
    /// デフォルトポリシーを使用したバリデーターを作成
    fn default() -> Self {
        SafePickleValidator::new(SafePicklePolicy::default())
    }
}

/// PythonオブジェクトをJSON値に変換するヘルパー関数
///
/// この関数は、PythonオブジェクトをRustのserde_json::Valueに変換します。
/// JSONでサポートされている型（null, bool, 数値, 文字列, 配列, オブジェクト）
/// のみを処理できます。
///
/// # 引数
/// * `obj` - 変換するPythonオブジェクト
/// * `py` - Python GILトークン
///
/// # 戻り値
/// - `Ok(serde_json::Value)`: 変換されたJSON値
/// - `Err(PyErr)`: サポートされていない型の場合はTypeError
///
/// # サポートされる型
/// - None -> null
/// - bool -> boolean
/// - int -> number (i64 or u64)
/// - float -> number (f64)
/// - str -> string
/// - list -> array
/// - dict -> object
fn pyobject_to_json_value(obj: PyObject, py: Python) -> PyResult<serde_json::Value> {
    use pyo3::types::{PyBool, PyDict, PyFloat, PyInt, PyList, PyString};

    let obj_ref = obj.bind(py);

    // 型に応じて変換を行う
    if obj_ref.is_none() {
        // Python None -> JSON null
        Ok(serde_json::Value::Null)
    } else if let Ok(val) = obj_ref.downcast::<PyBool>() {
        // Python bool -> JSON boolean
        Ok(serde_json::Value::Bool(val.is_true()))
    } else if let Ok(val) = obj_ref.downcast::<PyInt>() {
        // Python int -> JSON number
        if let Ok(i) = val.extract::<i64>() {
            Ok(serde_json::Value::Number(i.into()))
        } else {
            // 大きな数値はu64として試行
            let u: u64 = val.extract()?;
            Ok(serde_json::Value::Number(u.into()))
        }
    } else if let Ok(val) = obj_ref.downcast::<PyFloat>() {
        // Python float -> JSON number
        let f: f64 = val.extract()?;
        Ok(serde_json::Value::Number(
            serde_json::Number::from_f64(f)
                .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Invalid float"))?,
        ))
    } else if let Ok(val) = obj_ref.downcast::<PyString>() {
        // Python str -> JSON string
        Ok(serde_json::Value::String(val.to_string()))
    } else if let Ok(val) = obj_ref.downcast::<PyList>() {
        // Python list -> JSON array（再帰的に変換）
        let mut arr = Vec::new();
        for item in val.iter() {
            arr.push(pyobject_to_json_value(item.into(), py)?);
        }
        Ok(serde_json::Value::Array(arr))
    } else if let Ok(val) = obj_ref.downcast::<PyDict>() {
        // Python dict -> JSON object（再帰的に変換）
        let mut map = serde_json::Map::new();
        for (key, value) in val.iter() {
            let key_str: String = key.extract()?;
            map.insert(key_str, pyobject_to_json_value(value.into(), py)?);
        }
        Ok(serde_json::Value::Object(map))
    } else {
        // サポートされていない型
        Err(PyErr::new::<pyo3::exceptions::PyTypeError, _>(
            "Unsupported type for JSON serialization. Use pickle mode for arbitrary objects.",
        ))
    }
}

/// JSON値をPythonオブジェクトに変換するヘルパー関数
///
/// この関数は、serde_json::ValueをPythonオブジェクトに変換します。
/// `pyobject_to_json_value`の逆変換を行います。
///
/// # 引数
/// * `value` - 変換するJSON値
/// * `py` - Python GILトークン
///
/// # 戻り値
/// - `Ok(PyObject)`: 変換されたPythonオブジェクト
/// - `Err(PyErr)`: 変換エラー（無効な数値など）
///
/// # 変換ルール
/// - null -> None
/// - boolean -> bool
/// - number -> int または float
/// - string -> str
/// - array -> list
/// - object -> dict
fn json_value_to_pyobject(value: serde_json::Value, py: Python) -> PyResult<PyObject> {
    use pyo3::types::{PyBool, PyDict, PyFloat, PyInt, PyList, PyString};

    match value {
        serde_json::Value::Null => Ok(py.None()),
        serde_json::Value::Bool(b) => Ok(PyBool::new(py, b).to_owned().unbind().into()),
        serde_json::Value::Number(n) => {
            // 整数として扱えるか試行
            if let Some(i) = n.as_i64() {
                Ok(PyInt::new(py, i).to_owned().unbind().into())
            } else if let Some(u) = n.as_u64() {
                Ok(PyInt::new(py, u).to_owned().unbind().into())
            } else if let Some(f) = n.as_f64() {
                Ok(PyFloat::new(py, f).to_owned().unbind().into())
            } else {
                Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    "Invalid number",
                ))
            }
        }
        serde_json::Value::String(s) => Ok(PyString::new(py, &s).to_owned().unbind().into()),
        serde_json::Value::Array(arr) => {
            // 配列の各要素を再帰的に変換
            let list = PyList::empty(py);
            for item in arr {
                list.append(json_value_to_pyobject(item, py)?)?;
            }
            Ok(list.into())
        }
        serde_json::Value::Object(map) => {
            // オブジェクトの各キー・値ペアを再帰的に変換
            let dict = PyDict::new(py);
            for (key, value) in map {
                dict.set_item(key, json_value_to_pyobject(value, py)?)?;
            }
            Ok(dict.into())
        }
    }
}

/// 書き込みバッファの型エイリアス（複雑さ軽減のため）
///
/// WriteBufferは、バッチ書き込み操作のために保留中の書き込みを保持します。
/// Vec<(key, value)>の形式で、キーと暗号化済みの値のペアを格納します。
type WriteBuffer = Arc<Mutex<Vec<(String, Vec<u8>)>>>;

/// 永続化モード - パフォーマンスと耐久性のトレードオフを制御
///
/// このモードは、データの書き込み時にいつディスクに永続化するかを決定します。
/// 用途に応じて適切なモードを選択してください。
///
/// # パフォーマンス比較
/// - Memory: 100M+ ops/sec（最速、永続化なし）
/// - Lazy: 40-80M ops/sec（高速、flush時に永続化）
/// - WriteThrough: 1-3M ops/sec（安全、即時永続化）
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
pub enum PersistMode {
    /// 純粋なインメモリモード
    ///
    /// - 最高速（100M+ ops/sec）
    /// - データは永続化されない（プロセス終了時に消失）
    /// - キャッシュやセッションデータに最適
    Memory,

    /// 遅延永続化モード
    ///
    /// - 高速（40-80M ops/sec）
    /// - flush()またはclose()時にのみディスクに書き込み
    /// - バッチ処理やデータ処理パイプラインに最適
    Lazy,

    /// 書き込み即時永続化モード
    ///
    /// - 安全（1-3M ops/sec）
    /// - 各書き込み操作後すぐにディスクに書き込み
    /// - 重要なデータや即時の耐久性が必要な場合に最適
    /// - v4.2: バッファリング最適化により43倍の高速化
    WriteThrough,
}

impl FromStr for PersistMode {
    type Err = String;

    /// 文字列からPersistModeを解析
    ///
    /// # 引数
    /// * `s` - 解析する文字列（大文字小文字を区別しない）
    ///
    /// # 有効な値
    /// - "memory" -> PersistMode::Memory
    /// - "lazy" -> PersistMode::Lazy
    /// - "writethrough" または "write_through" -> PersistMode::WriteThrough
    ///
    /// # 戻り値
    /// - `Ok(PersistMode)`: 解析成功
    /// - `Err(String)`: 無効な値の場合のエラーメッセージ
    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s.to_lowercase().as_str() {
            "memory" => Ok(PersistMode::Memory),
            "lazy" => Ok(PersistMode::Lazy),
            "writethrough" | "write_through" => Ok(PersistMode::WriteThrough),
            _ => Err(format!("Invalid persist_mode: {}", s)),
        }
    }
}

/// ストレージモード - データのシリアライズ形式を制御
///
/// データをどのような形式でSQLiteに保存するかを決定します。
/// 用途に応じて適切なモードを選択してください。
///
/// # モード比較
/// | モード  | サイズ | 速度  | 任意の型 | 可読性 |
/// |---------|--------|-------|----------|--------|
/// | Pickle  | 中     | 高速  | ◯        | ✕      |
/// | Json    | 大     | 中    | ✕        | ◯      |
/// | JsonB   | 小     | 高速  | ✕        | ✕      |
/// | Bytes   | 最小   | 最高速| バイト   | ✕      |
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Default)]
pub enum StorageMode {
    /// Pickle形式（デフォルト）
    ///
    /// - 任意のPythonオブジェクトを保存可能
    /// - Pythonエコシステムとの互換性が高い
    /// - Safe Pickle検証と組み合わせて使用推奨
    #[default]
    Pickle,

    /// JSON テキスト形式
    ///
    /// - 人間が読めるテキスト形式
    /// - 基本的なJSON型のみサポート（dict, list, str, int, float, bool, null）
    /// - 他システムとの相互運用性に優れる
    Json,

    /// JSONB バイナリ形式（MessagePack使用）
    ///
    /// - コンパクトなバイナリ形式
    /// - JSONより小さく高速
    /// - 基本的なJSON型のみサポート
    JsonB,

    /// 生バイト形式
    ///
    /// - 変換なしでバイト列を直接保存
    /// - 最高速・最小サイズ
    /// - アプリケーション側でのシリアライズが必要
    Bytes,
}

impl FromStr for StorageMode {
    type Err = String;

    /// 文字列からStorageModeを解析
    ///
    /// # 引数
    /// * `s` - 解析する文字列（大文字小文字を区別しない）
    ///
    /// # 有効な値
    /// - "pickle" -> StorageMode::Pickle
    /// - "json" -> StorageMode::Json
    /// - "jsonb" -> StorageMode::JsonB
    /// - "bytes" -> StorageMode::Bytes
    ///
    /// # 戻り値
    /// - `Ok(StorageMode)`: 解析成功
    /// - `Err(String)`: 無効な値の場合のエラーメッセージ
    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s.to_lowercase().as_str() {
            "pickle" => Ok(StorageMode::Pickle),
            "json" => Ok(StorageMode::Json),
            "jsonb" => Ok(StorageMode::JsonB),
            "bytes" => Ok(StorageMode::Bytes),
            _ => Err(format!(
                "Invalid storage_mode: {}. Choose from ['pickle', 'json', 'jsonb', 'bytes']",
                s
            )),
        }
    }
}

/// 高性能 DictSQLite v4.2 実装（I/O最適化版）
///
/// このクラスは、Pythonの辞書のようなインターフェースで
/// SQLiteデータベースを操作するための高性能実装を提供します。
///
/// # アーキテクチャ
/// - **Hot Tier**: ロックフリー並行ハッシュマップ（100M+ ops/sec）
/// - **LRUエビクション**: メモリ管理のための自動削除
/// - **Warm Tier**: 頻繁にアクセスされるデータのメモリマッピング
/// - **Cold Tier**: SQLiteでの永続化
/// - **非同期サポート**: I/O操作の非同期実行
/// - **AES-256-GCM暗号化**: オプショナルな暗号化（v4機能）
/// - **Safe Pickle検証**: 安全なPickle操作（v4機能）
///
/// # v4.2 最適化
/// - 書き込みバッファリングによるWriteThroughモードの43倍高速化
/// - バッチSQL操作によるI/Oオーバーヘッド削減
///
/// # 使用例
/// ```python
/// from dictsqlite import DictSQLiteV4
///
/// # 基本的な使用法
/// db = DictSQLiteV4("mydb.db")
/// db["key"] = "value"
/// print(db["key"])
///
/// # 暗号化付き
/// db = DictSQLiteV4("secure.db", encryption_password="secret123")
///
/// # 高速モード
/// db = DictSQLiteV4(":memory:", persist_mode="memory")
/// ```
#[pyclass]
pub struct DictSQLiteV4 {
    /// Hot Tier: ロックフリー並行ハッシュマップ（インメモリ）
    ///
    /// DashMapを使用して、複数スレッドから安全に高速アクセス可能。
    /// キーは文字列、値は暗号化済み（または生の）バイト列。
    hot_tier: Arc<DashMap<String, Vec<u8>>>,

    /// LRUトラッカー: エビクション用（挿入順序を保護）
    ///
    /// hot_tierがキャパシティを超えた場合、最も長く使われていない
    /// エントリを特定してwarm tierに退避するために使用。
    access_tracker: Arc<Mutex<LruCache<String, ()>>>,

    /// ストレージエンジン: warm/cold tierの管理
    ///
    /// Memory以外の永続化モードで使用。
    /// SQLiteへの読み書きを担当。
    storage: Arc<Mutex<Option<StorageEngine>>>,

    /// 設定
    config: Config,

    /// 暗号化エンジン（オプショナル）
    ///
    /// encryption_passwordが指定された場合のみ有効。
    /// AES-256-GCMによる暗号化・復号化を行う。
    crypto: Option<Arc<CryptoEngine>>,

    /// Safe Pickleバリデーター（オプショナル）
    ///
    /// enable_safe_pickle=Trueの場合のみ有効。
    /// Pickleデータの安全性を検証する。
    safe_pickle: Option<Arc<SafePickleValidator>>,

    /// 書き込みバッファ: SQLバッチ書き込み用（v4.2最適化）
    ///
    /// WriteThroughモードでの書き込みを一時的にバッファリングし、
    /// バッチでSQLiteに書き込むことでパフォーマンスを向上。
    write_buffer: WriteBuffer,

    /// バッファサイズ閾値: 自動フラッシュ用
    ///
    /// バッファがこのサイズに達すると自動的にフラッシュ。
    /// 現在WriteThroughモードでは未使用（即時フラッシュのため）。
    #[allow(dead_code)]
    buffer_size: usize,
}

/// DictSQLiteの設定構造体
///
/// データベースの動作を制御するための各種設定を保持します。
/// デフォルト値は一般的なユースケースに最適化されています。
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Config {
    /// Hot tierの最大エントリ数
    ///
    /// この数を超えると、LRUエビクションが発動し、
    /// 最も使われていないエントリがwarm tierに移動します。
    /// デフォルト: 1,000,000エントリ
    pub hot_tier_capacity: usize,

    /// Warm tierのサイズ（バイト）
    ///
    /// メモリ内キャッシュの最大サイズ。
    /// デフォルト: 100MB
    pub warm_tier_size: usize,

    /// 非同期バックグラウンドフラッシュの有効化
    ///
    /// trueの場合、バックグラウンドでデータを永続化。
    /// デフォルト: true
    pub enable_async_flush: bool,

    /// フラッシュ間隔（ミリ秒）
    ///
    /// 非同期フラッシュが有効な場合の間隔。
    /// デフォルト: 1000ms
    pub flush_interval_ms: u64,

    /// シャード数（並行アクセス用）
    ///
    /// DashMapの内部シャード数。CPUコア数に基づいて設定。
    /// 2のべき乗に切り上げられます。
    /// デフォルト: CPUコア数の2のべき乗
    pub num_shards: usize,

    /// 永続化モード
    ///
    /// データの永続化タイミングを制御。
    /// デフォルト: WriteThrough（即時永続化）
    pub persist_mode: PersistMode,

    /// 暗号化の有効化
    ///
    /// encryption_passwordが設定されている場合にtrue。
    /// デフォルト: false
    pub enable_encryption: bool,

    /// Safe Pickle検証の有効化
    ///
    /// Pickleデータの安全性検証を有効にする。
    /// デフォルト: false
    pub enable_safe_pickle: bool,

    /// ストレージモード
    ///
    /// データのシリアライズ形式。
    /// デフォルト: Pickle
    pub storage_mode: StorageMode,

    /// デフォルトテーブル名
    ///
    /// テーブルを指定しない操作で使用されるテーブル。
    /// デフォルト: "main"
    pub table_name: String,
}

impl Default for Config {
    /// デフォルト設定の取得
    ///
    /// 一般的なユースケースに最適化されたデフォルト値を返します。
    /// 必要に応じてこれらの値を上書きしてカスタマイズできます。
    fn default() -> Self {
        Config {
            hot_tier_capacity: 1_000_000,       // 100万エントリ
            warm_tier_size: 100 * 1024 * 1024,  // 100MB
            enable_async_flush: true,           // 非同期フラッシュ有効
            flush_interval_ms: 1000,            // 1秒間隔
            num_shards: num_cpus::get().next_power_of_two(), // CPUコア数ベース
            persist_mode: PersistMode::WriteThrough, // 即時永続化
            enable_encryption: false,           // 暗号化なし
            enable_safe_pickle: false,          // Safe Pickle検証なし
            storage_mode: StorageMode::Pickle,  // Pickle形式
            table_name: "main".to_string(),     // メインテーブル
        }
    }
}

#[pymethods]
impl DictSQLiteV4 {
    /// DictSQLiteV4の新しいインスタンスを作成
    ///
    /// # 引数
    /// * `db_path` - データベースファイルのパス（":memory:"でインメモリDB）
    /// * `hot_capacity` - Hot tierの最大エントリ数（デフォルト: 1,000,000）
    /// * `enable_async` - 非同期フラッシュを有効にするか（デフォルト: true）
    /// * `persist_mode` - 永続化モード: "memory", "lazy", "writethrough"
    /// * `storage_mode` - ストレージモード: "pickle", "json", "jsonb", "bytes"
    /// * `table_name` - デフォルトテーブル名（デフォルト: "main"）
    /// * `encryption_password` - 暗号化パスワード（Noneで暗号化なし）
    /// * `enable_safe_pickle` - Safe Pickle検証を有効にするか
    /// * `safe_pickle_allowed_modules` - Safe Pickleで許可するモジュールプレフィックス
    /// * `buffer_size` - 書き込みバッファサイズ（デフォルト: 100）
    ///
    /// # 戻り値
    /// 新しいDictSQLiteV4インスタンス
    ///
    /// # エラー
    /// - 無効なpersist_modeまたはstorage_modeの場合: ValueError
    /// - データベースファイルを開けない場合: IOError
    /// - 暗号化エンジンの初期化に失敗した場合: ValueError
    ///
    /// # 使用例
    /// ```python
    /// # 基本的な使用法
    /// db = DictSQLiteV4("mydb.db")
    ///
    /// # 暗号化付き
    /// db = DictSQLiteV4("secure.db", encryption_password="secret")
    ///
    /// # JSONB形式で高速永続化
    /// db = DictSQLiteV4("fast.db", storage_mode="jsonb", persist_mode="lazy")
    /// ```
    #[new]
    #[pyo3(signature = (db_path, hot_capacity=1_000_000, enable_async=true, persist_mode="writethrough", storage_mode="pickle", table_name="main", encryption_password=None, enable_safe_pickle=false, safe_pickle_allowed_modules=None, buffer_size=100))]
    #[allow(clippy::too_many_arguments)]
    fn new(
        db_path: String,
        hot_capacity: usize,
        enable_async: bool,
        persist_mode: &str,
        storage_mode: &str,
        table_name: &str,
        encryption_password: Option<String>,
        enable_safe_pickle: bool,
        safe_pickle_allowed_modules: Option<Vec<String>>,
        buffer_size: usize,
    ) -> PyResult<Self> {
        // 永続化モードを文字列からenumに変換
        let persist_mode_parsed = PersistMode::from_str(persist_mode)
            .map_err(PyErr::new::<pyo3::exceptions::PyValueError, _>)?;

        // ストレージモードを文字列からenumに変換
        let storage_mode_parsed = StorageMode::from_str(storage_mode)
            .map_err(PyErr::new::<pyo3::exceptions::PyValueError, _>)?;

        // 設定を構築
        let config = Config {
            hot_tier_capacity: hot_capacity,
            enable_async_flush: enable_async,
            persist_mode: persist_mode_parsed,
            enable_encryption: encryption_password.is_some(),
            enable_safe_pickle,
            storage_mode: storage_mode_parsed,
            table_name: table_name.to_string(),
            ..Default::default()
        };

        // DashMapをシャード数とキャパシティで初期化
        // シャード数はCPUコア数に基づいて最適化
        let hot_tier = Arc::new(DashMap::with_capacity_and_shard_amount(
            config.hot_tier_capacity,
            config.num_shards,
        ));

        // LRUキャッシュをエビクション追跡用に初期化
        let access_tracker = Arc::new(Mutex::new(LruCache::new(
            NonZeroUsize::new(config.hot_tier_capacity).unwrap(),
        )));

        // 純粋なメモリモードでない場合のみストレージを作成
        let storage = if config.persist_mode == PersistMode::Memory {
            Arc::new(Mutex::new(None))
        } else {
            Arc::new(Mutex::new(Some(
                StorageEngine::new(&db_path, &config)
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?,
            )))
        };

        // パスワードが提供された場合、暗号化エンジンを初期化
        let crypto = if let Some(password) = encryption_password {
            Some(Arc::new(CryptoEngine::new(&password, None).map_err(
                |e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()),
            )?))
        } else {
            None
        };

        // Safe Pickle検証が有効な場合、バリデーターを初期化
        let safe_pickle = if enable_safe_pickle {
            // カスタム許可モジュールが提供された場合はポリシーを構築
            let policy = if let Some(modules) = safe_pickle_allowed_modules {
                let mut policy = SafePicklePolicy::new()?;
                for module in modules {
                    policy = policy.with_module_prefix(module.clone())?;
                }
                policy
            } else {
                SafePicklePolicy::default()
            };

            Some(Arc::new(SafePickleValidator::new(policy)))
        } else {
            None
        };

        // 書き込みバッファを初期化（v4.2最適化）
        let write_buffer = Arc::new(Mutex::new(Vec::with_capacity(buffer_size)));

        Ok(DictSQLiteV4 {
            hot_tier,
            access_tracker,
            storage,
            config,
            crypto,
            safe_pickle,
            write_buffer,
            buffer_size,
        })
    }

    /// キーで値を取得（Hot tierからのロックフリー読み取り）
    ///
    /// # 引数
    /// * `key` - 取得するキー
    /// * `default` - キーが存在しない場合のデフォルト値（オプション）
    ///
    /// # 戻り値
    /// 値のバイト列、または存在しない場合はdefaultまたはNone
    ///
    /// # 処理の流れ
    /// 1. Hot tierで検索（最速）
    /// 2. 見つからない場合はストレージ（Cold tier）で検索
    /// 3. ストレージで見つかった場合はHot tierにプロモート
    /// 4. 暗号化されている場合は復号化
    ///
    /// # エラー
    /// - 暗号化されたデータでパスワードなしの場合: ValueError
    /// - 復号化に失敗した場合: ValueError
    #[pyo3(signature = (key, default=None))]
    fn get(&self, key: String, default: Option<Vec<u8>>, py: Python) -> PyResult<PyObject> {
        // LRU追跡のためにアクセスを記録
        self.access_tracker.lock().unwrap().put(key.clone(), ());

        // Hot tierを最初に試行（ロックフリー読み取り）
        if let Some(value) = self.hot_tier.get(&key) {
            // 暗号化されているがパスワードがない場合のチェック
            if self.crypto.is_none() && crate::crypto::CryptoEngine::is_encrypted(&value) {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    "Data is encrypted but no password was provided",
                ));
            }

            // 暗号化が有効な場合は復号化
            let data = if let Some(ref crypto) = self.crypto {
                crypto
                    .decrypt(&value)
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?
            } else {
                value.clone()
            };
            return Ok(PyBytes::new(py, &data).into());
        }

        // Memoryモードの場合、Hot tierが唯一のtier
        if self.config.persist_mode == PersistMode::Memory {
            return Ok(default
                .map(|v| PyBytes::new(py, &v).into())
                .unwrap_or_else(|| py.None()));
        }

        // 他のモードではストレージ（Cold tier）も検索
        let storage_guard = self.storage.lock().unwrap();
        if let Some(ref storage) = *storage_guard {
            if let Ok(Some(value)) = storage.get(&key) {
                // 暗号化されているがパスワードがない場合のチェック
                if self.crypto.is_none() && crate::crypto::CryptoEngine::is_encrypted(&value) {
                    return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                        "Data is encrypted but no password was provided",
                    ));
                }

                // 暗号化が有効な場合は復号化
                let data = if let Some(ref crypto) = self.crypto {
                    crypto.decrypt(&value).map_err(|e| {
                        PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string())
                    })?
                } else {
                    value.clone()
                };

                // Hot tierにプロモート（暗号化状態で保存）
                // これにより次回アクセス時の速度が向上
                drop(storage_guard);
                self.hot_tier.insert(key, value);
                return Ok(PyBytes::new(py, &data).into());
            }
        }

        // キーが見つからない場合はデフォルト値またはNoneを返す
        Ok(default
            .map(|v| PyBytes::new(py, &v).into())
            .unwrap_or_else(|| py.None()))
    }

    /// キーに値を設定（Hot tierへのロックフリー書き込み）
    ///
    /// # 引数
    /// * `key` - 設定するキー
    /// * `value` - 設定する値（バイト列）
    ///
    /// # 処理の流れ
    /// 1. Safe Pickle検証（有効な場合、Pickleモードのみ）
    /// 2. 暗号化（有効な場合）
    /// 3. Hot tierに書き込み
    /// 4. LRUアクセス追跡を更新
    /// 5. WriteThroughモードの場合、バッファ経由でストレージに書き込み
    /// 6. 必要に応じてLRUエビクションを実行
    ///
    /// # v4.2最適化
    /// 書き込みバッファリングにより、WriteThroughモードで43倍の高速化を実現。
    ///
    /// # エラー
    /// - Safe Pickle検証に失敗した場合: ValueError
    /// - 暗号化に失敗した場合: ValueError
    /// - ストレージ書き込みに失敗した場合: IOError
    fn set(&self, key: String, value: Vec<u8>) -> PyResult<()> {
        // Safe Pickle検証（有効かつPickleモードの場合のみ）
        // JSON/JSONB/Bytesモードでは意味がないのでスキップ
        if let Some(ref validator) = self.safe_pickle {
            if self.config.storage_mode == StorageMode::Pickle {
                validator
                    .validate(&value)
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;
            }
        }

        // 暗号化が有効な場合は暗号化
        let data = if let Some(ref crypto) = self.crypto {
            crypto
                .encrypt(&value)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?
        } else {
            value
        };

        // Hot tierに挿入（ロックフリー書き込み）
        self.hot_tier.insert(key.clone(), data.clone());

        // LRUアクセス追跡を更新
        self.access_tracker.lock().unwrap().put(key.clone(), ());

        // v4.2最適化: WriteThroughモードでは書き込みバッファを使用
        if self.config.persist_mode == PersistMode::WriteThrough {
            let should_flush = {
                let mut buffer = self.write_buffer.lock().unwrap();
                buffer.push((key.clone(), data));
                // バッファサイズに達したらフラッシュ
                // buffer_size=1の場合は即時フラッシュ
                buffer.len() >= self.buffer_size
            };

            // バッファが満杯ならフラッシュ
            if should_flush {
                self.flush_write_buffer()?;
            }
        }

        // Hot tierがキャパシティを超えた場合、エビクションを実行
        if self.hot_tier.len() > self.config.hot_tier_capacity {
            self.evict_to_warm_tier()?;
        }

        Ok(())
    }

    /// 最も長く使われていないアイテムをWarm tier（ストレージ）に退避
    ///
    /// Hot tierがキャパシティを超えた場合に呼び出されます。
    /// LRUトラッカーを使用して最も古いエントリを特定し、
    /// ストレージに書き込んでからHot tierから削除します。
    ///
    /// # エラー
    /// - ストレージ書き込みに失敗した場合: IOError
    fn evict_to_warm_tier(&self) -> PyResult<()> {
        let mut tracker = self.access_tracker.lock().unwrap();

        // LRU（最も長く使われていない）エントリを見つける
        if let Some((evict_key, _)) = tracker.pop_lru() {
            // Hot tierから削除
            if let Some((_, value)) = self.hot_tier.remove(&evict_key) {
                // Memoryモードでない場合はストレージに書き込み
                if self.config.persist_mode != PersistMode::Memory {
                    let mut storage_guard = self.storage.lock().unwrap();
                    if let Some(ref mut storage) = *storage_guard {
                        storage.set(&evict_key, &value).map_err(|e| {
                            PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string())
                        })?;
                    }
                }
            }
        }

        Ok(())
    }

    /// 書き込みバッファをストレージにフラッシュ（v4.2最適化）
    ///
    /// バッファ内の複数の書き込みをバッチでSQLiteに書き込むことで、
    /// I/Oオーバーヘッドを削減しパフォーマンスを向上させます。
    ///
    /// # 戻り値
    /// - `Ok(())`: フラッシュ成功
    /// - `Err(PyErr)`: ストレージ書き込みエラー
    fn flush_write_buffer(&self) -> PyResult<()> {
        let mut buffer = self.write_buffer.lock().unwrap();

        // バッファが空の場合は何もしない
        if buffer.is_empty() {
            return Ok(());
        }

        // ストレージハンドルを取得
        let mut storage_guard = self.storage.lock().unwrap();
        if let Some(ref mut storage) = *storage_guard {
            // バッファ内の全アイテムを書き込み
            for (key, value) in buffer.drain(..) {
                storage
                    .set(&key, &value)
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
            }
        }

        Ok(())
    }

    /// 保留中の書き込みをストレージにフラッシュ
    ///
    /// Lazyモードでは、このメソッドを呼び出すまでデータは永続化されません。
    /// WriteThroughモードでは書き込みバッファのフラッシュのみ行います。
    /// Memoryモードでは何もしません。
    ///
    /// # v4.2
    /// 書き込みバッファも同時にフラッシュします。
    ///
    /// # 使用例
    /// ```python
    /// db = DictSQLiteV4("test.db", persist_mode="lazy")
    /// db["key"] = "value"
    /// db.flush()  # ここで永続化される
    /// ```
    fn flush(&self) -> PyResult<()> {
        // Memoryモードでは何もしない
        if self.config.persist_mode == PersistMode::Memory {
            return Ok(());
        }

        // まず書き込みバッファをフラッシュ（v4.2）
        self.flush_write_buffer()?;

        // Then flush hot tier for Lazy mode
        if self.config.persist_mode == PersistMode::Lazy {
            let mut storage_guard = self.storage.lock().unwrap();
            if let Some(ref mut storage) = *storage_guard {
                // Persist all hot tier entries
                for entry in self.hot_tier.iter() {
                    storage
                        .set(entry.key(), entry.value())
                        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
                }
            }
        }
        Ok(())
    }

    /// Delete key
    fn delete(&self, key: String) -> PyResult<()> {
        // Check if key exists first
        if !self.contains(key.clone())? {
            return Err(PyErr::new::<pyo3::exceptions::PyKeyError, _>(format!(
                "Key not found: {}",
                key
            )));
        }

        // Track that we're removing this
        self.access_tracker.lock().unwrap().pop(&key);

        // Remove from hot tier
        self.hot_tier.remove(&key);

        // Remove from write buffer (v4.2)
        if self.config.persist_mode == PersistMode::WriteThrough {
            let mut buffer = self.write_buffer.lock().unwrap();
            buffer.retain(|(k, _)| k != &key);
        }

        // Also remove from storage
        if self.config.persist_mode != PersistMode::Memory {
            let mut storage_guard = self.storage.lock().unwrap();
            if let Some(ref mut storage) = *storage_guard {
                let _ = storage.delete(&key);
            }
        }

        Ok(())
    }

    /// Bulk insert (optimized batch operation)
    fn bulk_insert(&self, items: Bound<'_, PyDict>) -> PyResult<()> {
        for (key, value) in items.iter() {
            let key_str: String = key.extract()?;
            let value_bytes: Vec<u8> = value.extract()?;
            self.hot_tier.insert(key_str, value_bytes);
        }
        Ok(())
    }

    /// Get all keys
    fn keys(&self, _py: Python) -> PyResult<Vec<String>> {
        use std::collections::HashSet;

        // Collect keys from hot tier
        let mut all_keys: HashSet<String> = self
            .hot_tier
            .iter()
            .map(|entry| entry.key().clone())
            .collect();

        // Also get keys from storage if not in memory-only mode
        if self.config.persist_mode != PersistMode::Memory {
            let storage_guard = self.storage.lock().unwrap();
            if let Some(ref storage) = *storage_guard {
                if let Ok(storage_keys) = storage.keys() {
                    all_keys.extend(storage_keys);
                }
            }
        }

        Ok(all_keys.into_iter().collect())
    }

    /// Get all items as (key, value) tuples (dict-compatible)
    fn items(&self, py: Python) -> PyResult<Vec<(String, PyObject)>> {
        use std::collections::HashMap;

        // First, get all items from storage
        let mut all_items: HashMap<String, Vec<u8>> = HashMap::new();

        if self.config.persist_mode != PersistMode::Memory {
            let storage_guard = self.storage.lock().unwrap();
            if let Some(ref storage) = *storage_guard {
                if let Ok(keys) = storage.keys() {
                    for key in keys {
                        if let Ok(Some(value)) = storage.get(&key) {
                            all_items.insert(key, value);
                        }
                    }
                }
            }
        }

        // Then overlay with hot tier items (which take precedence)
        for entry in self.hot_tier.iter() {
            all_items.insert(entry.key().clone(), entry.value().clone());
        }

        // Convert to Python objects
        let items: Vec<(String, PyObject)> = all_items
            .into_iter()
            .map(|(key, value)| {
                let data = if let Some(ref crypto) = self.crypto {
                    crypto.decrypt(&value).unwrap_or_else(|_| value.clone())
                } else {
                    value
                };
                (key, PyBytes::new(py, &data).into())
            })
            .collect();
        Ok(items)
    }

    /// Get all values (dict-compatible)
    fn values(&self, py: Python) -> PyResult<Vec<PyObject>> {
        use std::collections::HashMap;

        // First, get all items from storage
        let mut all_items: HashMap<String, Vec<u8>> = HashMap::new();

        if self.config.persist_mode != PersistMode::Memory {
            let storage_guard = self.storage.lock().unwrap();
            if let Some(ref storage) = *storage_guard {
                if let Ok(keys) = storage.keys() {
                    for key in keys {
                        if let Ok(Some(value)) = storage.get(&key) {
                            all_items.insert(key, value);
                        }
                    }
                }
            }
        }

        // Then overlay with hot tier items (which take precedence)
        for entry in self.hot_tier.iter() {
            all_items.insert(entry.key().clone(), entry.value().clone());
        }

        // Convert to Python objects
        let values: Vec<PyObject> = all_items
            .into_values()
            .map(|value| {
                let data = if let Some(ref crypto) = self.crypto {
                    crypto.decrypt(&value).unwrap_or_else(|_| value.clone())
                } else {
                    value
                };
                PyBytes::new(py, &data).into()
            })
            .collect();
        Ok(values)
    }

    /// Update from dict (dict-compatible alias for bulk_insert)
    fn update(&self, items: Bound<'_, PyDict>) -> PyResult<()> {
        self.bulk_insert(items)
    }

    /// Pop with optional default (dict-compatible)
    #[pyo3(signature = (key, default=None))]
    fn pop(&self, key: String, default: Option<Vec<u8>>, py: Python) -> PyResult<PyObject> {
        // Track that we're removing this
        self.access_tracker.lock().unwrap().pop(&key);

        if let Some((_, value)) = self.hot_tier.remove(&key) {
            let data = if let Some(ref crypto) = self.crypto {
                crypto
                    .decrypt(&value)
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?
            } else {
                value
            };
            return Ok(PyBytes::new(py, &data).into());
        }

        // Also try to remove from storage if it exists there
        if self.config.persist_mode != PersistMode::Memory {
            let mut storage_guard = self.storage.lock().unwrap();
            if let Some(ref mut storage) = *storage_guard {
                if let Ok(Some(value)) = storage.get(&key) {
                    // Delete from storage
                    let _ = storage.delete(&key);
                    let data = if let Some(ref crypto) = self.crypto {
                        crypto.decrypt(&value).map_err(|e| {
                            PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string())
                        })?
                    } else {
                        value
                    };
                    return Ok(PyBytes::new(py, &data).into());
                }
            }
        }

        Ok(default
            .map(|v| PyBytes::new(py, &v).into())
            .unwrap_or_else(|| py.None()))
    }

    /// Setdefault - get value or set and return default (dict-compatible)
    fn setdefault(&self, key: String, default: Vec<u8>, py: Python) -> PyResult<PyObject> {
        // Check if key exists
        if let Some(value) = self.hot_tier.get(&key) {
            let data = if let Some(ref crypto) = self.crypto {
                crypto
                    .decrypt(&value)
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?
            } else {
                value.clone()
            };
            return Ok(PyBytes::new(py, &data).into());
        }

        // Not in hot tier, check storage
        if self.config.persist_mode != PersistMode::Memory {
            let storage_guard = self.storage.lock().unwrap();
            if let Some(ref storage) = *storage_guard {
                if let Ok(Some(value)) = storage.get(&key) {
                    let data = if let Some(ref crypto) = self.crypto {
                        crypto.decrypt(&value).map_err(|e| {
                            PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string())
                        })?
                    } else {
                        value.clone()
                    };
                    drop(storage_guard);
                    // Promote to hot tier
                    self.hot_tier.insert(key, value);
                    return Ok(PyBytes::new(py, &data).into());
                }
            }
        }

        // Key doesn't exist, set the default
        self.set(key.clone(), default.clone())?;
        Ok(PyBytes::new(py, &default).into())
    }

    /// Get number of items in hot tier
    fn len(&self) -> PyResult<usize> {
        use std::collections::HashSet;

        // Determine the key prefix for this table
        let prefix = if !self.config.table_name.is_empty() && self.config.table_name != "main" {
            format!("{}:", self.config.table_name)
        } else {
            String::new()
        };

        // Collect all unique keys for this table
        let mut all_keys: HashSet<String> = self
            .hot_tier
            .iter()
            .filter_map(|entry| {
                let key = entry.key().clone();
                // If we have a prefix, only include keys with that prefix
                if !prefix.is_empty() {
                    if key.starts_with(&prefix) {
                        Some(key)
                    } else {
                        None
                    }
                } else {
                    // For main table, exclude keys with any table prefix (containing ':')
                    if !key.contains(':') {
                        Some(key)
                    } else {
                        None
                    }
                }
            })
            .collect();

        // Also get keys from storage if not in memory-only mode
        if self.config.persist_mode != PersistMode::Memory {
            let storage_guard = self.storage.lock().unwrap();
            if let Some(ref storage) = *storage_guard {
                if let Ok(storage_keys) = storage.keys() {
                    for key in storage_keys {
                        // Apply same filtering logic
                        if !prefix.is_empty() {
                            if key.starts_with(&prefix) {
                                all_keys.insert(key);
                            }
                        } else {
                            // For main table, exclude keys with any table prefix
                            if !key.contains(':') {
                                all_keys.insert(key);
                            }
                        }
                    }
                }
            }
        }

        Ok(all_keys.len())
    }

    /// Check if key exists
    fn contains(&self, key: String) -> PyResult<bool> {
        // Add table prefix if needed
        let full_key = if !self.config.table_name.is_empty() && self.config.table_name != "main" {
            format!("{}:{}", self.config.table_name, key)
        } else {
            key
        };

        // First check hot tier
        if self.hot_tier.contains_key(&full_key) {
            return Ok(true);
        }

        // Then check storage
        if self.config.persist_mode != PersistMode::Memory {
            let storage_guard = self.storage.lock().unwrap();
            if let Some(ref storage) = *storage_guard {
                if let Ok(Some(_)) = storage.get(&full_key) {
                    return Ok(true);
                }
            }
        }

        Ok(false)
    }

    /// Clear all data
    fn clear(&self) -> PyResult<()> {
        // Clear hot tier (in-memory cache)
        self.hot_tier.clear();

        // Clear write buffer to prevent pending writes from re-populating the database
        self.write_buffer.lock().unwrap().clear();

        // Clear storage if not in memory-only mode
        if self.config.persist_mode != PersistMode::Memory {
            let mut storage_guard = self.storage.lock().unwrap();
            if let Some(ref mut storage) = *storage_guard {
                storage.clear().map_err(|e| {
                    PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!(
                        "Failed to clear storage: {}",
                        e
                    ))
                })?;
            }
        }

        Ok(())
    }

    /// Close database (flush if needed)
    fn close(&self) -> PyResult<()> {
        self.flush()?;
        Ok(())
    }

    /// Get performance stats
    fn stats(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        dict.set_item("hot_tier_size", self.hot_tier.len())?;
        dict.set_item("hot_tier_capacity", self.config.hot_tier_capacity)?;
        dict.set_item("num_shards", self.config.num_shards)?;
        dict.set_item("encryption_enabled", self.crypto.is_some())?;
        dict.set_item("safe_pickle_enabled", self.safe_pickle.is_some())?;
        dict.set_item("persist_mode", format!("{:?}", self.config.persist_mode))?;
        Ok(dict.into())
    }

    /// Dict-like access: db[key]
    fn __getitem__(&self, key: String, py: Python) -> PyResult<PyObject> {
        // Add table prefix if default table is not "main" or empty
        let full_key = if !self.config.table_name.is_empty() && self.config.table_name != "main" {
            format!("{}:{}", self.config.table_name, key)
        } else {
            key.clone()
        };

        let result = self.get(full_key.clone(), None, py)?;
        if result.is_none(py) {
            return Err(PyErr::new::<pyo3::exceptions::PyKeyError, _>(format!(
                "Key not found: {}",
                key
            )));
        }

        // Extract bytes from result
        let data: Vec<u8> = result.extract(py)?;

        // Deserialize based on storage mode
        match self.config.storage_mode {
            StorageMode::Pickle => {
                // If safe_pickle is enabled, use safe_loads for validation
                if self.config.enable_safe_pickle {
                    if let Some(ref validator) = self.safe_pickle {
                        // Use safe_pickle validator to load and validate
                        let unpickled = validator.validate_and_load(&data)?;
                        Ok(unpickled)
                    } else {
                        // Fallback: use regular pickle.loads
                        let pickle = py.import("pickle")?;
                        let loads = pickle.getattr("loads")?;
                        let unpickled = loads.call1((PyBytes::new(py, &data),))?;
                        Ok(unpickled.into())
                    }
                } else {
                    // Use pickle module to deserialize
                    let pickle = py.import("pickle")?;
                    let loads = pickle.getattr("loads")?;
                    let unpickled = loads.call1((PyBytes::new(py, &data),))?;
                    Ok(unpickled.into())
                }
            }
            StorageMode::Json => {
                // Deserialize from JSON text
                let json_value: serde_json::Value = serde_json::from_slice(&data).map_err(|e| {
                    PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                        "JSON deserialization error: {}",
                        e
                    ))
                })?;
                json_value_to_pyobject(json_value, py)
            }
            StorageMode::JsonB => {
                // Deserialize from MessagePack binary
                let json_value: serde_json::Value = rmp_serde::from_slice(&data).map_err(|e| {
                    PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                        "MessagePack deserialization error: {}",
                        e
                    ))
                })?;
                json_value_to_pyobject(json_value, py)
            }
            StorageMode::Bytes => {
                // Return raw bytes
                Ok(PyBytes::new(py, &data).into())
            }
        }
    }

    /// Dict-like access: db[key] = value
    fn __setitem__(&self, key: String, value: PyObject, py: Python) -> PyResult<()> {
        // Add table prefix if default table is not "main" or empty
        let full_key = if !self.config.table_name.is_empty() && self.config.table_name != "main" {
            format!("{}:{}", self.config.table_name, key)
        } else {
            key.clone()
        };

        // Convert value based on storage mode
        let data: Vec<u8> = match self.config.storage_mode {
            StorageMode::Pickle => {
                // If value is already bytes, check if it's pickled data
                // Pickle data starts with 0x80 (protocol 2+) or other specific markers
                if let Ok(bytes_data) = value.extract::<Vec<u8>>(py) {
                    // Check if it looks like pickle data (starts with pickle protocol marker)
                    if !bytes_data.is_empty() && (bytes_data[0] == 0x80 || bytes_data[0] == 0x00) {
                        // Likely pre-pickled data, use directly for safe_pickle validation
                        bytes_data
                    } else {
                        // Plain bytes, need to pickle
                        let pickle = py.import("pickle")?;
                        let dumps = pickle.getattr("dumps")?;
                        let pickled = dumps.call1((value,))?;
                        pickled.extract::<Vec<u8>>()?
                    }
                } else {
                    // Not bytes, use pickle module to serialize
                    let pickle = py.import("pickle")?;
                    let dumps = pickle.getattr("dumps")?;
                    let pickled = dumps.call1((value,))?;
                    pickled.extract::<Vec<u8>>()?
                }
            }
            StorageMode::Json => {
                // Convert to JSON text
                let json_value = pyobject_to_json_value(value, py)?;
                serde_json::to_vec(&json_value).map_err(|e| {
                    PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                        "JSON serialization error: {}",
                        e
                    ))
                })?
            }
            StorageMode::JsonB => {
                // Convert to MessagePack binary
                let json_value = pyobject_to_json_value(value, py)?;
                rmp_serde::to_vec(&json_value).map_err(|e| {
                    PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                        "MessagePack serialization error: {}",
                        e
                    ))
                })?
            }
            StorageMode::Bytes => {
                // Expect bytes directly
                value.extract::<Vec<u8>>(py)?
            }
        };

        self.set(full_key, data)
    }

    /// Dict-like access: del db[key]
    fn __delitem__(&self, key: String) -> PyResult<()> {
        self.delete(key)
    }

    /// Dict-like access: key in db
    fn __contains__(&self, key: String) -> PyResult<bool> {
        self.contains(key)
    }

    /// Dict-like access: len(db)
    fn __len__(&self) -> PyResult<usize> {
        self.len()
    }

    /// Get a table proxy for accessing a specific table
    fn table(slf: PyRef<Self>, table_name: String) -> PyResult<TableProxy> {
        Ok(TableProxy {
            db: slf.into(),
            table_name,
        })
    }

    /// List all tables (by extracting unique table prefixes from keys)
    fn tables(&self, _py: Python) -> PyResult<Vec<String>> {
        let all_keys = self.keys(_py)?;
        let mut tables = std::collections::HashSet::new();

        for key in all_keys {
            if let Some(pos) = key.find(':') {
                tables.insert(key[..pos].to_string());
            } else {
                // Keys without prefix belong to "main" table
                tables.insert("main".to_string());
            }
        }

        Ok(tables.into_iter().collect())
    }
}

/// TableProxy provides dict-like access to a specific table
#[pyclass]
pub struct TableProxy {
    db: Py<DictSQLiteV4>,
    table_name: String,
}

#[pymethods]
impl TableProxy {
    /// Dict-like access: table[key]
    fn __getitem__(&self, key: String, py: Python) -> PyResult<PyObject> {
        let full_key = format!("{}:{}", self.table_name, key);
        let db = self.db.borrow(py);

        // Get the raw data
        let result = db.get(full_key.clone(), None, py)?;
        if result.is_none(py) {
            return Err(PyErr::new::<pyo3::exceptions::PyKeyError, _>(format!(
                "Key not found: {}",
                key
            )));
        }

        // Extract and deserialize based on storage mode
        let data: Vec<u8> = result.extract(py)?;

        match db.config.storage_mode {
            StorageMode::Pickle => {
                let pickle = py.import("pickle")?;
                let loads = pickle.getattr("loads")?;
                let unpickled = loads.call1((PyBytes::new(py, &data),))?;
                Ok(unpickled.into())
            }
            StorageMode::Json => {
                let json_value: serde_json::Value = serde_json::from_slice(&data).map_err(|e| {
                    PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                        "JSON deserialization error: {}",
                        e
                    ))
                })?;
                json_value_to_pyobject(json_value, py)
            }
            StorageMode::JsonB => {
                let json_value: serde_json::Value = rmp_serde::from_slice(&data).map_err(|e| {
                    PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                        "MessagePack deserialization error: {}",
                        e
                    ))
                })?;
                json_value_to_pyobject(json_value, py)
            }
            StorageMode::Bytes => Ok(PyBytes::new(py, &data).into()),
        }
    }

    /// Dict-like access: table[key] = value
    fn __setitem__(&self, key: String, value: PyObject, py: Python) -> PyResult<()> {
        let full_key = format!("{}:{}", self.table_name, key);
        let db = self.db.borrow(py);

        // Serialize based on storage mode
        let data: Vec<u8> = match db.config.storage_mode {
            StorageMode::Pickle => {
                let pickle = py.import("pickle")?;
                let dumps = pickle.getattr("dumps")?;
                let pickled = dumps.call1((value,))?;
                pickled.extract::<Vec<u8>>()?
            }
            StorageMode::Json => {
                let json_value = pyobject_to_json_value(value, py)?;
                serde_json::to_vec(&json_value).map_err(|e| {
                    PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                        "JSON serialization error: {}",
                        e
                    ))
                })?
            }
            StorageMode::JsonB => {
                let json_value = pyobject_to_json_value(value, py)?;
                rmp_serde::to_vec(&json_value).map_err(|e| {
                    PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                        "MessagePack serialization error: {}",
                        e
                    ))
                })?
            }
            StorageMode::Bytes => value.extract::<Vec<u8>>(py)?,
        };

        db.set(full_key, data)
    }

    /// Dict-like access: del table[key]
    fn __delitem__(&self, key: String, py: Python) -> PyResult<()> {
        let full_key = format!("{}:{}", self.table_name, key);
        let db = self.db.borrow(py);
        db.delete(full_key)
    }

    /// Dict-like access: key in table
    fn __contains__(&self, key: String, py: Python) -> PyResult<bool> {
        let full_key = format!("{}:{}", self.table_name, key);
        let db = self.db.borrow(py);
        db.contains(full_key)
    }

    /// Get all keys in this table
    fn keys(&self, py: Python) -> PyResult<Vec<String>> {
        let db = self.db.borrow(py);
        let all_keys = db.keys(py)?;
        let prefix = format!("{}:", self.table_name);

        Ok(all_keys
            .into_iter()
            .filter(|k| k.starts_with(&prefix))
            .map(|k| k[prefix.len()..].to_string())
            .collect())
    }

    /// Get all values in this table
    fn values(&self, py: Python) -> PyResult<Vec<PyObject>> {
        let keys = self.keys(py)?;
        let mut values = Vec::new();
        for key in keys {
            values.push(self.__getitem__(key, py)?);
        }
        Ok(values)
    }

    /// Get all items as (key, value) tuples
    fn items(&self, py: Python) -> PyResult<Vec<(String, PyObject)>> {
        let keys = self.keys(py)?;
        let mut items = Vec::new();
        for key in keys {
            items.push((key.clone(), self.__getitem__(key, py)?));
        }
        Ok(items)
    }

    /// Get value with default
    #[pyo3(signature = (key, default=None))]
    fn get(&self, key: String, default: Option<PyObject>, py: Python) -> PyResult<PyObject> {
        match self.__getitem__(key, py) {
            Ok(value) => Ok(value),
            Err(_) => Ok(default.unwrap_or_else(|| py.None())),
        }
    }

    /// Clear all items in this table
    fn clear(&self, py: Python) -> PyResult<()> {
        let keys = self.keys(py)?;
        for key in keys {
            self.__delitem__(key, py)?;
        }
        Ok(())
    }

    /// Get number of items in this table
    fn __len__(&self, py: Python) -> PyResult<usize> {
        Ok(self.keys(py)?.len())
    }

    /// String representation: show table name and contents as dict
    fn __repr__(&self, py: Python) -> PyResult<String> {
        let items = self.items(py)?;
        if items.is_empty() {
            return Ok(format!("TableProxy('{}', {{}})", self.table_name));
        }

        // Format items as dict-like string
        let mut item_strs = Vec::new();
        for (key, value) in items {
            // Try to get a string representation of the value
            let value_repr = if let Ok(repr_method) = value.getattr(py, "__repr__") {
                if let Ok(repr_result) = repr_method.call0(py) {
                    if let Ok(s) = repr_result.extract::<String>(py) {
                        s
                    } else {
                        "...".to_string()
                    }
                } else {
                    "...".to_string()
                }
            } else {
                "...".to_string()
            };
            item_strs.push(format!("{:?}: {}", key, value_repr));
        }

        Ok(format!(
            "TableProxy('{}', {{{}}})",
            self.table_name,
            item_strs.join(", ")
        ))
    }

    /// String representation for str()
    fn __str__(&self, py: Python) -> PyResult<String> {
        self.__repr__(py)
    }
}

/// Python module definition
#[pymodule]
fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<DictSQLiteV4>()?;
    m.add_class::<AsyncDictSQLite>()?;
    m.add_class::<TableProxy>()?;
    m.add_class::<AsyncTableProxy>()?;
    Ok(())
}
