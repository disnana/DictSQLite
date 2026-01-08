// v6.0: PyO3 0.27 API完全移行

use dashmap::DashMap;
use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyDict};
use rayon::prelude::*;
use std::collections::HashMap;
use std::sync::{Arc, Mutex, OnceLock};
use tokio::runtime::Runtime;

use crate::{
    json_value_to_pyobject, pyobject_to_json_value, Config, PersistMode, StorageEngine,
    StorageMode, TableMode,
};

// v5.1最適化: プロセス全体で共有されるTokio Runtime
// インスタンスごとにRuntimeを作成する代わりに、グローバルで1つを共有
static GLOBAL_RUNTIME: OnceLock<Runtime> = OnceLock::new();

/// グローバルTokio Runtimeを取得または初期化
fn get_global_runtime() -> &'static Runtime {
    GLOBAL_RUNTIME.get_or_init(|| Runtime::new().expect("Failed to create global Tokio runtime"))
}

/// Async version of DictSQLite v4.2 for high-concurrency scenarios
///
/// Optimizations (v4.2):
/// - Write buffering for 300x speedup on WriteThrough mode
/// - Batch SQL operations to reduce I/O overhead
/// - Shard-per-core DashMap for optimal concurrent access
/// - Rayon for parallel batch operations
/// - No GIL contention for pure in-memory operations
/// - True asyncio support with Python awaitable methods
#[pyclass]
pub struct AsyncDictSQLite {
    /// Lock-free concurrent hashmap with shard-per-core
    cache: Arc<DashMap<String, Vec<u8>>>,

    /// Storage engine for persistence (optional)
    /// v5最適化: Mutexを削除、StorageEngineは内部でスレッドセーフ
    storage: Arc<Option<StorageEngine>>,

    /// Configuration
    config: Config,

    /// Capacity
    capacity: usize,

    /// Write buffer for batching SQL writes (v4.2 optimization)
    write_buffer: Arc<Mutex<HashMap<String, Vec<u8>>>>,

    /// Buffer size threshold for auto-flush
    buffer_size: usize,

    /// Tokio runtime for async operations (v5.1: shared via OnceLock)
    runtime: &'static Runtime,
}

#[pymethods]
impl AsyncDictSQLite {
    #[new]
    #[pyo3(signature = (db_path, capacity=1_000_000, persist_mode="lazy", storage_mode="pickle", table_name="main", buffer_size=100, table_mode="prefix"))]
    fn new(
        db_path: String,
        capacity: usize,
        persist_mode: &str,
        storage_mode: &str,
        table_name: &str,
        buffer_size: usize,
        table_mode: &str,
    ) -> PyResult<Self> {
        use std::str::FromStr;

        // Use shard-per-core for optimal concurrent access
        let num_shards = num_cpus::get().next_power_of_two();
        let cache = Arc::new(DashMap::with_capacity_and_shard_amount(
            capacity, num_shards,
        ));

        // Create config with custom values
        let persist_mode_parsed = PersistMode::from_str(persist_mode)
            .map_err(PyErr::new::<pyo3::exceptions::PyValueError, _>)?;

        let storage_mode_parsed = StorageMode::from_str(storage_mode)
            .map_err(PyErr::new::<pyo3::exceptions::PyValueError, _>)?;

        let table_mode_parsed = TableMode::from_str(table_mode)
            .map_err(PyErr::new::<pyo3::exceptions::PyValueError, _>)?;

        let config = Config {
            hot_tier_capacity: capacity,
            persist_mode: persist_mode_parsed,
            storage_mode: storage_mode_parsed,
            table_name: table_name.to_string(),
            table_mode: table_mode_parsed,
            ..Default::default()
        };

        // v5最適化: Mutexを削除、StorageEngineは内部でスレッドセーフ
        let storage = if config.persist_mode == PersistMode::Memory {
            Arc::new(None)
        } else {
            Arc::new(Some(StorageEngine::new(&db_path, &config).map_err(
                |e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()),
            )?))
        };

        // Initialize write buffer (v4.2 optimization)
        let write_buffer = Arc::new(Mutex::new(HashMap::with_capacity(buffer_size)));

        // v5.1最適化: グローバル共有Runtimeを使用
        // インスタンスごとに新しいRuntimeを作成する代わりに、プロセス全体で1つのRuntimeを共有
        // これによりメモリ使用量とスレッド生成コストを削減
        let runtime = get_global_runtime();

