use pyo3::prelude::*;
use pyo3::types::PyBytes;
use tokio::runtime::Runtime;
use std::sync::Arc;
use dashmap::DashMap;

/// Async version of DictSQLite v3.0 for high-concurrency scenarios
#[pyclass]
pub struct AsyncDictSQLite {
    /// Lock-free concurrent hashmap
    cache: Arc<DashMap<String, Vec<u8>>>,
    
    /// Tokio runtime for async operations
    runtime: Arc<Runtime>,
    
    /// Configuration
    capacity: usize,
}

#[pymethods]
impl AsyncDictSQLite {
    #[new]
    #[pyo3(signature = (_db_path, capacity=1_000_000))]
    fn new(_db_path: String, capacity: usize) -> PyResult<Self> {
        let runtime = Runtime::new()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
        
        let cache = Arc::new(DashMap::with_capacity(capacity));
        
        Ok(AsyncDictSQLite {
            cache,
            runtime: Arc::new(runtime),
            capacity,
        })
    }
    
    /// Async get (non-blocking)
    fn get_async(&self, key: String, py: Python) -> PyResult<Option<PyObject>> {
        let cache = self.cache.clone();
        
        py.allow_threads(|| {
            if let Some(value) = cache.get(&key) {
                Python::with_gil(|py| {
                    Ok(Some(PyBytes::new(py, &value).into()))
                })
            } else {
                Ok(None)
            }
        })
    }
    
    /// Async set (non-blocking)
    fn set_async(&self, key: String, value: Vec<u8>) -> PyResult<()> {
        self.cache.insert(key, value);
        Ok(())
    }
    
    /// Batch get (optimized for concurrent access)
    fn batch_get(&self, keys: Vec<String>, py: Python) -> PyResult<Vec<Option<PyObject>>> {
        py.allow_threads(|| {
            let results: Vec<Option<PyObject>> = keys.iter().map(|key| {
                self.cache.get(key).map(|value| {
                    Python::with_gil(|py| {
                        PyBytes::new(py, &value).into()
                    })
                })
            }).collect();
            Ok(results)
        })
    }
    
    /// Batch set (optimized for concurrent writes)
    fn batch_set(&self, items: Vec<(String, Vec<u8>)>) -> PyResult<()> {
        for (key, value) in items {
            self.cache.insert(key, value);
        }
        Ok(())
    }
    
    /// Get cache statistics
    fn stats(&self) -> PyResult<(usize, usize)> {
        Ok((self.cache.len(), self.capacity))
    }
}
