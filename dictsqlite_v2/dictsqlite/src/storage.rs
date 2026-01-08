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
//! - コネクションプールによる並行アクセスの最適化
//! - v5.1: オプションのZstd圧縮

use anyhow::Result;
use dashmap::{DashMap, DashSet};
use r2d2::Pool;
use r2d2_sqlite::SqliteConnectionManager;
use rusqlite::params;
use std::collections::HashMap;
use std::sync::Arc;

use crate::Config;

// v5.1圧縮機能: マジックバイトで圧縮データを識別
// 非圧縮データとの後方互換性を維持
const ZSTD_MAGIC_BYTES: &[u8] = b"ZSTD";

/// データを圧縮（圧縮有効時のみ）
/// マジックバイトをプレフィックスとして付与し、後方互換性を維持
fn compress_data(data: &[u8], config: &Config) -> Vec<u8> {
    if !config.enable_compression {
        return data.to_vec();
    }

    // 小さいデータ（128バイト未満）は圧縮しない（オーバーヘッドが大きい）
    if data.len() < 128 {
        return data.to_vec();
    }

    match zstd::encode_all(data, config.compression_level) {
        Ok(compressed) => {
            // 圧縮が効果的な場合のみ使用（オリジナルより小さい場合）
            if compressed.len() < data.len() {
                let mut result = Vec::with_capacity(ZSTD_MAGIC_BYTES.len() + compressed.len());
                result.extend_from_slice(ZSTD_MAGIC_BYTES);
                result.extend_from_slice(&compressed);
                result
            } else {
                data.to_vec()
            }
        }
        Err(_) => data.to_vec(), // 圧縮失敗時は非圧縮で保存
    }
}

/// データを展開（圧縮されている場合のみ）
/// マジックバイトをチェックして圧縮データを識別
fn decompress_data(data: &[u8]) -> Vec<u8> {
    // マジックバイトをチェック
    if data.len() > ZSTD_MAGIC_BYTES.len() && data.starts_with(ZSTD_MAGIC_BYTES) {
        let compressed = &data[ZSTD_MAGIC_BYTES.len()..];
        match zstd::decode_all(compressed) {
            Ok(decompressed) => decompressed,
            Err(_) => data.to_vec(), // 展開失敗時は元データ返却
        }
    } else {
        data.to_vec() // 非圧縮データはそのまま返却
    }
}

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
/// 内部のコネクションプールとキャッシュはスレッドセーフであり、
/// 複数スレッドから安全に並行アクセス可能です。
///
/// # コネクションプール
/// r2d2ライブラリを使用したコネクションプールにより、
/// 複数の並行リクエストを効率的に処理します。
pub struct StorageEngine {
    /// Cold tier用のSQLiteコネクションプール
    cold_pool: Pool<SqliteConnectionManager>,

    /// Warm tier: 頻繁にアクセスされるデータのインメモリキャッシュ
    /// v5最適化: DashMapによるロックフリーアクセス
    warm_cache: Arc<DashMap<String, Vec<u8>>>,

    /// アクセスカウントバッファ（v5最適化）
    /// getでの書き込みを回避し、バッチでフラッシュする
    access_count_buffer: Arc<DashMap<String, u64>>,

