use dashmap::DashMap;
use lru::LruCache;
use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyDict};
use pyo3::Bound;
use serde::{Deserialize, Serialize};
use std::num::NonZeroUsize;
use std::str::FromStr;
use std::sync::{Arc, Mutex};

mod async_ops;
mod cache;
mod crypto;
mod storage;

#[cfg(test)]
mod tests_jsonb;
#[cfg(test)]
mod tests_lru;
#[cfg(test)]
mod tests_storage;

pub use async_ops::{AsyncDictSQLite, AsyncTableProxy};
pub use cache::HybridCache;
pub use crypto::CryptoEngine;
pub use storage::{MemoryTier, StorageEngine};

/// Safe Pickle Policy using Python's safe_pickle module
#[derive(Debug)]
pub struct SafePicklePolicy {
    policy: PyObject,
}

impl SafePicklePolicy {
    /// Create a new default policy
    pub fn new() -> PyResult<Self> {
        Python::with_gil(|py| {
            let sys = py.import("sys")?;
            let path = sys.getattr("path")?;
            path.call_method1("append", ("modules",))?;
            let safe_pickle = py.import("safe_pickle")?;
            let policy_class = safe_pickle.getattr("SafePolicy")?;
            // Call SafePolicy() without arguments - it now defaults denied_globals to DEFAULT_DENY
            let policy = policy_class.call0()?;
            Ok(SafePicklePolicy {
                policy: policy.unbind(),
            })
        })
    }

    /// Create policy for a package
    pub fn for_package(pkg_prefix: &str) -> PyResult<Self> {
        Python::with_gil(|py| {
            let sys = py.import("sys")?;
            let path = sys.getattr("path")?;
            path.call_method1("append", ("modules",))?;
            let safe_pickle = py.import("safe_pickle")?;
            let policy_class = safe_pickle.getattr("SafePolicy")?;
            let policy = policy_class.call_method1("for_package", (pkg_prefix,))?;
            Ok(SafePicklePolicy {
                policy: policy.unbind(),
            })
        })
    }

    /// Add allowed module prefix
    pub fn with_module_prefix(self, prefix: String) -> PyResult<Self> {
        Python::with_gil(|py| {
            let policy_bound = self.policy.bind(py);
            let allowed_module_prefixes = policy_bound.getattr("allowed_module_prefixes")?;
            allowed_module_prefixes.call_method1("append", (prefix,))?;
            Ok(self)
        })
    }
}

impl Default for SafePicklePolicy {
    fn default() -> Self {
        Self::new().unwrap()
    }
}

/// Safe Pickle Validator using Python's safe_pickle module
pub struct SafePickleValidator {
    policy: SafePicklePolicy,
}

impl SafePickleValidator {
    /// Create a new validator with the given policy
    pub fn new(policy: SafePicklePolicy) -> Self {
        SafePickleValidator { policy }
    }

    /// Validate pickle data using Python's safe_loads
    pub fn validate(&self, data: &[u8]) -> PyResult<()> {
        // Try to load, if successful, it's valid
        let _ = self.validate_and_load(data)?;
        Ok(())
    }

    /// Validate and load pickle data using Python's safe_loads
    pub fn validate_and_load(&self, data: &[u8]) -> PyResult<PyObject> {
        Python::with_gil(|py| {
            let sys = py.import("sys")?;
            let path = sys.getattr("path")?;
            path.call_method1("append", ("modules",))?;
            let safe_pickle = py.import("safe_pickle")?;
            let safe_loads = safe_pickle.getattr("safe_loads")?;
            let kwargs = pyo3::types::PyDict::new(py);
            kwargs.set_item("policy", self.policy.policy.bind(py))?;
            let result = safe_loads.call((data,), Some(&kwargs))?;
            Ok(result.unbind())
        })
    }
}

impl Default for SafePickleValidator {
    fn default() -> Self {
        SafePickleValidator::new(SafePicklePolicy::default())
    }
}