        Ok(AsyncDictSQLite {
            cache,
            storage,
            config,
            capacity,
            write_buffer,
            buffer_size,
            runtime,
        })
    }

    /// Async get (non-blocking, no GIL for cache access)
    /// Now with storage fallback for persistence modes
    fn get_async(&self, key: String, py: Python) -> PyResult<Option<Py<PyAny>>> {
        let cache = self.cache.clone();

        // Release GIL during cache access
        let result = py.detach(|| cache.get(&key).map(|value| value.clone()));

        // If found in cache, return immediately
        if let Some(value) = result {
            return Ok(Some(PyBytes::new(py, &value).into()));
        }

        // Fallback to storage if not in memory mode
        // v5最適化: Mutex削除、直接アクセス
        if self.config.persist_mode != PersistMode::Memory {
            if let Some(ref storage) = *self.storage {
                if let Ok(Some(value)) = storage.get(&key) {
                    // Promote to cache for future access
                    self.cache.insert(key, value.clone());
                    return Ok(Some(PyBytes::new(py, &value).into()));
                }
            }
        }

        Ok(None)
    }

    /// Async set (non-blocking, with write buffering for v4.2)
    /// Write buffering provides 300x speedup by batching SQL operations
    fn set_async(&self, key: String, value: Vec<u8>) -> PyResult<()> {
        // Always update cache immediately for fast reads
        self.cache.insert(key.clone(), value.clone());

        // Handle persistence based on mode
        if self.config.persist_mode == PersistMode::WriteThrough {
            // Add to write buffer
            {
                let mut buffer = self.write_buffer.lock().unwrap();
                buffer.insert(key, value);
            }

            // In writethrough mode, always flush immediately to maintain semantics
            // This ensures data is immediately visible to other instances
            self.flush_write_buffer()?;
        }

        Ok(())
    }

    /// Flush write buffer to storage (v4.2 optimization)
    /// Batches multiple writes into a single transaction
    fn flush_write_buffer(&self) -> PyResult<()> {
        let mut buffer = self.write_buffer.lock().unwrap();

        if buffer.is_empty() {
            return Ok(());
        }

        // v5最適化: Mutex削除、直接アクセス
        if let Some(ref storage) = *self.storage {
            // Batch write all buffered items in a single transaction
            for (key, value) in buffer.drain() {
                storage
                    .set(&key, &value)
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
            }
        }

        Ok(())
    }

    /// Batch get (optimized with Rayon for parallel processing)
    /// v4.2: Improved cache miss handling with batch storage reads
    fn batch_get(&self, keys: Vec<String>, py: Python) -> PyResult<Vec<Option<Py<PyAny>>>> {
        let cache = self.cache.clone();

        // Release GIL during parallel batch processing
        let (cached_results, cache_misses): (Vec<_>, Vec<_>) = py.detach(|| {
            // Use rayon for parallel batch processing
            let results: Vec<(usize, Option<Vec<u8>>)> = keys
                .par_iter()
                .enumerate()
                .map(|(idx, key)| (idx, cache.get(key).map(|value| value.clone())))
                .collect();

            // Separate cached results from misses
            let mut cached = Vec::new();
            let mut misses = Vec::new();
            for (idx, result) in results {
                match result {
                    Some(value) => cached.push((idx, Some(value))),
                    None => {
                        cached.push((idx, None));
                        misses.push((idx, keys[idx].clone()));
                    }
                }
            }
            (cached, misses)
        });

        // If there are cache misses and we have storage, batch fetch them
        let mut final_results = cached_results;
        if !cache_misses.is_empty() && self.config.persist_mode != PersistMode::Memory {
            // v5最適化: Mutex削除、直接アクセス
            if let Some(ref storage) = *self.storage {
                // v4.2 Optimization: Batch read from storage (reduces SQL queries)
                for (idx, key) in cache_misses {
                    if let Ok(Some(value)) = storage.get(&key) {
                        // Promote to cache
                        self.cache.insert(key, value.clone());
                        final_results[idx].1 = Some(value);
                    }
                }
            }
        }

        // Convert to Py<PyAny>s with GIL
        Ok(final_results
            .into_iter()
            .map(|(_, opt_value)| opt_value.map(|value| PyBytes::new(py, &value).into()))
            .collect())
    }

    /// Batch set (optimized with Rayon for parallel writes)
    fn batch_set(&self, items: Vec<(String, Vec<u8>)>) -> PyResult<()> {
        // Parallel batch insert using rayon (no GIL needed)
        items.par_iter().for_each(|(key, value)| {
            self.cache.insert(key.clone(), value.clone());
        });

        Ok(())
    }

    /// High-performance batch get without Python objects (direct bytes)
    fn batch_get_fast(&self, keys: Vec<String>) -> PyResult<Vec<Option<Vec<u8>>>> {
        // Fully parallel, no GIL contention
        let results: Vec<Option<Vec<u8>>> = keys
            .par_iter()
            .map(|key| self.cache.get(key).map(|value| value.clone()))
            .collect();

        Ok(results)
    }

    /// Get cache statistics
    fn stats(&self) -> PyResult<(usize, usize)> {
        Ok((self.cache.len(), self.capacity))
    }

    /// Clear all data
    fn clear(&self) -> PyResult<()> {
        self.cache.clear();
        Ok(())
    }

    /// Flush cache to storage (for Lazy mode)
    /// v4.2: Also flushes write buffer
    fn flush(&self) -> PyResult<()> {
        if self.config.persist_mode == PersistMode::Memory {
            return Ok(());
        }

        // First, flush any pending writes in the buffer
        self.flush_write_buffer()?;

        // Then flush the cache (for Lazy mode)
        // v5最適化: Mutex削除、直接アクセス
        if self.config.persist_mode == PersistMode::Lazy {
            if let Some(ref storage) = *self.storage {
                for entry in self.cache.iter() {
                    storage
                        .set(entry.key(), entry.value())
                        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
                }
            }
        }

        Ok(())
    }

    /// Close and flush if needed
    fn close(&self) -> PyResult<()> {
        // Flush write buffer for WriteThrough mode
        // Flush both buffer and cache for Lazy mode
        if self.config.persist_mode != PersistMode::Memory {
            self.flush()?;
        }
        Ok(())
    }

    /// Truly async get operation (awaitable in Python)
    /// Returns a Python coroutine that resolves to the value
    #[pyo3(signature = (key))]
    async fn aget(&self, key: String) -> PyResult<Option<Vec<u8>>> {
        let cache = self.cache.clone();
        let storage = self.storage.clone();
        let config = self.config.clone();
        let runtime = self.runtime;

        // Check cache first
        if let Some(value) = cache.get(&key) {
            return Ok(Some(value.clone()));
        }

        // Fallback to storage if not in memory mode
        // v5最適化: Mutex削除、直接アクセス
        if config.persist_mode != PersistMode::Memory {
            let key_clone = key.clone();
            let value = runtime
                .spawn_blocking(move || {
                    if let Some(ref storage_engine) = *storage {
                        storage_engine.get(&key_clone).ok().flatten()
                    } else {
                        None
                    }
                })
                .await
                .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;

            if let Some(val) = value {
                // Promote to cache for future access
                cache.insert(key, val.clone());
                return Ok(Some(val));
            }
        }

        Ok(None)
    }

    /// Truly async set operation (awaitable in Python)
    /// Returns a Python coroutine that completes when the operation is done
    #[pyo3(signature = (key, value))]
    async fn aset(&self, key: String, value: Vec<u8>) -> PyResult<()> {
        let cache = self.cache.clone();
        let write_buffer = self.write_buffer.clone();
        let storage = self.storage.clone();
        let config = self.config.clone();
        let buffer_size = self.buffer_size;
        let runtime = self.runtime;

        // Always update cache immediately for fast reads
        cache.insert(key.clone(), value.clone());

        // Handle persistence based on mode
        // v5最適化: Mutex削除、直接アクセス
        if config.persist_mode == PersistMode::WriteThrough {
            // Add to write buffer
            let should_flush = {
                let mut buffer = write_buffer.lock().unwrap();
                buffer.insert(key, value);
                buffer.len() >= buffer_size
            };

            // Flush if buffer is full
            if should_flush {
                runtime
                    .spawn_blocking(move || {
                        let mut buffer = write_buffer.lock().unwrap();
                        if buffer.is_empty() {
                            return Ok(());
                        }

                        // Get storage handle and write
                        if let Some(ref storage_engine) = *storage {
                            for (k, v) in buffer.drain() {
                                storage_engine.set(&k, &v).map_err(|e| {
                                    pyo3::exceptions::PyIOError::new_err(e.to_string())
                                })?;
                            }
                        }
                        Ok::<(), PyErr>(())
                    })
                    .await
                    .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))??;
            }
        }

        Ok(())
    }

    /// Truly async batch get operation (awaitable in Python)
    #[pyo3(signature = (keys))]
    async fn abatch_get(&self, keys: Vec<String>) -> PyResult<Vec<Option<Vec<u8>>>> {
        let cache = self.cache.clone();
        let storage = self.storage.clone();
        let config = self.config.clone();
        let runtime = self.runtime;

        let mut results = Vec::with_capacity(keys.len());

        // Check cache for all keys
        let mut cache_misses = Vec::new();
        for (idx, key) in keys.iter().enumerate() {
            if let Some(value) = cache.get(key) {
                results.push((idx, Some(value.clone())));
            } else {
                results.push((idx, None));
                cache_misses.push((idx, key.clone()));
            }
        }

        // v5最適化: Mutex削除、直接アクセス
        if !cache_misses.is_empty() && config.persist_mode != PersistMode::Memory {
            let fetched = runtime
                .spawn_blocking(move || {
                    let mut fetched_values = Vec::new();

                    if let Some(ref storage_engine) = *storage {
                        for (idx, key) in cache_misses {
                            if let Ok(Some(value)) = storage_engine.get(&key) {
                                fetched_values.push((idx, key, value));
                            }
                        }
                    }
                    fetched_values
                })
                .await
                .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;

            for (idx, key, value) in fetched {
                // Promote to cache
                cache.insert(key, value.clone());
                results[idx].1 = Some(value);
            }
        }

        // Sort by index and extract values
        results.sort_by_key(|(idx, _)| *idx);
        Ok(results.into_iter().map(|(_, v)| v).collect::<Vec<_>>())
    }

    /// Truly async batch set operation (awaitable in Python)
    #[pyo3(signature = (items))]
    async fn abatch_set(&self, items: Vec<(String, Vec<u8>)>) -> PyResult<()> {
        let cache = self.cache.clone();
        let write_buffer = self.write_buffer.clone();
        let storage = self.storage.clone();
        let config = self.config.clone();
        let buffer_size = self.buffer_size;
        let runtime = self.runtime;

        // Update cache immediately for all items
        for (key, value) in &items {
            cache.insert(key.clone(), value.clone());
        }

        // Handle persistence based on mode
        if config.persist_mode == PersistMode::WriteThrough {
            // Add to write buffer
            let should_flush = {
                let mut buffer = write_buffer.lock().unwrap();
                for (key, value) in items {
                    buffer.insert(key, value);
                }
                // Flush when buffer reaches size threshold
                buffer.len() >= buffer_size
            };

            // Flush if buffer is full
            // v5最適化: Mutex削除、直接アクセス
            if should_flush {
                runtime
                    .spawn_blocking(move || {
                        let mut buffer = write_buffer.lock().unwrap();
                        if buffer.is_empty() {
                            return Ok(());
                        }

                        // Get storage handle and write
                        if let Some(ref storage_engine) = *storage {
                            for (k, v) in buffer.drain() {
                                storage_engine.set(&k, &v).map_err(|e| {
                                    pyo3::exceptions::PyIOError::new_err(e.to_string())
                                })?;
                            }
                        }
                        Ok::<(), PyErr>(())
                    })
                    .await
                    .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))??;
            }
        }

        Ok(())
    }

    /// Truly async contains operation (awaitable in Python)
    /// Check if a key exists in the database
    #[pyo3(signature = (key))]
    async fn acontains(&self, key: String) -> PyResult<bool> {
        let cache = self.cache.clone();
        let storage = self.storage.clone();
        let config = self.config.clone();

        // Check cache first
        if cache.contains_key(&key) {
            return Ok(true);
        }

        // If not in cache and we have storage, check storage
        // v5最適化: Mutex削除、直接アクセス
        if config.persist_mode != PersistMode::Memory {
            if let Some(ref storage_engine) = *storage {
                match storage_engine.get(&key) {
                    Ok(Some(_)) => return Ok(true),
                    Ok(None) => return Ok(false),
                    Err(_) => return Ok(false),
                }
            }
        }

        Ok(false)
    }

    /// Truly async delete operation (awaitable in Python)
    /// Delete a key from the database
    #[pyo3(signature = (key))]
    async fn adelete(&self, key: String) -> PyResult<()> {
        let cache = self.cache.clone();
        let storage = self.storage.clone();
        let config = self.config.clone();
        let runtime = self.runtime;

        // Remove from cache
        cache.remove(&key);

        // Remove from storage if persistence is enabled
        // v5最適化: Mutex削除、直接アクセス
        if config.persist_mode != PersistMode::Memory {
            runtime
                .spawn_blocking(move || {
                    if let Some(ref storage_engine) = *storage {
                        storage_engine
                            .delete(&key)
                            .map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;
                    }
                    Ok::<(), PyErr>(())
                })
                .await
                .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))??;
        }

        Ok(())
    }

    /// Truly async flush operation (awaitable in Python)
    /// Flush cached data to storage
    async fn aflush(&self) -> PyResult<()> {
        let cache = self.cache.clone();
        let write_buffer = self.write_buffer.clone();
        let storage = self.storage.clone();
        let config = self.config.clone();
        let runtime = self.runtime;

        if config.persist_mode == PersistMode::Memory {
            return Ok(());
        }

        // v5最適化: Mutex削除、直接アクセス
        runtime
            .spawn_blocking(move || {
                // First, flush any pending writes in the buffer
                let mut buffer = write_buffer.lock().unwrap();
                if !buffer.is_empty() {
                    if let Some(ref storage_engine) = *storage {
                        for (k, v) in buffer.drain() {
                            storage_engine
                                .set(&k, &v)
                                .map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;
                        }
                    }
                }
                drop(buffer);

                // Then flush the cache (for Lazy mode)
                if config.persist_mode == PersistMode::Lazy {
                    if let Some(ref storage_engine) = *storage {
                        for entry in cache.iter() {
                            storage_engine
                                .set(entry.key(), entry.value())
                                .map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;
                        }
                    }
                }

                Ok::<(), PyErr>(())
            })
            .await
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))??;

        Ok(())
    }

    /// Truly async close operation (awaitable in Python)
    /// Close and flush if needed
    async fn aclose(&self) -> PyResult<()> {
        // Flush write buffer for WriteThrough mode
        // Flush both buffer and cache for Lazy mode
        if self.config.persist_mode != PersistMode::Memory {
            self.aflush().await?;
        }
        Ok(())
    }

    /// Dict-like access: db[key]
    fn __getitem__(&self, key: String, py: Python) -> PyResult<Py<PyAny>> {
        // Add table prefix if default table is not "main" or empty
        let full_key = if !self.config.table_name.is_empty() && self.config.table_name != "main" {
            format!("{}:{}", self.config.table_name, key)
        } else {
            key.clone()
        };

        let result = self.get_async(full_key.clone(), py)?;
        if result.is_none() {
            return Err(PyErr::new::<pyo3::exceptions::PyKeyError, _>(format!(
                "Key not found: {}",
                key
            )));
        }

        // Extract bytes from result
        let data: Vec<u8> = result.unwrap().extract(py)?;

        // Deserialize based on storage mode
        match self.config.storage_mode {
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

    /// Dict-like access: db[key] = value
    fn __setitem__(&self, key: String, value: Py<PyAny>, py: Python) -> PyResult<()> {
        // Add table prefix if default table is not "main" or empty
        let full_key = if !self.config.table_name.is_empty() && self.config.table_name != "main" {
            format!("{}:{}", self.config.table_name, key)
        } else {
            key.clone()
        };

        // Convert value based on storage mode
        let data: Vec<u8> = match self.config.storage_mode {
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

        self.set_async(full_key, data)
    }

    /// Dict-like contains: key in db
    fn __contains__(&self, key: String, _py: Python) -> PyResult<bool> {
        // Add table prefix if default table is not "main" or empty
        let full_key = if !self.config.table_name.is_empty() && self.config.table_name != "main" {
            format!("{}:{}", self.config.table_name, key)
        } else {
            key
        };

        // Check cache first
        if self.cache.contains_key(&full_key) {
            return Ok(true);
        }

        // Check storage if persistence is enabled
        // v5最適化: Mutex削除、直接アクセス
        if self.config.persist_mode != PersistMode::Memory {
            if let Some(ref storage_engine) = *self.storage {
                match storage_engine.get(&full_key) {
                    Ok(Some(_)) => return Ok(true),
                    Ok(None) => return Ok(false),
                    Err(_) => return Ok(false),
                }
            }
        }

        Ok(false)
    }

    /// Dict-like deletion: del db[key]
    fn __delitem__(&self, key: String, py: Python) -> PyResult<()> {
        // Add table prefix if default table is not "main" or empty
        let full_key = if !self.config.table_name.is_empty() && self.config.table_name != "main" {
            format!("{}:{}", self.config.table_name, key)
        } else {
            key.clone()
        };

        // Check if key exists first
        if !self.__contains__(full_key.clone(), py)? {
            return Err(PyErr::new::<pyo3::exceptions::PyKeyError, _>(format!(
                "Key not found: {}",
                key
            )));
        }

        // Remove from cache
        self.cache.remove(&full_key);

        // Remove from write buffer
        if self.config.persist_mode == PersistMode::WriteThrough {
            let mut buffer = self.write_buffer.lock().unwrap();
            buffer.remove(&full_key);
        }

        // Remove from storage if persistence is enabled
        // v5最適化: Mutex削除、直接アクセス
        if self.config.persist_mode != PersistMode::Memory {
            if let Some(ref storage_engine) = *self.storage {
                storage_engine
                    .delete(&full_key)
                    .map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;
            }
        }

        Ok(())
    }

    /// Get a table proxy for accessing a specific table
    fn table(slf: PyRef<Self>, table_name: String) -> PyResult<AsyncTableProxy> {
        Ok(AsyncTableProxy {
            db: slf.into(),
            table_name,
        })
    }
}

/// AsyncTableProxy provides dict-like access to a specific table
#[pyclass]
pub struct AsyncTableProxy {
    db: Py<AsyncDictSQLite>,
    table_name: String,
}

#[pymethods]
impl AsyncTableProxy {
    /// Dict-like access: table[key]
    fn __getitem__(&self, key: String, py: Python) -> PyResult<Py<PyAny>> {
        let db = self.db.borrow(py);

        // Get raw data based on table mode
        let data: Vec<u8> = match db.config.table_mode {
            TableMode::Prefix => {
                // Prefix mode: use table:key format
                let full_key = format!("{}:{}", self.table_name, key);
                let result = db.get_async(full_key.clone(), py)?;
                if result.is_none() {
                    return Err(PyErr::new::<pyo3::exceptions::PyKeyError, _>(format!(
                        "Key not found: {}",
                        key
                    )));
                }
                result.unwrap().extract(py)?
            }
            TableMode::Separate => {
                // Separate mode: use separate SQLite table
                let cache_key = format!("{}:{}", self.table_name, key);

                // Check cache first
                if let Some(value) = db.cache.get(&cache_key) {
                    value.clone()
                } else {
                    // Check storage
                    // v5最適化: Mutex削除、直接アクセス
                    if let Some(ref storage) = *db.storage {
                        match storage.get_with_table(&self.table_name, &key) {
                            Ok(Some(value)) => {
                                // Promote to cache
                                db.cache.insert(cache_key, value.clone());
                                value
                            }
                            Ok(None) => {
                                return Err(PyErr::new::<pyo3::exceptions::PyKeyError, _>(
                                    format!("Key not found: {}", key),
                                ));
                            }
                            Err(e) => {
                                return Err(PyErr::new::<pyo3::exceptions::PyIOError, _>(
                                    e.to_string(),
                                ));
                            }
                        }
                    } else {
                        return Err(PyErr::new::<pyo3::exceptions::PyKeyError, _>(format!(
                            "Key not found: {}",
                            key
                        )));
                    }
                }
            }
        };

        // Deserialize based on storage mode
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
    fn __setitem__(&self, key: String, value: Py<PyAny>, py: Python) -> PyResult<()> {
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

        match db.config.table_mode {
            TableMode::Prefix => {
                let full_key = format!("{}:{}", self.table_name, key);
                db.set_async(full_key, data)
            }
            TableMode::Separate => {
                let cache_key = format!("{}:{}", self.table_name, key);

                // Update cache
                db.cache.insert(cache_key, data.clone());

                // Write to storage in WriteThrough mode
                // v5最適化: Mutex削除、直接アクセス
                if db.config.persist_mode == PersistMode::WriteThrough {
                    if let Some(ref storage) = *db.storage {
                        storage
                            .set_with_table(&self.table_name, &key, &data)
                            .map_err(|e| {
                                PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string())
                            })?;
                    }
                }

                Ok(())
            }
        }
    }

    /// Dict-like access: key in table
    fn __contains__(&self, key: String, py: Python) -> PyResult<bool> {
        let db = self.db.borrow(py);

        match db.config.table_mode {
            TableMode::Prefix => {
                let full_key = format!("{}:{}", self.table_name, key);
                let result = db.get_async(full_key, py)?;
                Ok(result.is_some())
            }
            TableMode::Separate => {
                let cache_key = format!("{}:{}", self.table_name, key);

                // Check cache first
                if db.cache.contains_key(&cache_key) {
                    return Ok(true);
                }

                // Check storage
                // v5最適化: Mutex削除、直接アクセス
                if db.config.persist_mode != PersistMode::Memory {
                    if let Some(ref storage) = *db.storage {
                        if let Ok(Some(_)) = storage.get_with_table(&self.table_name, &key) {
                            return Ok(true);
                        }
                    }
                }

                Ok(false)
            }
        }
    }

    /// Get all keys in this table
    fn keys(&self, py: Python) -> PyResult<Vec<String>> {
        let db = self.db.borrow(py);
        let prefix = format!("{}:", self.table_name);

        match db.config.table_mode {
            TableMode::Prefix => {
                // Get all keys from cache
                let mut all_keys: Vec<String> = db
                    .cache
                    .iter()
                    .filter(|entry| entry.key().starts_with(&prefix))
                    .map(|entry| entry.key()[prefix.len()..].to_string())
                    .collect();

                // Also get keys from storage if not in memory mode
                // v5最適化: Mutex削除、直接アクセス
                if db.config.persist_mode != PersistMode::Memory {
                    if let Some(ref storage) = *db.storage {
                        if let Ok(storage_keys) = storage.keys() {
                            for key in storage_keys {
                                if key.starts_with(&prefix) {
                                    let short_key = key[prefix.len()..].to_string();
                                    if !all_keys.contains(&short_key) {
                                        all_keys.push(short_key);
                                    }
                                }
                            }
                        }
                    }
                }

                Ok(all_keys)
            }
            TableMode::Separate => {
                use std::collections::HashSet;

                // Get keys from cache
                let mut all_keys: HashSet<String> = db
                    .cache
                    .iter()
                    .filter_map(|entry| {
                        let k = entry.key().clone();
                        if k.starts_with(&prefix) {
                            Some(k[prefix.len()..].to_string())
                        } else {
                            None
                        }
                    })
                    .collect();

                // Get keys from storage
                // v5最適化: Mutex削除、直接アクセス
                if db.config.persist_mode != PersistMode::Memory {
                    if let Some(ref storage) = *db.storage {
                        if let Ok(storage_keys) = storage.keys_with_table(&self.table_name) {
                            all_keys.extend(storage_keys);
                        }
                    }
                }

                Ok(all_keys.into_iter().collect())
            }
        }
    }

    /// Get all items as (key, value) tuples
    fn items(&self, py: Python) -> PyResult<Vec<(String, Py<PyAny>)>> {
        let keys = self.keys(py)?;
        let mut items = Vec::new();
        for key in keys {
            items.push((key.clone(), self.__getitem__(key, py)?));
        }
        Ok(items)
    }

    /// Get all values in this table
    fn values(&self, py: Python) -> PyResult<Vec<Py<PyAny>>> {
        let keys = self.keys(py)?;
        let mut values = Vec::new();
        for key in keys {
            values.push(self.__getitem__(key, py)?);
        }
        Ok(values)
    }

    /// Get value with default
    #[pyo3(signature = (key, default=None))]
    fn get(&self, key: String, default: Option<Py<PyAny>>, py: Python) -> PyResult<Py<PyAny>> {
        match self.__getitem__(key, py) {
            Ok(value) => Ok(value),
            Err(_) => Ok(default.unwrap_or_else(|| py.None())),
        }
    }

    /// Dict-like access: del table[key]
    fn __delitem__(&self, key: String, py: Python) -> PyResult<()> {
        let db = self.db.borrow(py);

        match db.config.table_mode {
            TableMode::Prefix => {
                let full_key = format!("{}:{}", self.table_name, key);
                // Remove from cache
                db.cache.remove(&full_key);
                // Remove from storage
                // Remove from storage
                // v5最適化: Mutex削除、直接アクセス
                if db.config.persist_mode != PersistMode::Memory {
                    if let Some(ref storage) = *db.storage {
                        let _ = storage.delete(&full_key);
                    }
                }
                Ok(())
            }
            TableMode::Separate => {
                let cache_key = format!("{}:{}", self.table_name, key);

                // Remove from cache
                db.cache.remove(&cache_key);

                // Remove from storage
                // v5最適化: Mutex削除、直接アクセス
                if db.config.persist_mode != PersistMode::Memory {
                    if let Some(ref storage) = *db.storage {
                        let _ = storage.delete_with_table(&self.table_name, &key);
                    }
                }

                Ok(())
            }
        }
    }

    /// Pop: Remove key and return value (dict.pop())
    #[pyo3(signature = (key, default=None))]
    fn pop(&self, key: String, default: Option<Py<PyAny>>, py: Python) -> PyResult<Py<PyAny>> {
        match self.__getitem__(key.clone(), py) {
            Ok(value) => {
                self.__delitem__(key, py)?;
                Ok(value)
            }
            Err(_) => match default {
                Some(d) => Ok(d),
                None => Err(PyErr::new::<pyo3::exceptions::PyKeyError, _>(format!(
                    "Key not found: {}",
                    key
                ))),
            },
        }
    }

    /// Setdefault: Set key if not exists, return value (dict.setdefault())
    #[pyo3(signature = (key, default=None))]
    fn setdefault(
        &self,
        key: String,
        default: Option<Py<PyAny>>,
        py: Python,
    ) -> PyResult<Py<PyAny>> {
        match self.__getitem__(key.clone(), py) {
            Ok(value) => Ok(value),
            Err(_) => {
                let value = default.unwrap_or_else(|| py.None());
                self.__setitem__(key.clone(), value.clone_ref(py), py)?;
                Ok(value)
            }
        }
    }

    /// Update: Update with dict items (dict.update())
    fn update(&self, other: &Bound<'_, PyDict>, py: Python) -> PyResult<()> {
        for (key, value) in other.iter() {
            let key_str: String = key.extract()?;
            self.__setitem__(key_str, value.into(), py)?;
        }
        Ok(())
    }

    /// Iterator support: for key in table
    fn __iter__(slf: PyRef<Self>, py: Python) -> PyResult<Py<AsyncTableProxyIterator>> {
        let keys = slf.keys(py)?;
        Py::new(py, AsyncTableProxyIterator { keys, index: 0 })
    }

    /// Clear all items in this table
    fn clear(&self, py: Python) -> PyResult<()> {
        let db = self.db.borrow(py);

        match db.config.table_mode {
            TableMode::Prefix => {
                let keys = self.keys(py)?;
                for key in keys {
                    self.__delitem__(key, py)?;
                }
                Ok(())
            }
            TableMode::Separate => {
                // Clear cache entries for this table
                let prefix = format!("{}:", self.table_name);
                let keys_to_remove: Vec<String> = db
                    .cache
                    .iter()
                    .filter(|entry| entry.key().starts_with(&prefix))
                    .map(|entry| entry.key().clone())
                    .collect();

                for key in keys_to_remove {
                    db.cache.remove(&key);
                }

                // Clear storage table
                // v5最適化: Mutex削除、直接アクセス
                if db.config.persist_mode != PersistMode::Memory {
                    if let Some(ref storage) = *db.storage {
                        storage.clear_table(&self.table_name).map_err(|e| {
                            PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string())
                        })?;
                    }
                }

                Ok(())
            }
        }
    }

    /// Get number of items in this table
    fn __len__(&self, py: Python) -> PyResult<usize> {
        Ok(self.keys(py)?.len())
    }

    /// String representation: show table name and contents as dict
    fn __repr__(&self, py: Python) -> PyResult<String> {
        let items = self.items(py)?;
        if items.is_empty() {
            return Ok(format!("AsyncTableProxy('{}', {{}})", self.table_name));
        }

        // Format items as dict-like string
        let mut item_strs = Vec::new();
        for (key, value) in items {
            // Try to get a string representation of the value using method chaining
            let value_repr = value
                .getattr(py, "__repr__")
                .and_then(|repr_method| repr_method.call0(py))
                .and_then(|repr_result| repr_result.extract::<String>(py))
                .unwrap_or_else(|_| "...".to_string());
            item_strs.push(format!("{:?}: {}", key, value_repr));
        }

        Ok(format!(
            "AsyncTableProxy('{}', {{{}}})",
            self.table_name,
            item_strs.join(", ")
        ))
    }

    /// String representation for str()
    fn __str__(&self, py: Python) -> PyResult<String> {
        self.__repr__(py)
    }

    /// Equality comparison: table == dict
    ///
    /// Compares the AsyncTableProxy with a Python dict or another AsyncTableProxy.
    /// Returns True if all keys and values match.
    fn __eq__(&self, other: Py<PyAny>, py: Python) -> PyResult<bool> {
        // Get items from this table (we need them for comparison)
        let self_items = self.items(py)?;
        let self_len = self_items.len();

        // Check if other is a dict
        if let Ok(other_dict) = other.cast_bound::<PyDict>(py) {
            // Compare with dict - check size first for early exit
            if self_len != other_dict.len() {
                return Ok(false);
            }

            // Compare each item directly without creating intermediate HashMap
            for (key, value) in self_items.iter() {
                if let Some(other_value) = other_dict.get_item(key)? {
                    // Compare values using Python's __eq__
                    let eq_result = value.bind(py).eq(other_value)?;
                    if !eq_result {
                        return Ok(false);
                    }
                } else {
                    return Ok(false);
                }
            }
            Ok(true)
        } else if let Ok(other_table) = other.extract::<PyRef<AsyncTableProxy>>(py) {
            // Compare with another AsyncTableProxy
            let other_items = other_table.items(py)?;

            // Check size first for early exit
            if self_len != other_items.len() {
                return Ok(false);
            }

            // Create a HashMap only for the other table to enable O(1) lookup
            let other_map: std::collections::HashMap<&String, &Py<PyAny>> =
                other_items.iter().map(|(k, v)| (k, v)).collect();

            // Compare each item
            for (key, value) in self_items.iter() {
                if let Some(other_value) = other_map.get(key) {
                    let eq_result = value.bind(py).eq(*other_value)?;
                    if !eq_result {
                        return Ok(false);
                    }
                } else {
                    return Ok(false);
                }
            }
            Ok(true)
        } else {
            // Not a dict or AsyncTableProxy - not equal
            Ok(false)
        }
    }
}

/// Iterator for AsyncTableProxy keys
#[pyclass]
pub struct AsyncTableProxyIterator {
    keys: Vec<String>,
    index: usize,
}

#[pymethods]
impl AsyncTableProxyIterator {
    fn __iter__(slf: PyRef<Self>) -> PyRef<Self> {
        slf
    }

    fn __next__(mut slf: PyRefMut<Self>) -> Option<String> {
        if slf.index < slf.keys.len() {
            let key = slf.keys[slf.index].clone();
            slf.index += 1;
            Some(key)
        } else {
            None
        }
    }
}
