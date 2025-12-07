//! # キャッシュモジュール - 高性能ハイブリッドキャッシュ
//!
//! このモジュールは、LRUエビクション付きの高性能キャッシュを提供します。
//! DashMapを使用したロックフリーの並行アクセスをサポートします。
//!
//! ## 特徴
//! - ロックフリーの並行読み書き
//! - LRU（Least Recently Used）エビクション
//! - アクセスカウントベースのキャッシュ管理

use dashmap::DashMap;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;

/// 高性能ハイブリッドキャッシュ（LRUエビクション付き）
///
/// DashMapを使用したロックフリーの並行アクセスをサポートし、
/// LRUエビクションによる自動的なメモリ管理を提供します。
///
/// # 使用例
/// ```rust,ignore
/// let cache = HybridCache::new(1000);
/// cache.set("key".to_string(), vec![1, 2, 3]);
/// let value = cache.get("key");
/// ```
pub struct HybridCache {
    /// ロックフリー並行ハッシュマップ
    cache: Arc<DashMap<String, CacheEntry>>,

    /// 最大キャパシティ（エントリ数）
    capacity: usize,

    /// アクセスカウンター（LRU追跡用）
    /// Atomicを使用してロックフリーでインクリメント
    access_counter: Arc<AtomicU64>,
}

/// キャッシュエントリ
///
/// 値とアクセスメタデータを保持する構造体
#[derive(Clone)]
struct CacheEntry {
    /// 保存されている値
    value: Vec<u8>,
    /// 最終アクセス時刻（access_counterの値）
    last_access: u64,
    /// アクセス回数
    access_count: u64,
}

impl HybridCache {
    /// 新しいハイブリッドキャッシュを作成
    ///
    /// # 引数
    /// * `capacity` - 最大キャパシティ（エントリ数）
    ///
    /// # 戻り値
    /// 新しいHybridCacheインスタンス
    pub fn new(capacity: usize) -> Self {
        HybridCache {
            cache: Arc::new(DashMap::with_capacity(capacity)),
            capacity,
            access_counter: Arc::new(AtomicU64::new(0)),
        }
    }

    /// 値を取得（ロックフリー読み取り）
    ///
    /// アクセス時にメタデータを更新してLRU追跡を行います。
    ///
    /// # 引数
    /// * `key` - 取得するキー
    ///
    /// # 戻り値
    /// - `Some(Vec<u8>)`: 値が見つかった場合
    /// - `None`: キーが存在しない場合
    pub fn get(&self, key: &str) -> Option<Vec<u8>> {
        self.cache.get_mut(key).map(|mut entry| {
            // アクセス時刻を更新（Atomic操作でスレッドセーフ）
            let access_time = self.access_counter.fetch_add(1, Ordering::Relaxed);
            entry.last_access = access_time;
            entry.access_count += 1;
            entry.value.clone()
        })
    }

    /// 値を設定（ロックフリー書き込み）
    ///
    /// キャパシティを超えた場合は自動的にLRUエントリを削除します。
    ///
    /// # 引数
    /// * `key` - 設定するキー
    /// * `value` - 設定する値
    pub fn set(&self, key: String, value: Vec<u8>) {
        let access_time = self.access_counter.fetch_add(1, Ordering::Relaxed);
        let entry = CacheEntry {
            value,
            last_access: access_time,
            access_count: 1,
        };

        self.cache.insert(key, entry);

        // キャパシティを超えた場合はエビクション
        if self.cache.len() > self.capacity {
            self.evict_lru();
        }
    }

    /// 最も長く使われていないエントリを削除（LRUエビクション）
    ///
    /// 全エントリをスキャンして最も古いアクセス時刻を持つエントリを特定し、
    /// 削除します。O(n)の計算量。
    fn evict_lru(&self) {
        let mut oldest_key: Option<String> = None;
        let mut oldest_access: u64 = u64::MAX;

        // LRUエントリを検索
        for entry in self.cache.iter() {
            if entry.value().last_access < oldest_access {
                oldest_access = entry.value().last_access;
                oldest_key = Some(entry.key().clone());
            }
        }

        // 最も古いエントリを削除
        if let Some(key) = oldest_key {
            self.cache.remove(&key);
        }
    }

    /// エントリを削除
    ///
    /// # 引数
    /// * `key` - 削除するキー
    ///
    /// # 戻り値
    /// - `Some(Vec<u8>)`: 削除された値
    /// - `None`: キーが存在しなかった場合
    pub fn remove(&self, key: &str) -> Option<Vec<u8>> {
        self.cache.remove(key).map(|(_, entry)| entry.value)
    }

    /// キャッシュをクリア
    ///
    /// 全エントリを削除します。
    pub fn clear(&self) {
        self.cache.clear();
    }

    /// キャッシュサイズを取得
    ///
    /// # 戻り値
    /// 現在のエントリ数
    pub fn len(&self) -> usize {
        self.cache.len()
    }

    /// キャッシュが空かどうかを確認
    ///
    /// # 戻り値
    /// キャッシュが空の場合true
    pub fn is_empty(&self) -> bool {
        self.cache.is_empty()
    }
}