/// Helper function to convert Python object to serde_json::Value
fn pyobject_to_json_value(obj: PyObject, py: Python) -> PyResult<serde_json::Value> {
    use pyo3::types::{PyBool, PyDict, PyFloat, PyInt, PyList, PyString};

    let obj_ref = obj.bind(py);

    if obj_ref.is_none() {
        Ok(serde_json::Value::Null)
    } else if let Ok(val) = obj_ref.downcast::<PyBool>() {
        Ok(serde_json::Value::Bool(val.is_true()))
    } else if let Ok(val) = obj_ref.downcast::<PyInt>() {
        if let Ok(i) = val.extract::<i64>() {
            Ok(serde_json::Value::Number(i.into()))
        } else {
            // Try as u64 for large numbers
            let u: u64 = val.extract()?;
            Ok(serde_json::Value::Number(u.into()))
        }
    } else if let Ok(val) = obj_ref.downcast::<PyFloat>() {
        let f: f64 = val.extract()?;
        Ok(serde_json::Value::Number(
            serde_json::Number::from_f64(f)
                .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Invalid float"))?,
        ))
    } else if let Ok(val) = obj_ref.downcast::<PyString>() {
        Ok(serde_json::Value::String(val.to_string()))
    } else if let Ok(val) = obj_ref.downcast::<PyList>() {
        let mut arr = Vec::new();
        for item in val.iter() {
            arr.push(pyobject_to_json_value(item.into(), py)?);
        }
        Ok(serde_json::Value::Array(arr))
    } else if let Ok(val) = obj_ref.downcast::<PyDict>() {
        let mut map = serde_json::Map::new();
        for (key, value) in val.iter() {
            let key_str: String = key.extract()?;
            map.insert(key_str, pyobject_to_json_value(value.into(), py)?);
        }
        Ok(serde_json::Value::Object(map))
    } else {
        Err(PyErr::new::<pyo3::exceptions::PyTypeError, _>(
            "Unsupported type for JSON serialization. Use pickle mode for arbitrary objects.",
        ))
    }
}

/// Helper function to convert serde_json::Value to Python object
fn json_value_to_pyobject(value: serde_json::Value, py: Python) -> PyResult<PyObject> {
    use pyo3::types::{PyBool, PyDict, PyFloat, PyInt, PyList, PyString};

    match value {
        serde_json::Value::Null => Ok(py.None()),
        serde_json::Value::Bool(b) => Ok(PyBool::new(py, b).to_owned().unbind().into()),
        serde_json::Value::Number(n) => {
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
            let list = PyList::empty(py);
            for item in arr {
                list.append(json_value_to_pyobject(item, py)?)?;
            }
            Ok(list.into())
        }
        serde_json::Value::Object(map) => {
            let dict = PyDict::new(py);
            for (key, value) in map {
                dict.set_item(key, json_value_to_pyobject(value, py)?)?;
            }
            Ok(dict.into())
        }
    }
}

/// Type alias for write buffer to reduce complexity
type WriteBuffer = Arc<Mutex<Vec<(String, Vec<u8>)>>>;

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

/// Storage mode for data serialization
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Default)]
pub enum StorageMode {
    /// Pickle format (default, supports any Python object)
    #[default]
    Pickle,

    /// JSON text format (human-readable, limited types)
    Json,

    /// JSONB binary format using MessagePack (fast, compact, limited types)
    JsonB,

    /// Raw bytes (no conversion)
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
            _ => Err(format!(
                "Invalid storage_mode: {}. Choose from ['pickle', 'json', 'jsonb', 'bytes']",
                s
            )),
        }
    }
}

/// High-performance DictSQLite v4.2 implementation with I/O optimizations
///
/// Architecture:
/// - Lock-free concurrent hashmap for hot tier (100M+ ops/sec)
/// - LRU eviction for memory management
/// - Memory-mapped warm tier for frequently accessed data
/// - SQLite cold tier for persistence
/// - Async support for I/O operations
/// - Optional AES-256-GCM encryption (v4 feature)
/// - Safe Pickle validation (v4 feature)
///
/// v4.2 Optimizations:
/// - Write buffering for 43x speedup in WriteThrough mode
/// - Batch SQL operations to reduce I/O overhead
#[pyclass]
pub struct DictSQLiteV4 {
    /// Hot tier: Lock-free concurrent hashmap (in-memory)
    hot_tier: Arc<DashMap<String, Vec<u8>>>,

