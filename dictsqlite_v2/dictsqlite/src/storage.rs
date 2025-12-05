//! # ストレージモジュール - SQLiteバックエンドの管理
//!
//! このモジュールは、DictSQLiteのCold/Warm tierを管理する
//! StorageEngineを提供します。
//!
//! ## アーキテクチャ
//! - **Cold Tier**: SQLiteデータベース（永続化）
//! - **Warm Tier**: インメモリキャッシュ（頻繁にアクセスされるデータ）
//!
//! ## 最適化
//! - WALモードによる高速書き込み
//! - 準備済みステートメントのキャッシング
//! - バルクインサート用のトランザクション最適化

use anyhow::Result;
use rusqlite::{params, Connection};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};

use crate::{Config, TableMode};

/// メモリtierの種類
///
/// DictSQLiteの3層アーキテクチャを表す列挙型。
/// データは使用頻度に応じてtier間を移動します。
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MemoryTier {
    /// Hot tier: ロックフリー並行ハッシュマップ（インメモリ、最速）
    ///
    /// 最もアクセス頻度が高いデータを保持。
    /// DashMapによるロックフリーアクセスで100M+ ops/secを実現。
    Hot,

    /// Warm tier: メモリマップドファイル（高速、永続）
    ///
    /// 中程度のアクセス頻度のデータを保持。
    /// Hot tierから退避されたデータの一時的なキャッシュ。
    Warm,

    /// Cold tier: SQLiteディスクストレージ（永続、低速）
    ///
    /// 永続化が必要なすべてのデータの最終保存先。
    /// WALモードにより高速な書き込みを実現。
    Cold,
}

/// ストレージエンジン - Warm/Cold tierの管理
///
/// SQLiteデータベースへのアクセスを管理し、
/// Warm tierキャッシュによる読み取り高速化を提供します。
///
/// # スレッドセーフティ
/// 内部のConnectionとキャッシュはMutexで保護されているため、
/// 複数スレッドから安全にアクセス可能です。
pub struct StorageEngine {
    /// Cold tier用のSQLite接続（Mutexでスレッドセーフ化）
    cold_conn: Arc<Mutex<Connection>>,

    /// Warm tier: 頻繁にアクセスされるデータのインメモリキャッシュ
    warm_cache: Arc<Mutex<HashMap<String, Vec<u8>>>>,

    /// 設定
    config: Config,

    /// データベースパス
    #[allow(dead_code)]
    db_path: String,
}

impl StorageEngine {
    /// 新しいストレージエンジンを作成
    ///
    /// SQLiteデータベースを開き、パフォーマンス最適化のための
    /// PRAGMAを設定し、必要なテーブルとインデックスを作成します。
    ///
    /// # 引数
    /// * `db_path` - SQLiteデータベースファイルのパス
    /// * `config` - DictSQLiteの設定
    ///
    /// # 戻り値
    /// - `Ok(StorageEngine)`: 初期化されたストレージエンジン
    /// - `Err(...)`: データベースのオープンまたは初期化に失敗
    ///
    /// # SQLite最適化設定
    /// - `WAL`: Write-Ahead Loggingで並行読み取りを高速化
    /// - `synchronous=NORMAL`: 書き込みパフォーマンスと安全性のバランス
    /// - `cache_size=-64000`: 64MBのページキャッシュ
    /// - `temp_store=MEMORY`: 一時テーブルをメモリに保持
    /// - `mmap_size=30GB`: メモリマッピングで大規模データアクセスを高速化
    pub fn new(db_path: &str, config: &Config) -> Result<Self> {
        let cold_conn = Connection::open(db_path)?;

        // SQLiteのパフォーマンス最適化
        // これらのPRAGMAは読み書きの速度を大幅に向上させます
        cold_conn.execute_batch(
            "
            PRAGMA journal_mode=WAL;
            PRAGMA synchronous=NORMAL;
            PRAGMA cache_size=-64000;
            PRAGMA temp_store=MEMORY;
            PRAGMA mmap_size=30000000000;
            PRAGMA page_size=4096;
            PRAGMA auto_vacuum=INCREMENTAL;
        ",
        )?;

        // Key-Valueストアテーブルの作成
        // tier: データがどのtierに属するか（0=Hot, 1=Warm, 2=Cold）
        // access_count: アクセス回数（プロモーション判定用）
        // last_access: 最終アクセス時刻（LRU判定用）
        cold_conn.execute(
            "CREATE TABLE IF NOT EXISTS kv_store (
                key TEXT PRIMARY KEY,
                value BLOB NOT NULL,
                tier INTEGER DEFAULT 2,
                access_count INTEGER DEFAULT 0,
                last_access INTEGER DEFAULT 0
            )",
            [],
        )?;

