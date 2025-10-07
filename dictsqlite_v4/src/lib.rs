use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyDict};
use dashmap::DashMap;
use std::sync::{Arc, Mutex};
use serde::{Deserialize, Serialize};
use std::str::FromStr;

mod storage;
mod cache;
mod async_ops;
mod crypto;
mod safe_pickle;

pub use storage::{StorageEngine, MemoryTier};
pub use cache::HybridCache;
pub use async_ops::AsyncDictSQLite;
pub use crypto::CryptoEngine;
pub use safe_pickle::{SafePicklePolicy, SafePickleValidator};

/// Persistence mode for performance vs durability trade-off
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
pub enum PersistMode {
    /// Pure in-memory (fastest: 100M+ ops/sec, no durability)
    Memory,
    
    /// Lazy persistence (fast: 40-80M ops/sec, persist on flush)
    Lazy,
    
    /// Write-through (safe: 1-3M ops/sec, immediate durability)
    WriteThrough,
}

impl FromStr for PersistMode {
    type Err = String;
    
    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s.to_lowercase().as_str() {
            "memory" => Ok(PersistMode::Memory),
            "lazy" => Ok(PersistMode::Lazy),
            "writethrough" | "write_through" => Ok(PersistMode::WriteThrough),
            _ => Err(format!("Invalid persist_mode: {}", s)),
        }
    }
}

/// High-performance DictSQLite v4.0 implementation with enhanced security
/// 
/// Architecture:
/// - Lock-free concurrent hashmap for hot tier (100M+ ops/sec)
/// - Memory-mapped warm tier for frequently accessed data
/// - SQLite cold tier for persistence
/// - Async support for I/O operations
/// - Optional AES-256-GCM encryption (v4 feature)
/// - Safe Pickle validation (v4 feature)
#[pyclass]
pub struct DictSQLiteV4 {
    /// Hot tier: Lock-free concurrent hashmap (in-memory)
    hot_tier: Arc<DashMap<String, Vec<u8>>>,
    
    /// Storage engine managing warm and cold tiers
    storage: Arc<Mutex<Option<StorageEngine>>>,
    
    /// Configuration
    config: Config,
    
    /// Encryption engine (optional)
    crypto: Option<Arc<CryptoEngine>>,
    
    /// Safe pickle validator (optional)
    safe_pickle: Option<Arc<SafePickleValidator>>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Config {
    /// Maximum hot tier size (entries)
    pub hot_tier_capacity: usize,
    
    /// Warm tier size (bytes)
    pub warm_tier_size: usize,
    
    /// Enable async background flush
    pub enable_async_flush: bool,
    
    /// Flush interval (milliseconds)
    pub flush_interval_ms: u64,
    
    /// Number of shards for concurrent access
    pub num_shards: usize,
    
    /// Persistence mode
    pub persist_mode: PersistMode,
    
    /// Enable encryption
    pub enable_encryption: bool,
    
    /// Enable safe pickle validation
    pub enable_safe_pickle: bool,
}

impl Default for Config {
    fn default() -> Self {
        Config {
            hot_tier_capacity: 1_000_000,
            warm_tier_size: 100 * 1024 * 1024, // 100MB
            enable_async_flush: true,
            flush_interval_ms: 1000,
            num_shards: num_cpus::get(),
            persist_mode: PersistMode::WriteThrough,
            enable_encryption: false,
            enable_safe_pickle: false,
        }
    }
}

#[pymethods]
impl DictSQLiteV4 {
    #[new]
    #[pyo3(signature = (db_path, hot_capacity=1_000_000, enable_async=true, persist_mode="writethrough", encryption_password=None, enable_safe_pickle=false))]
    fn new(
        db_path: String, 
        hot_capacity: usize, 
        enable_async: bool, 
        persist_mode: &str,
        encryption_password: Option<String>,
        enable_safe_pickle: bool,
    ) -> PyResult<Self> {
        let mut config = Config::default();
        config.hot_tier_capacity = hot_capacity;
        config.enable_async_flush = enable_async;
        config.persist_mode = PersistMode::from_str(persist_mode)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e))?;
        config.enable_encryption = encryption_password.is_some();
        config.enable_safe_pickle = enable_safe_pickle;
        
        let hot_tier = Arc::new(DashMap::with_capacity_and_shard_amount(
            config.hot_tier_capacity,
            config.num_shards,
        ));
        
        // Only create storage if not in pure memory mode
        let storage = if config.persist_mode == PersistMode::Memory {
            Arc::new(Mutex::new(None))
        } else {
            Arc::new(Mutex::new(Some(
                StorageEngine::new(&db_path, &config)
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?
            )))
        };
        
        // Initialize encryption if password provided
        let crypto = if let Some(password) = encryption_password {
            Some(Arc::new(
                CryptoEngine::new(&password, None)
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?
            ))
        } else {
            None
        };
        