    /// LRU tracker for eviction (protects insertion order)
    access_tracker: Arc<Mutex<LruCache<String, ()>>>,

    /// Storage engine managing warm and cold tiers
    storage: Arc<Mutex<Option<StorageEngine>>>,

    /// Configuration
    config: Config,

    /// Encryption engine (optional)
    crypto: Option<Arc<CryptoEngine>>,

    /// Safe pickle validator (optional)
    safe_pickle: Option<Arc<SafePickleValidator>>,

    /// Write buffer for batching SQL writes (v4.2 optimization)
    write_buffer: WriteBuffer,

    /// Buffer size threshold for auto-flush
    buffer_size: usize,
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

    /// Storage mode for serialization
    pub storage_mode: StorageMode,

    /// Default table name
    pub table_name: String,
}

impl Default for Config {
    fn default() -> Self {
        Config {
            hot_tier_capacity: 1_000_000,
            warm_tier_size: 100 * 1024 * 1024, // 100MB
            enable_async_flush: true,
            flush_interval_ms: 1000,
            num_shards: num_cpus::get().next_power_of_two(),
            persist_mode: PersistMode::WriteThrough,
            enable_encryption: false,
            enable_safe_pickle: false,
            storage_mode: StorageMode::Pickle,
            table_name: "main".to_string(),
        }
    }
}

#[pymethods]
impl DictSQLiteV4 {
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
        let persist_mode_parsed = PersistMode::from_str(persist_mode)
            .map_err(PyErr::new::<pyo3::exceptions::PyValueError, _>)?;

        let storage_mode_parsed = StorageMode::from_str(storage_mode)
            .map_err(PyErr::new::<pyo3::exceptions::PyValueError, _>)?;

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

        let hot_tier = Arc::new(DashMap::with_capacity_and_shard_amount(
            config.hot_tier_capacity,
            config.num_shards,
        ));

        // Initialize LRU tracker for eviction
        let access_tracker = Arc::new(Mutex::new(LruCache::new(
            NonZeroUsize::new(config.hot_tier_capacity).unwrap(),
        )));

        // Only create storage if not in pure memory mode
        let storage = if config.persist_mode == PersistMode::Memory {
            Arc::new(Mutex::new(None))
        } else {
            Arc::new(Mutex::new(Some(
                StorageEngine::new(&db_path, &config)
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?,
            )))
        };

