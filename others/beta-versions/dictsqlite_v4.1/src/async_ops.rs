use dashmap::DashMap;
use pyo3::prelude::*;
use pyo3::types::PyBytes;
use rayon::prelude::*;
use std::sync::{Arc, Mutex};

use crate::{Config, PersistMode, StorageEngine};

/// Async version of DictSQLite v4.1 for high-concurrency scenarios
///
/// Optimizations:
/// - Shard-per-core DashMap for optimal concurrent access
/// - Rayon for parallel batch operations
/// - No GIL contention for pure in-memory operations
/// - Optional persistence support (v4.1 feature)
#[pyclass]
pub struct AsyncDictSQLite {
    /// Lock-free concurrent hashmap with shard-per-core
    cache: Arc<DashMap<String, Vec<u8>>>,

    /// Storage engine for persistence (optional)
    storage: Arc<Mutex<Option<StorageEngine>>>,

    /// Configuration
    config: Config,

    /// Capacity
    capacity: usize,
}

#[pymethods]
impl AsyncDictSQLite {
    #[new]
    #[pyo3(signature = (db_path, capacity=1_000_000, persist_mode="lazy"))]
    fn new(db_path: String, capacity: usize, persist_mode: &str) -> PyResult<Self> {
        use std::str::FromStr;

        // Use shard-per-core for optimal concurrent access
        let num_shards = num_cpus::get();
        let cache = Arc::new(DashMap::with_capacity_and_shard_amount(
            capacity, num_shards,
        ));

        // Create config
        let mut config = Config::default();
        config.hot_tier_capacity = capacity;
        config.persist_mode = PersistMode::from_str(persist_mode)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e))?;

        // Initialize storage engine
        let storage = if config.persist_mode == PersistMode::Memory {
            Arc::new(Mutex::new(None))
        } else {
            Arc::new(Mutex::new(Some(
                StorageEngine::new(&db_path, &config)
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?,
            )))
        };

        Ok(AsyncDictSQLite {
            cache,
            storage,
            config,
            capacity,
        })
    }

    /// Async get (non-blocking, no GIL for cache access)
    /// Now with storage fallback for persistence modes
    fn get_async(&self, key: String, py: Python) -> PyResult<Option<PyObject>> {
        let cache = self.cache.clone();

        // Release GIL during cache access
        let result = py.allow_threads(|| cache.get(&key).map(|value| value.clone()));

        // If found in cache, return immediately
        if let Some(value) = result {
            return Ok(Some(PyBytes::new(py, &value).into()));
        }

        // Fallback to storage if not in memory mode
        if self.config.persist_mode != PersistMode::Memory {
            let storage_guard = self.storage.lock().unwrap();
            if let Some(ref storage) = *storage_guard {
                if let Ok(Some(value)) = storage.get(&key) {
                    // Promote to cache for future access
                    drop(storage_guard);
                    self.cache.insert(key, value.clone());
                    return Ok(Some(PyBytes::new(py, &value).into()));
                }
            }
        }

        Ok(None)
    }

    /// Async set (non-blocking, no GIL for cache access)
    /// Now with optional persistence
    fn set_async(&self, key: String, value: Vec<u8>) -> PyResult<()> {
        self.cache.insert(key.clone(), value.clone());

        // Immediate write for WriteThrough mode
        if self.config.persist_mode == PersistMode::WriteThrough {
            let mut storage_guard = self.storage.lock().unwrap();
            if let Some(ref mut storage) = *storage_guard {
                storage
                    .set(&key, &value)
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
            }
        }

        Ok(())
    }

    /// Batch get (optimized with Rayon for parallel processing)
    fn batch_get(&self, keys: Vec<String>, py: Python) -> PyResult<Vec<Option<PyObject>>> {
        let cache = self.cache.clone();

        // Release GIL during parallel batch processing
        let results = py.allow_threads(|| {
            // Use rayon for parallel batch processing
            keys.par_iter()
                .map(|key| cache.get(key).map(|value| value.clone()))
                .collect::<Vec<_>>()
        });

        // Convert to PyObjects with GIL
        Ok(results
            .into_iter()
            .map(|opt_value| opt_value.map(|value| PyBytes::new(py, &value).into()))
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
    fn flush(&self) -> PyResult<()> {
        if self.config.persist_mode == PersistMode::Memory {
            return Ok(());
        }

        let mut storage_guard = self.storage.lock().unwrap();
        if let Some(ref mut storage) = *storage_guard {
            for entry in self.cache.iter() {
                storage
                    .set(entry.key(), entry.value())
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
            }
        }
        Ok(())
    }

    /// Close and flush if needed
    fn close(&self) -> PyResult<()> {
        if self.config.persist_mode == PersistMode::Lazy {
            self.flush()?;
        }
        Ok(())
    }
}
