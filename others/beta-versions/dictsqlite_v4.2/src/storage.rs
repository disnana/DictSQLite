use rusqlite::{Connection, params};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use anyhow::Result;

use crate::Config;

/// Memory tier types for hybrid storage
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MemoryTier {
    /// Hot tier: Lock-free concurrent hashmap (in-memory, fastest)
    Hot,
    /// Warm tier: Memory-mapped file (fast, persistent)
    Warm,
    /// Cold tier: SQLite on disk (persistent, slower)
    Cold,
}

/// Storage engine managing warm and cold tiers
pub struct StorageEngine {
    /// SQLite connection for cold tier (wrapped in Mutex for thread safety)
    cold_conn: Arc<Mutex<Connection>>,
    
    /// Warm tier: In-memory cache with eventual persistence
    warm_cache: Arc<Mutex<HashMap<String, Vec<u8>>>>,
    
    /// Configuration
    config: Config,
    
    /// Database path
    #[allow(dead_code)]
    db_path: String,
}

impl StorageEngine {
    /// Create new storage engine
    pub fn new(db_path: &str, config: &Config) -> Result<Self> {
        let cold_conn = Connection::open(db_path)?;
        
        // Optimize SQLite for performance
        cold_conn.execute_batch("
            PRAGMA journal_mode=WAL;
            PRAGMA synchronous=NORMAL;
            PRAGMA cache_size=-64000;
            PRAGMA temp_store=MEMORY;
            PRAGMA mmap_size=30000000000;
            PRAGMA page_size=4096;
            PRAGMA auto_vacuum=INCREMENTAL;
        ")?;
        
        // Create table if not exists
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
        
        // Create index on access patterns for tiering decisions
        cold_conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_access 
             ON kv_store(access_count DESC, last_access DESC)",
            [],
        )?;
        
        let warm_cache = Arc::new(Mutex::new(
            HashMap::with_capacity(config.warm_tier_size / 1024)
        ));
        
        Ok(StorageEngine {
            cold_conn: Arc::new(Mutex::new(cold_conn)),
            warm_cache,
            config: config.clone(),
            db_path: db_path.to_string(),
        })
    }
    
    /// Get value from warm or cold tier
    pub fn get(&self, key: &str) -> Result<Option<Vec<u8>>> {
        // Check warm tier first
        {
            let warm = self.warm_cache.lock().unwrap();
            if let Some(value) = warm.get(key) {
                return Ok(Some(value.clone()));
            }
        }
        
        // Check cold tier (SQLite)
        let value_opt = {
            let conn = self.cold_conn.lock().unwrap();
            let mut stmt = conn.prepare_cached(
                "SELECT value FROM kv_store WHERE key = ?1"
            )?;
            
            let result = stmt.query_row(params![key], |row| {
                row.get::<_, Vec<u8>>(0)
            });
            
            match result {
                Ok(value) => Some(value),
                Err(rusqlite::Error::QueryReturnedNoRows) => None,
                Err(e) => return Err(e.into()),
            }
        };
        
        if let Some(value) = value_opt {
            // Update access count for tiering
            {
                let conn = self.cold_conn.lock().unwrap();
                conn.execute(
                    "UPDATE kv_store SET access_count = access_count + 1, 
                     last_access = strftime('%s', 'now') WHERE key = ?1",
                    params![key],
                )?;
            }
            
            // Promote to warm tier if frequently accessed
            self.promote_to_warm(key, &value)?;
            
            Ok(Some(value))
        } else {
            Ok(None)
        }
    }
    
    /// Set value in cold tier
    pub fn set(&mut self, key: &str, value: &[u8]) -> Result<()> {
        let conn = self.cold_conn.lock().unwrap();
        conn.execute(
            "INSERT OR REPLACE INTO kv_store (key, value, tier, last_access) 
             VALUES (?1, ?2, 2, strftime('%s', 'now'))",
            params![key, value],
        )?;
        Ok(())
    }
    
    /// Bulk insert to cold tier (optimized transaction)
    pub fn bulk_insert(&mut self, items: &HashMap<String, Vec<u8>>) -> Result<()> {
        let mut conn = self.cold_conn.lock().unwrap();
        let tx = conn.transaction()?;
        
        {
            let mut stmt = tx.prepare_cached(
                "INSERT OR REPLACE INTO kv_store (key, value, tier, last_access) 
                 VALUES (?1, ?2, 2, strftime('%s', 'now'))"
            )?;
            
            for (key, value) in items {
                stmt.execute(params![key, value])?;
            }
        }
        
        tx.commit()?;
        Ok(())
    }
    
    /// Promote key to warm tier based on access patterns
    fn promote_to_warm(&self, key: &str, value: &[u8]) -> Result<()> {
        let mut warm = self.warm_cache.lock().unwrap();
        
        // Check warm tier size limit
        let current_size: usize = warm.values().map(|v| v.len()).sum();
        if current_size + value.len() < self.config.warm_tier_size {
            warm.insert(key.to_string(), value.to_vec());
        }
        
        Ok(())
    }
    
    /// Evict items from warm tier to cold tier
    pub fn evict_warm_tier(&mut self) -> Result<usize> {
        // Get all items from warm tier
        let items = {
            let mut warm = self.warm_cache.lock().unwrap();
            let items: HashMap<String, Vec<u8>> = warm.drain().collect();
            items
        };
        
        let count = items.len();
        
        // Write all warm tier items to cold tier
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
    
    /// Get all keys from cold tier
    pub fn keys(&self) -> Result<Vec<String>> {
        let conn = self.cold_conn.lock().unwrap();
        let mut stmt = conn.prepare("SELECT key FROM kv_store")?;
        let keys: Result<Vec<String>, _> = stmt
            .query_map([], |row| row.get(0))?
            .collect();
        keys.map_err(|e| e.into())
    }
    
    /// Delete key from all tiers
    pub fn delete(&mut self, key: &str) -> Result<()> {
        // Remove from warm tier
        self.warm_cache.lock().unwrap().remove(key);
        
        // Remove from cold tier
        let conn = self.cold_conn.lock().unwrap();
        conn.execute(
            "DELETE FROM kv_store WHERE key = ?1",
            params![key],
        )?;
        
        Ok(())
    }
    
    /// Clear all tiers
    pub fn clear(&mut self) -> Result<()> {
        self.warm_cache.lock().unwrap().clear();
        let conn = self.cold_conn.lock().unwrap();
        conn.execute("DELETE FROM kv_store", [])?;
        Ok(())
    }
    
    /// Get storage statistics
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
}

#[derive(Debug)]
pub struct StorageStats {
    pub warm_tier_entries: usize,
    pub warm_tier_bytes: usize,
    pub cold_tier_entries: i64,
}