    /// 既知のテーブルキャッシュ（v5最適化）
    /// CREATE TABLE IF NOT EXISTSの重複実行を防ぐ
    known_tables: Arc<DashSet<String>>,

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
    ///
    /// # コネクションプール
    /// - プールサイズ: ユーザー指定可能（デフォルト: 32）
    /// - v7.0: min_idle, idle_timeout, connection_timeout追加
    pub fn new(db_path: &str, config: &Config) -> Result<Self> {
        // コネクションプールマネージャーの作成
        let manager = SqliteConnectionManager::file(db_path).with_init(|conn| {
            // SQLiteのパフォーマンス最適化
            // v7.0: APSW同等性能を目指した最適化PRAGMA
            //
            // WALモード: 読み書き並行性を最大化
            // synchronous=NORMAL: データ安全性とパフォーマンスのバランス
            // busy_timeout: ロック競合時の待機（エラー削減）
            // read_uncommitted: 読み取りロックを取得しない（WAL前提）
            conn.execute_batch(
                "
                    PRAGMA journal_mode=WAL;
                    PRAGMA synchronous=NORMAL;
                    PRAGMA cache_size=-128000;
                    PRAGMA temp_store=MEMORY;
                    PRAGMA mmap_size=30000000000;
                    PRAGMA page_size=4096;
                    PRAGMA wal_autocheckpoint=10000;
                    PRAGMA busy_timeout=5000;
                    PRAGMA read_uncommitted=1;
                    PRAGMA journal_size_limit=67108864;
                ",
            )?;
            Ok(())
        });

        // v7.0: コネクションプールの最適化設定
        // max_size=32: 高負荷環境で十分な並行性（WAL推奨上限）
        // min_idle: 最小接続数（pool_sizeに応じて調整、max_sizeを超えないように）
        // idle_timeout=30s: アイドル接続を30秒後に回収（メモリ効率）
        // connection_timeout=5s: 接続取得タイムアウト（デッドロック防止）
        let pool_size = config.pool_size;
        // min_idleはpool_sizeを超えてはならない（r2d2の制約）
        let min_idle = std::cmp::min(2, pool_size) as u32;

        let cold_pool = Pool::builder()
            .max_size(pool_size as u32)
            .min_idle(Some(min_idle))
            .idle_timeout(Some(std::time::Duration::from_secs(30)))
            .connection_timeout(std::time::Duration::from_secs(5))
            .build(manager)?;

        // 初期接続を取得してテーブルとインデックスを作成
        let conn = cold_pool.get()?;

        // Key-Valueストアテーブルの作成
        // tier: データがどのtierに属するか（0=Hot, 1=Warm, 2=Cold）
        // access_count: アクセス回数（プロモーション判定用）
        // last_access: 最終アクセス時刻（LRU判定用）
        conn.execute(
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
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_access 
             ON kv_store(access_count DESC, last_access DESC)",
            [],
        )?;

        // 接続を解放（プールに返却）
        drop(conn);

        // Warm tierキャッシュの初期化（v5最適化: DashMap）
        let warm_cache = Arc::new(DashMap::with_capacity(config.warm_tier_size / 1024));

        // v5最適化: アクセスカウントバッファ
        let access_count_buffer = Arc::new(DashMap::new());

        // v5最適化: 既知テーブルキャッシュ
        let known_tables = Arc::new(DashSet::new());
        // デフォルトテーブルを既知として登録
        known_tables.insert("kv_store".to_string());

        Ok(StorageEngine {
            cold_pool,
            warm_cache,
            access_count_buffer,
            known_tables,
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
        // まずWarm tierをチェック（最速、v5最適化: ロックフリー）
        if let Some(value) = self.warm_cache.get(key) {
            return Ok(Some(value.clone()));
        }

        // Cold tier（SQLite）をチェック - プールから接続を取得
        let value_opt = {
            let conn = self.cold_pool.get()?;
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
            // v5.1: 圧縮データを透過的に展開
            let decompressed = decompress_data(&value);

            // v5最適化: アクセスカウントをバッファに記録（DB書き込みなし）
            self.access_count_buffer
                .entry(key.to_string())
                .and_modify(|count| *count += 1)
                .or_insert(1);

            // 頻繁にアクセスされる場合はWarm tierにプロモート（展開済みデータをキャッシュ）
            self.promote_to_warm(key, &decompressed)?;

            Ok(Some(decompressed))
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
    /// v5最適化: &selfに変更（コネクションプールは内部でスレッドセーフ）
    /// v5.1: オプションでZstd圧縮を適用
    pub fn set(&self, key: &str, value: &[u8]) -> Result<()> {
        // v5.1: 圧縮が有効な場合はデータを圧縮
        let data_to_store = compress_data(value, &self.config);

        let conn = self.cold_pool.get()?;
        conn.execute(
            "INSERT OR REPLACE INTO kv_store (key, value, tier, last_access) 
             VALUES (?1, ?2, 2, strftime('%s', 'now'))",
            params![key, data_to_store],
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
    /// v5最適化: &selfに変更
    pub fn bulk_insert(&self, items: &HashMap<String, Vec<u8>>) -> Result<()> {
        let mut conn = self.cold_pool.get()?;
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
    /// v5最適化: DashMapを使用（ロックフリー）
    fn promote_to_warm(&self, key: &str, value: &[u8]) -> Result<()> {
        // Warm tierのサイズ制限をチェック
        let current_size: usize = self.warm_cache.iter().map(|r| r.value().len()).sum();
        if current_size + value.len() < self.config.warm_tier_size {
            self.warm_cache.insert(key.to_string(), value.to_vec());
        }

        Ok(())
    }

    /// Warm tierの全アイテムをCold tierに退避
    ///
    /// Warm tierのデータをSQLiteに書き込み、メモリを解放します。
    /// シャットダウン時やメモリ逼迫時に呼び出されます。
    ///
    /// # v4.2.1最適化
    /// bulk_insert()を使用して高速化
    ///
    /// # 戻り値
    /// - `Ok(usize)`: 退避したアイテム数
    /// - `Err(...)`: SQLiteエラー
    /// v5最適化: &selfに変更、DashMapを使用
    pub fn evict_warm_tier(&self) -> Result<usize> {
        // Warm tierから全アイテムを取得
        let items: HashMap<String, Vec<u8>> = self
            .warm_cache
            .iter()
            .map(|r| (r.key().clone(), r.value().clone()))
            .collect();

        let count = items.len();

        // クリア
        self.warm_cache.clear();

        // v4.2.1最適化: bulk_insert()で一括書き込み（単一トランザクション）
        if !items.is_empty() {
            self.bulk_insert(&items)?;
        }

        Ok(count)
    }

    /// v5最適化: アクセスカウントバッファをDBにフラッシュ
    ///
    /// バッファリングされたアクセスカウントをまとめてDBに書き込みます。
    /// close時または定期的に呼び出されます。
    ///
    /// # 戻り値
    /// - `Ok(usize)`: フラッシュしたエントリ数
    /// - `Err(...)`: SQLiteエラー
    pub fn flush_access_counts(&self) -> Result<usize> {
        // バッファが空なら何もしない
        if self.access_count_buffer.is_empty() {
            return Ok(0);
        }

        // バッファからデータを取得してクリア
        let counts: Vec<(String, u64)> = self
            .access_count_buffer
            .iter()
            .map(|r| (r.key().clone(), *r.value()))
            .collect();
        self.access_count_buffer.clear();

        let count = counts.len();

        // トランザクションで一抬更新
        let mut conn = self.cold_pool.get()?;
        let tx = conn.transaction()?;

        {
            let mut stmt = tx.prepare_cached(
                "UPDATE kv_store SET access_count = access_count + ?1, 
                 last_access = strftime('%s', 'now') WHERE key = ?2",
            )?;

            for (key, increment) in counts {
                let _ = stmt.execute(params![increment, key]);
            }
        }

        tx.commit()?;
        Ok(count)
    }

    /// Cold tierから全キーを取得
    ///
    /// # 戻り値
    /// - `Ok(Vec<String>)`: 全キーのリスト
    /// - `Err(...)`: SQLiteエラー
    pub fn keys(&self) -> Result<Vec<String>> {
        let conn = self.cold_pool.get()?;
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
    /// v5最適化: &selfに変更、DashMapを使用
    pub fn delete(&self, key: &str) -> Result<()> {
        // Warm tierから削除
        self.warm_cache.remove(key);

        // Cold tierから削除
        let conn = self.cold_pool.get()?;
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
    /// v5最適化: &selfに変更、DashMapを使用
    pub fn clear(&self) -> Result<()> {
        self.warm_cache.clear();
        self.access_count_buffer.clear();
        let conn = self.cold_pool.get()?;
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
    /// v5最適化: DashMapを使用
    pub fn stats(&self) -> StorageStats {
        let warm_size: usize = self.warm_cache.iter().map(|r| r.value().len()).sum();

        let cold_tier_entries = if let Ok(conn) = self.cold_pool.get() {
            conn.query_row("SELECT COUNT(*) FROM kv_store", [], |row| row.get(0))
                .unwrap_or(0)
        } else {
            0
        };

        StorageStats {
            warm_tier_entries: self.warm_cache.len(),
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
        // kv_main を使用して他のテーブル名との一貫性を保つ
        if sanitized.is_empty() {
            "kv_main".to_string()
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
    /// v5最適化: テーブルキャッシュを使用
    pub fn ensure_table_exists(&self, table_name: &str) -> Result<()> {
        let safe_table_name = Self::sanitize_table_name(table_name);

        // v5最適化: 既知テーブルならSQLスキップ
        if self.known_tables.contains(&safe_table_name) {
            return Ok(());
        }

        let conn = self.cold_pool.get()?;

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

        // キャッシュに登録
        self.known_tables.insert(safe_table_name);

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
    /// v5最適化: DashMapを使用、アクセスカウントはバッファリング
    pub fn get_with_table(&self, table_name: &str, key: &str) -> Result<Option<Vec<u8>>> {
        // まずWarm tierをチェック（v5最適化: ロックフリー）
        let cache_key = format!("{}:{}", table_name, key);
        if let Some(value) = self.warm_cache.get(&cache_key) {
            return Ok(Some(value.clone()));
        }

        let safe_table_name = Self::sanitize_table_name(table_name);

        // テーブルが存在することを確認
        self.ensure_table_exists(table_name)?;

        // Cold tier（SQLite）をチェック
        let value_opt = {
            let conn = self.cold_pool.get()?;
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
            // v5最適化: アクセスカウントをバッファに記録（DB書き込みなし）
            self.access_count_buffer
                .entry(cache_key.clone())
                .and_modify(|count| *count += 1)
                .or_insert(1);

            // Warm tierにプロモート
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
    /// v5最適化: &selfに変更
    pub fn set_with_table(&self, table_name: &str, key: &str, value: &[u8]) -> Result<()> {
        let safe_table_name = Self::sanitize_table_name(table_name);

        // テーブルが存在することを確認
        self.ensure_table_exists(table_name)?;

        let conn = self.cold_pool.get()?;
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
    /// v5最適化: &selfに変更、DashMapを使用
    pub fn delete_with_table(&self, table_name: &str, key: &str) -> Result<()> {
        // Warm tierから削除
        let cache_key = format!("{}:{}", table_name, key);
        self.warm_cache.remove(&cache_key);

        let safe_table_name = Self::sanitize_table_name(table_name);

        // Cold tierから削除
        let conn = self.cold_pool.get()?;
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

        let conn = self.cold_pool.get()?;
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
    /// v5最適化: &selfに変更、DashMapを使用
    pub fn clear_table(&self, table_name: &str) -> Result<()> {
        // Warm tierから該当テーブルのエントリを削除
        let prefix = format!("{}:", table_name);
        self.warm_cache.retain(|k, _| !k.starts_with(&prefix));

        let safe_table_name = Self::sanitize_table_name(table_name);

        // Cold tierからテーブルの全データを削除
        let conn = self.cold_pool.get()?;
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
        let conn = self.cold_pool.get()?;
        let mut stmt =
            conn.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'kv_%'")?;

        let tables: Result<Vec<String>, _> = stmt
            .query_map([], |row| {
                let name: String = row.get(0)?;
                // kv_プレフィックスを除去して元のテーブル名を返す
                // プレフィックスがない場合はスキップ（セキュリティ対策）
                match name.strip_prefix("kv_") {
                    Some(table_name) => Ok(Some(table_name.to_string())),
                    None => Ok(None),
                }
            })?
            .filter_map(|r| r.transpose())
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
