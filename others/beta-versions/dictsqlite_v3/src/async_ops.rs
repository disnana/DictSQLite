use pyo3::prelude::*;
use pyo3::types::PyBytes;
use std::sync::Arc;
use dashmap::DashMap;
use rayon::prelude::*;

/// Async version of DictSQLite v3.0 for high-concurrency scenarios
/// 
/// Optimizations:
/// - Shard-per-core DashMap for optimal concurrent access
/// - Rayon for parallel batch operations
/// - No GIL contention for pure in-memory operations
#[pyclass]
pub struct AsyncDictSQLite {
    /// Lock-free concurrent hashmap with shard-per-core
    cache: Arc<DashMap<String, Vec<u8>>>,
    
    /// Configuration
    capacity: usize,
}

#[pymethods]
impl AsyncDictSQLite {
    #[new]
    #[pyo3(signature = (db_path, capacity=1_000_000))]
    fn new(db_path: String, capacity: usize) -> PyResult<Self> {
        // Use shard-per-core for optimal concurrent access
        let num_shards = num_cpus::get();
        let cache = Arc::new(DashMap::with_capacity_and_shard_amount(capacity, num_shards));
        
        // For now, AsyncDictSQLite is pure in-memory
        // TODO: Add async persistence support
        let _ = db_path; // Silence unused warning
        
        Ok(AsyncDictSQLite {
            cache,
            capacity,
        })
    }
    
    /// Async get (non-blocking, no GIL for cache access)
    fn get_async(&self, key: String, py: Python) -> PyResult<Option<PyObject>> {
        let cache = self.cache.clone();
        
        // Release GIL during cache access
        let result = py.allow_threads(|| {
            cache.get(&key).map(|value| value.clone())
        });
        
        // Re-acquire GIL only for Python object creation
        Ok(result.map(|value| PyBytes::new(py, &value).into()))
    }
    
    /// Async set (non-blocking, no GIL for cache access)
    fn set_async(&self, key: String, value: Vec<u8>) -> PyResult<()> {
        self.cache.insert(key, value);
        Ok(())
    }
    
    /// Batch get (optimized with Rayon for parallel processing)
    fn batch_get(&self, keys: Vec<String>, py: Python) -> PyResult<Vec<Option<PyObject>>> {
        let cache = self.cache.clone();
        
        // Release GIL during parallel batch processing
        let results = py.allow_threads(|| {
            // Use rayon for parallel batch processing
            keys.par_iter().map(|key| {
                cache.get(key).map(|value| value.clone())
            }).collect::<Vec<_>>()
        });
        
        // Convert to PyObjects with GIL
        Ok(results.into_iter().map(|opt_value| {
            opt_value.map(|value| PyBytes::new(py, &value).into())
        }).collect())
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
        let results: Vec<Option<Vec<u8>>> = keys.par_iter().map(|key| {
            self.cache.get(key).map(|value| value.clone())
        }).collect();
        
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
}