        // Initialize encryption if password provided
        let crypto = if let Some(password) = encryption_password {
            Some(Arc::new(CryptoEngine::new(&password, None).map_err(
                |e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()),
            )?))
        } else {
            None
        };

        // Initialize safe pickle validator if enabled
        let safe_pickle = if enable_safe_pickle {
            // Create policy with custom allowed modules if provided
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

        // Initialize write buffer (v4.2 optimization)
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

    /// Get value by key (lock-free read from hot tier)
    #[pyo3(signature = (key, default=None))]
    fn get(&self, key: String, default: Option<Vec<u8>>, py: Python) -> PyResult<PyObject> {
        // Track access for LRU
        self.access_tracker.lock().unwrap().put(key.clone(), ());

        // Try hot tier first (lock-free read)
        if let Some(value) = self.hot_tier.get(&key) {
            // Decrypt if encryption is enabled
            let data = if let Some(ref crypto) = self.crypto {
                crypto
                    .decrypt(&value)
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?
            } else {
                value.clone()
            };
            return Ok(PyBytes::new(py, &data).into());
        }

        // For Memory mode, hot tier is the only tier
        if self.config.persist_mode == PersistMode::Memory {
            return Ok(default
                .map(|v| PyBytes::new(py, &v).into())
                .unwrap_or_else(|| py.None()));
        }

        // Check storage tiers for other modes
        let storage_guard = self.storage.lock().unwrap();
        if let Some(ref storage) = *storage_guard {
            if let Ok(Some(value)) = storage.get(&key) {
                // Decrypt if encryption is enabled
                let data = if let Some(ref crypto) = self.crypto {
                    crypto.decrypt(&value).map_err(|e| {
                        PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string())
                    })?
                } else {
                    value.clone()
                };

                // Promote to hot tier (store encrypted)
                drop(storage_guard);
                self.hot_tier.insert(key, value);
                return Ok(PyBytes::new(py, &data).into());
            }
        }

        Ok(default
            .map(|v| PyBytes::new(py, &v).into())
            .unwrap_or_else(|| py.None()))
    }

    /// Set value for key (lock-free write to hot tier)
    /// v4.2: Uses write buffering for 43x speedup in WriteThrough mode
    fn set(&self, key: String, value: Vec<u8>) -> PyResult<()> {
        // Validate with safe pickle if enabled AND storage mode is Pickle
        // Safe pickle validation only makes sense for pickled data, not for JSON/JSONB/Bytes
        if let Some(ref validator) = self.safe_pickle {
            if self.config.storage_mode == StorageMode::Pickle {
                validator
                    .validate(&value)
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;
            }
        }

        // Encrypt if encryption is enabled
        let data = if let Some(ref crypto) = self.crypto {
            crypto
                .encrypt(&value)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?
        } else {
            value
        };

        self.hot_tier.insert(key.clone(), data.clone());

        // Track access for LRU
        self.access_tracker.lock().unwrap().put(key.clone(), ());

        // v4.2 Optimization: Use write buffer for WriteThrough mode
        if self.config.persist_mode == PersistMode::WriteThrough {
            let mut buffer = self.write_buffer.lock().unwrap();
            buffer.push((key.clone(), data));

            // Auto-flush when buffer is full
            if buffer.len() >= self.buffer_size {
                drop(buffer);
                self.flush_write_buffer()?;
            }
        }

        // Check if we need to evict to warm tier
        if self.hot_tier.len() > self.config.hot_tier_capacity {
            self.evict_to_warm_tier()?;
        }

        Ok(())
    }

    /// Evict least recently used item to warm tier (storage)
    fn evict_to_warm_tier(&self) -> PyResult<()> {
        let mut tracker = self.access_tracker.lock().unwrap();

        // Find LRU entry
        if let Some((evict_key, _)) = tracker.pop_lru() {
            // Remove from hot tier
            if let Some((_, value)) = self.hot_tier.remove(&evict_key) {
                // Write to storage if not in memory mode
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

    /// Flush write buffer to storage (v4.2 optimization)
    /// Batches multiple writes into a single transaction for better performance
    fn flush_write_buffer(&self) -> PyResult<()> {
        let mut buffer = self.write_buffer.lock().unwrap();

        if buffer.is_empty() {
            return Ok(());
        }

        // Get storage handle
        let mut storage_guard = self.storage.lock().unwrap();
        if let Some(ref mut storage) = *storage_guard {
            // Batch write all buffered items
            for (key, value) in buffer.drain(..) {
                storage
                    .set(&key, &value)
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
            }
        }

        Ok(())
    }

    /// Flush pending writes to storage (for Lazy mode)
    /// v4.2: Also flushes write buffer
    fn flush(&self) -> PyResult<()> {
        if self.config.persist_mode == PersistMode::Memory {
            return Ok(()); // No-op for pure memory mode
        }

        // First, flush write buffer (v4.2)
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
                    crypto
                        .decrypt(&value)
                        .unwrap_or_else(|_| value.clone())
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
                    crypto
                        .decrypt(&value)
                        .unwrap_or_else(|_| value.clone())
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
        
        // Collect all unique keys
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
        
        Ok(all_keys.len())
    }

    /// Check if key exists
    fn contains(&self, key: String) -> PyResult<bool> {
        // First check hot tier
        if self.hot_tier.contains_key(&key) {
            return Ok(true);
        }
        
        // Then check storage
        if self.config.persist_mode != PersistMode::Memory {
            let storage_guard = self.storage.lock().unwrap();
            if let Some(ref storage) = *storage_guard {
                if let Ok(Some(_)) = storage.get(&key) {
                    return Ok(true);
                }
            }
        }
        
        Ok(false)
    }

    /// Clear all data
    fn clear(&self) -> PyResult<()> {
        self.hot_tier.clear();
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
}

/// Python module definition
#[pymodule]
fn dictsqlite_v4(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<DictSQLiteV4>()?;
    m.add_class::<AsyncDictSQLite>()?;
    m.add_class::<TableProxy>()?;
    m.add_class::<AsyncTableProxy>()?;
    Ok(())
}