        // アクセスパターンに基づくtier判定用のインデックス
        // 頻繁にアクセスされるデータを効率的に特定するため
        cold_conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_access 
             ON kv_store(access_count DESC, last_access DESC)",
            [],
        )?;

        // Warm tierキャッシュの初期化
        // warm_tier_sizeをKBで割って概算のエントリ数とする
        let warm_cache = Arc::new(Mutex::new(HashMap::with_capacity(
            config.warm_tier_size / 1024,
        )));

        Ok(StorageEngine {
            cold_conn: Arc::new(Mutex::new(cold_conn)),
            warm_cache,
            config: config.clone(),
            db_path: db_path.to_string(),
        })
    }

    /// Warm tierまたはCold tierから値を取得
    ///
    /// 最初にWarm tier（インメモリキャッシュ）を検索し、
    /// 見つからない場合はCold tier（SQLite）を検索します。
    /// Cold tierで見つかった場合、アクセス頻度に応じて
    /// Warm tierへのプロモーションが行われます。
    ///
    /// # 引数
    /// * `key` - 取得するキー
    ///
    /// # 戻り値
    /// - `Ok(Some(Vec<u8>))`: 値が見つかった場合
    /// - `Ok(None)`: キーが存在しない場合
    /// - `Err(...)`: データベースエラー
    pub fn get(&self, key: &str) -> Result<Option<Vec<u8>>> {
        // まずWarm tierをチェック（最速）
        {
            let warm = self.warm_cache.lock().unwrap();
            if let Some(value) = warm.get(key) {
                return Ok(Some(value.clone()));
            }
        }

        // Cold tier（SQLite）をチェック
        let value_opt = {
            let conn = self.cold_conn.lock().unwrap();
            // 準備済みステートメントをキャッシュしてパフォーマンス向上
            let mut stmt = conn.prepare_cached("SELECT value FROM kv_store WHERE key = ?1")?;

            let result = stmt.query_row(params![key], |row| row.get::<_, Vec<u8>>(0));

            match result {
                Ok(value) => Some(value),
                Err(rusqlite::Error::QueryReturnedNoRows) => None,
                Err(e) => return Err(e.into()),
            }
        };

        if let Some(value) = value_opt {
            // アクセスカウントを更新（tier判定用）
            {
                let conn = self.cold_conn.lock().unwrap();
                conn.execute(
                    "UPDATE kv_store SET access_count = access_count + 1, 
                     last_access = strftime('%s', 'now') WHERE key = ?1",
                    params![key],
                )?;
            }

            // 頻繁にアクセスされる場合はWarm tierにプロモート
            self.promote_to_warm(key, &value)?;

            Ok(Some(value))
        } else {
            Ok(None)
        }
    }

    /// Cold tierに値を設定
    ///
    /// INSERT OR REPLACEを使用して、キーが存在する場合は上書き、
    /// 存在しない場合は新規挿入を行います。
    ///
    /// # 引数
    /// * `key` - 設定するキー
    /// * `value` - 設定する値（バイト列）
    ///
    /// # 戻り値
    /// - `Ok(())`: 成功
    /// - `Err(...)`: SQLiteエラー
    pub fn set(&mut self, key: &str, value: &[u8]) -> Result<()> {
        let conn = self.cold_conn.lock().unwrap();
        conn.execute(
            "INSERT OR REPLACE INTO kv_store (key, value, tier, last_access) 
             VALUES (?1, ?2, 2, strftime('%s', 'now'))",
            params![key, value],
        )?;
        Ok(())
    }

    /// Cold tierへのバルクインサート（トランザクション最適化版）
    ///
    /// 複数のアイテムを単一トランザクションで挿入することで、
    /// 個別挿入と比較して大幅なパフォーマンス向上を実現します。
    ///
    /// # 引数
    /// * `items` - 挿入するキー・値のペア
    ///
    /// # 戻り値
    /// - `Ok(())`: 成功
    /// - `Err(...)`: トランザクションまたはSQLiteエラー
    pub fn bulk_insert(&mut self, items: &HashMap<String, Vec<u8>>) -> Result<()> {
        let mut conn = self.cold_conn.lock().unwrap();
        // トランザクションを開始
        let tx = conn.transaction()?;

        {
            // 準備済みステートメントを再利用
            let mut stmt = tx.prepare_cached(
                "INSERT OR REPLACE INTO kv_store (key, value, tier, last_access) 
                 VALUES (?1, ?2, 2, strftime('%s', 'now'))",
            )?;

            for (key, value) in items {
                stmt.execute(params![key, value])?;
            }
        }

        // コミットで一括書き込み
        tx.commit()?;
        Ok(())
    }

    /// アクセスパターンに基づいてWarm tierにプロモート
    ///
    /// Cold tierからアクセスされたデータをWarm tierにコピーすることで、
    /// 次回以降のアクセスを高速化します。
    /// Warm tierのサイズ制限を超える場合はプロモートしません。
    ///
    /// # 引数
    /// * `key` - プロモートするキー
    /// * `value` - 値（バイト列）
    fn promote_to_warm(&self, key: &str, value: &[u8]) -> Result<()> {
        let mut warm = self.warm_cache.lock().unwrap();

        // Warm tierのサイズ制限をチェック
        let current_size: usize = warm.values().map(|v| v.len()).sum();
        if current_size + value.len() < self.config.warm_tier_size {
            warm.insert(key.to_string(), value.to_vec());
        }

        Ok(())
    }

    /// Warm tierの全アイテムをCold tierに退避
    ///
    /// Warm tierのデータをSQLiteに書き込み、メモリを解放します。
    /// シャットダウン時やメモリ逼迫時に呼び出されます。
    ///
    /// # 戻り値
    /// - `Ok(usize)`: 退避したアイテム数
    /// - `Err(...)`: SQLiteエラー
    pub fn evict_warm_tier(&mut self) -> Result<usize> {
        // Warm tierから全アイテムを取得
        let items = {
            let mut warm = self.warm_cache.lock().unwrap();
            let items: HashMap<String, Vec<u8>> = warm.drain().collect();
            items
        };

        let count = items.len();

        // 全アイテムをCold tierに書き込み
        if !items.is_empty() {
            let conn = self.cold_conn.lock().unwrap();
            for (key, value) in items.iter() {
                conn.execute(
                    "INSERT OR REPLACE INTO kv_store (key, value, tier, last_access) 
                     VALUES (?1, ?2, 2, strftime('%s', 'now'))",
                    params![key, value],
                )?;
            }
        }

        Ok(count)
    }

    /// Cold tierから全キーを取得
    ///
    /// # 戻り値
    /// - `Ok(Vec<String>)`: 全キーのリスト
    /// - `Err(...)`: SQLiteエラー
    pub fn keys(&self) -> Result<Vec<String>> {
        let conn = self.cold_conn.lock().unwrap();
        let mut stmt = conn.prepare("SELECT key FROM kv_store")?;
        let keys: Result<Vec<String>, _> = stmt.query_map([], |row| row.get(0))?.collect();
        keys.map_err(|e| e.into())
    }

    /// 全tierからキーを削除
    ///
    /// Warm tierとCold tierの両方からキーを削除します。
    ///
    /// # 引数
    /// * `key` - 削除するキー
    ///
    /// # 戻り値
    /// - `Ok(())`: 成功
    /// - `Err(...)`: SQLiteエラー
    pub fn delete(&mut self, key: &str) -> Result<()> {
        // Warm tierから削除
        self.warm_cache.lock().unwrap().remove(key);

        // Cold tierから削除
        let conn = self.cold_conn.lock().unwrap();
        conn.execute("DELETE FROM kv_store WHERE key = ?1", params![key])?;

        Ok(())
    }

    /// 全tierをクリア
    ///
    /// Warm tierとCold tierの両方の全データを削除します。
    /// この操作は取り消せません。
    ///
    /// # 戻り値
    /// - `Ok(())`: 成功
    /// - `Err(...)`: SQLiteエラー
    pub fn clear(&mut self) -> Result<()> {
        self.warm_cache.lock().unwrap().clear();
        let conn = self.cold_conn.lock().unwrap();
        conn.execute("DELETE FROM kv_store", [])?;
        Ok(())
    }

    /// ストレージ統計を取得
    ///
    /// Warm tierとCold tierの現在の状態を取得します。
    /// パフォーマンス監視やデバッグに使用できます。
    ///
    /// # 戻り値
    /// StorageStats構造体（エントリ数、バイトサイズなど）
    pub fn stats(&self) -> StorageStats {
        let warm = self.warm_cache.lock().unwrap();
        let warm_size: usize = warm.values().map(|v| v.len()).sum();

        let conn = self.cold_conn.lock().unwrap();
        let cold_tier_entries = conn
            .query_row("SELECT COUNT(*) FROM kv_store", [], |row| row.get(0))
            .unwrap_or(0);

        StorageStats {
            warm_tier_entries: warm.len(),
            warm_tier_bytes: warm_size,
            cold_tier_entries,
        }
    }

    // ========== 分離テーブルモード用のメソッド ==========

    /// テーブル名をサニタイズして安全なSQL識別子にする
    ///
    /// # 引数
    /// * `table_name` - テーブル名
    ///
    /// # 戻り値
    /// サニタイズされたテーブル名（アルファベット、数字、アンダースコアのみ）
    fn sanitize_table_name(table_name: &str) -> String {
        // 安全なテーブル名に変換（アルファベット、数字、アンダースコアのみ許可）
        let sanitized: String = table_name
            .chars()
            .filter(|c| c.is_alphanumeric() || *c == '_')
            .collect();
        
        // 空の場合はデフォルトテーブル名を使用
        if sanitized.is_empty() {
            "main".to_string()
        } else {
            format!("kv_{}", sanitized)
        }
    }

    /// 指定されたテーブルが存在することを確認し、存在しなければ作成
    ///
    /// # 引数
    /// * `table_name` - テーブル名
    ///
    /// # 戻り値
    /// - `Ok(())`: 成功
    /// - `Err(...)`: SQLiteエラー
    pub fn ensure_table_exists(&self, table_name: &str) -> Result<()> {
        let safe_table_name = Self::sanitize_table_name(table_name);
        let conn = self.cold_conn.lock().unwrap();
        
        // テーブルを作成（存在しない場合のみ）
        conn.execute(
            &format!(
                "CREATE TABLE IF NOT EXISTS {} (
                    key TEXT PRIMARY KEY,
                    value BLOB NOT NULL,
                    tier INTEGER DEFAULT 2,
                    access_count INTEGER DEFAULT 0,
                    last_access INTEGER DEFAULT 0
                )",
                safe_table_name
            ),
            [],
        )?;

        // インデックスを作成
        conn.execute(
            &format!(
                "CREATE INDEX IF NOT EXISTS idx_{}_access 
                 ON {}(access_count DESC, last_access DESC)",
                safe_table_name, safe_table_name
            ),
            [],
        )?;

        Ok(())
    }

    /// 指定されたテーブルから値を取得（分離モード用）
    ///
    /// # 引数
    /// * `table_name` - テーブル名
    /// * `key` - キー
    ///
    /// # 戻り値
    /// - `Ok(Some(Vec<u8>))`: 値が見つかった場合
    /// - `Ok(None)`: キーが存在しない場合
    /// - `Err(...)`: データベースエラー
    pub fn get_with_table(&self, table_name: &str, key: &str) -> Result<Option<Vec<u8>>> {
        // まずWarm tierをチェック（テーブル名:キー形式でキャッシュ）
        let cache_key = format!("{}:{}", table_name, key);
        {
            let warm = self.warm_cache.lock().unwrap();
            if let Some(value) = warm.get(&cache_key) {
                return Ok(Some(value.clone()));
            }
        }

        let safe_table_name = Self::sanitize_table_name(table_name);
        
        // テーブルが存在することを確認
        self.ensure_table_exists(table_name)?;

        // Cold tier（SQLite）をチェック
        let value_opt = {
            let conn = self.cold_conn.lock().unwrap();
            let query = format!("SELECT value FROM {} WHERE key = ?1", safe_table_name);
            let mut stmt = conn.prepare_cached(&query)?;

            let result = stmt.query_row(params![key], |row| row.get::<_, Vec<u8>>(0));

            match result {
                Ok(value) => Some(value),
                Err(rusqlite::Error::QueryReturnedNoRows) => None,
                Err(e) => return Err(e.into()),
            }
        };

        if let Some(value) = value_opt {
            // アクセスカウントを更新
            {
                let conn = self.cold_conn.lock().unwrap();
                let update_query = format!(
                    "UPDATE {} SET access_count = access_count + 1, 
                     last_access = strftime('%s', 'now') WHERE key = ?1",
                    safe_table_name
                );
                conn.execute(&update_query, params![key])?;
            }

            // Warm tierにプロモート（テーブル名:キー形式でキャッシュ）
            self.promote_to_warm(&cache_key, &value)?;

            Ok(Some(value))
        } else {
            Ok(None)
        }
    }

    /// 指定されたテーブルに値を設定（分離モード用）
    ///
    /// # 引数
    /// * `table_name` - テーブル名
    /// * `key` - キー
    /// * `value` - 値
    ///
    /// # 戻り値
    /// - `Ok(())`: 成功
    /// - `Err(...)`: SQLiteエラー
    pub fn set_with_table(&mut self, table_name: &str, key: &str, value: &[u8]) -> Result<()> {
        let safe_table_name = Self::sanitize_table_name(table_name);
        
        // テーブルが存在することを確認
        self.ensure_table_exists(table_name)?;

        let conn = self.cold_conn.lock().unwrap();
        let insert_query = format!(
            "INSERT OR REPLACE INTO {} (key, value, tier, last_access) 
             VALUES (?1, ?2, 2, strftime('%s', 'now'))",
            safe_table_name
        );
        conn.execute(&insert_query, params![key, value])?;
        Ok(())
    }

    /// 指定されたテーブルからキーを削除（分離モード用）
    ///
    /// # 引数
    /// * `table_name` - テーブル名
    /// * `key` - キー
    ///
    /// # 戻り値
    /// - `Ok(())`: 成功
    /// - `Err(...)`: SQLiteエラー
    pub fn delete_with_table(&mut self, table_name: &str, key: &str) -> Result<()> {
        // Warm tierから削除
        let cache_key = format!("{}:{}", table_name, key);
        self.warm_cache.lock().unwrap().remove(&cache_key);

        let safe_table_name = Self::sanitize_table_name(table_name);

        // Cold tierから削除
        let conn = self.cold_conn.lock().unwrap();
        let delete_query = format!("DELETE FROM {} WHERE key = ?1", safe_table_name);
        conn.execute(&delete_query, params![key])?;

        Ok(())
    }

    /// 指定されたテーブルの全キーを取得（分離モード用）
    ///
    /// # 引数
    /// * `table_name` - テーブル名
    ///
    /// # 戻り値
    /// - `Ok(Vec<String>)`: キーのリスト
    /// - `Err(...)`: SQLiteエラー
    pub fn keys_with_table(&self, table_name: &str) -> Result<Vec<String>> {
        let safe_table_name = Self::sanitize_table_name(table_name);
        
        // テーブルが存在することを確認
        self.ensure_table_exists(table_name)?;

        let conn = self.cold_conn.lock().unwrap();
        let query = format!("SELECT key FROM {}", safe_table_name);
        let mut stmt = conn.prepare(&query)?;
        let keys: Result<Vec<String>, _> = stmt.query_map([], |row| row.get(0))?.collect();
        keys.map_err(|e| e.into())
    }

    /// 指定されたテーブルをクリア（分離モード用）
    ///
    /// # 引数
    /// * `table_name` - テーブル名
    ///
    /// # 戻り値
    /// - `Ok(())`: 成功
    /// - `Err(...)`: SQLiteエラー
    pub fn clear_table(&mut self, table_name: &str) -> Result<()> {
        // Warm tierから該当テーブルのエントリを削除
        let prefix = format!("{}:", table_name);
        {
            let mut warm = self.warm_cache.lock().unwrap();
            warm.retain(|k, _| !k.starts_with(&prefix));
        }

        let safe_table_name = Self::sanitize_table_name(table_name);

        // Cold tierからテーブルの全データを削除
        let conn = self.cold_conn.lock().unwrap();
        let delete_query = format!("DELETE FROM {}", safe_table_name);
        conn.execute(&delete_query, [])?;
        Ok(())
    }

    /// 存在する全テーブル名を取得（分離モード用）
    ///
    /// # 戻り値
    /// - `Ok(Vec<String>)`: テーブル名のリスト
    /// - `Err(...)`: SQLiteエラー
    pub fn list_tables(&self) -> Result<Vec<String>> {
        let conn = self.cold_conn.lock().unwrap();
        let mut stmt = conn.prepare(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'kv_%'"
        )?;
        
        let tables: Result<Vec<String>, _> = stmt
            .query_map([], |row| {
                let name: String = row.get(0)?;
                // kv_プレフィックスを除去して元のテーブル名を返す
                Ok(name.strip_prefix("kv_").unwrap_or(&name).to_string())
            })?
            .collect();
        
        tables.map_err(|e| e.into())
    }
}

/// ストレージ統計情報
///
/// Warm tierとCold tierの現在の状態を表す構造体。
/// モニタリングやデバッグに使用できます。
#[derive(Debug)]
pub struct StorageStats {
    /// Warm tierのエントリ数
    pub warm_tier_entries: usize,
    /// Warm tierの合計バイトサイズ
    pub warm_tier_bytes: usize,
    /// Cold tier（SQLite）のエントリ数
    pub cold_tier_entries: i64,
}