        // Initialize safe pickle validator if enabled
        let safe_pickle = if enable_safe_pickle {
            Some(Arc::new(SafePickleValidator::default()))
        } else {
            None
        };
        
        Ok(DictSQLiteV4 {
            hot_tier,
            storage,
            config,
            crypto,
            safe_pickle,
        })
    }
    
    /// Get value by key (lock-free read from hot tier)
    fn get(&self, key: String, py: Python) -> PyResult<Option<PyObject>> {
        // Try hot tier first (lock-free read)
        if let Some(value) = self.hot_tier.get(&key) {
            // Decrypt if encryption is enabled
            let data = if let Some(ref crypto) = self.crypto {
                crypto.decrypt(&value)
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?
            } else {
                value.clone()
            };
            return Ok(Some(PyBytes::new(py, &data).into()));
        }
        
        // For Memory mode, hot tier is the only tier
        if self.config.persist_mode == PersistMode::Memory {
            return Ok(None);
        }
        
        // Check storage tiers for other modes
        let storage_guard = self.storage.lock().unwrap();
        if let Some(ref storage) = *storage_guard {
            if let Ok(Some(value)) = storage.get(&key) {
                // Decrypt if encryption is enabled
                let data = if let Some(ref crypto) = self.crypto {
                    crypto.decrypt(&value)
                        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?
                } else {
                    value.clone()
                };
                
                // Promote to hot tier (store encrypted)
                drop(storage_guard);
                self.hot_tier.insert(key, value);
                return Ok(Some(PyBytes::new(py, &data).into()));
            }
        }
        
        Ok(None)
    }
    
    /// Set value for key (lock-free write to hot tier)
    fn set(&self, key: String, value: Vec<u8>) -> PyResult<()> {
        // Validate with safe pickle if enabled
        if let Some(ref validator) = self.safe_pickle {
            validator.validate(&value)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;
        }
        
        // Encrypt if encryption is enabled
        let data = if let Some(ref crypto) = self.crypto {
            crypto.encrypt(&value)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?
        } else {
            value
        };
        
        self.hot_tier.insert(key.clone(), data.clone());
        
        // Persist immediately if WriteThrough mode
        if self.config.persist_mode == PersistMode::WriteThrough {
            let mut storage_guard = self.storage.lock().unwrap();
            if let Some(ref mut storage) = *storage_guard {
                storage.set(&key, &data)
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
            }
        }
        
        // Check if we need to evict to warm tier
        if self.hot_tier.len() > self.config.hot_tier_capacity {
            // TODO: Implement LRU eviction to warm tier
        }
        
        Ok(())
    }
    
    /// Flush pending writes to storage (for Lazy mode)
    fn flush(&self) -> PyResult<()> {
        if self.config.persist_mode == PersistMode::Memory {
            return Ok(()); // No-op for pure memory mode
        }
        
        let mut storage_guard = self.storage.lock().unwrap();
        if let Some(ref mut storage) = *storage_guard {
            // Persist all hot tier entries
            for entry in self.hot_tier.iter() {
                storage.set(entry.key(), entry.value())
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
            }
        }
        Ok(())
    }
    
    /// Delete key
    fn delete(&self, key: String) -> PyResult<()> {
        self.hot_tier.remove(&key);
        // TODO: Also remove from warm/cold tiers
        Ok(())
    }
    
    /// Bulk insert (optimized batch operation)
    fn bulk_insert(&self, items: &PyDict) -> PyResult<()> {
        for (key, value) in items.iter() {
            let key_str: String = key.extract()?;
            let value_bytes: Vec<u8> = value.extract()?;
            self.hot_tier.insert(key_str, value_bytes);
        }
        Ok(())
    }
    
    /// Get all keys
    fn keys(&self, _py: Python) -> PyResult<Vec<String>> {
        let keys: Vec<String> = self.hot_tier
            .iter()
            .map(|entry| entry.key().clone())
            .collect();
        Ok(keys)
    }
    
    /// Get number of items in hot tier
    fn len(&self) -> PyResult<usize> {
        Ok(self.hot_tier.len())
    }
    
    /// Check if key exists
    fn contains(&self, key: String) -> PyResult<bool> {
        Ok(self.hot_tier.contains_key(&key))
    }
    
    /// Clear all data
    fn clear(&self) -> PyResult<()> {
        self.hot_tier.clear();
        Ok(())
    }
    
    /// Close database (flush if needed)
    fn close(&self) -> PyResult<()> {
        if self.config.persist_mode == PersistMode::Lazy {
            self.flush()?;
        }
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
        self.get(key, py)?
            .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyKeyError, _>("Key not found"))
    }
    
    /// Dict-like access: db[key] = value
    fn __setitem__(&self, key: String, value: Vec<u8>) -> PyResult<()> {
        self.set(key, value)
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
}

/// Python module definition
#[pymodule]
fn dictsqlite_v4(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<DictSQLiteV4>()?;
    m.add_class::<AsyncDictSQLite>()?;
    Ok(())
}
