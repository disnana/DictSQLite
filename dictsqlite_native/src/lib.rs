use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyDict};
use rusqlite::{Connection, params};
use lru::LruCache;
use std::num::NonZeroUsize;
use std::sync::{Arc, Mutex};

/// Fast native cache implementation using Rust
#[pyclass]
struct NativeCache {
    cache: Arc<Mutex<LruCache<String, Vec<u8>>>>,
}

#[pymethods]
impl NativeCache {
    #[new]
    fn new(capacity: usize) -> Self {
        let cap = NonZeroUsize::new(capacity).unwrap_or(NonZeroUsize::new(1000).unwrap());
        NativeCache {
            cache: Arc::new(Mutex::new(LruCache::new(cap))),
        }
    }

    fn get(&self, key: &str, py: Python) -> PyResult<Option<PyObject>> {
        let cache = self.cache.lock().unwrap();
        match cache.peek(key) {
            Some(value) => Ok(Some(PyBytes::new(py, value).into())),
            None => Ok(None),
        }
    }

    fn put(&mut self, key: String, value: Vec<u8>) -> PyResult<()> {
        let mut cache = self.cache.lock().unwrap();
        cache.put(key, value);
        Ok(())
    }

    fn clear(&mut self) -> PyResult<()> {
        let mut cache = self.cache.lock().unwrap();
        cache.clear();
        Ok(())
    }

    fn len(&self) -> PyResult<usize> {
        let cache = self.cache.lock().unwrap();
        Ok(cache.len())
    }
}

/// Fast native SQLite wrapper
#[pyclass]
struct NativeSQLite {
    conn: Arc<Mutex<Connection>>,
    table_name: String,
}

#[pymethods]
impl NativeSQLite {
    #[new]
    fn new(db_path: &str, table_name: &str) -> PyResult<Self> {
        let conn = Connection::open(db_path)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
        
        // Create table if not exists
        let create_sql = format!(
            "CREATE TABLE IF NOT EXISTS {} (key TEXT PRIMARY KEY, value BLOB)",
            table_name
        );
        conn.execute(&create_sql, [])
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

        Ok(NativeSQLite {
            conn: Arc::new(Mutex::new(conn)),
            table_name: table_name.to_string(),
        })
    }

    fn get(&self, key: &str, py: Python) -> PyResult<Option<PyObject>> {
        let conn = self.conn.lock().unwrap();
        let query = format!("SELECT value FROM {} WHERE key = ?1", self.table_name);
        
        let mut stmt = conn.prepare(&query)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
        
        let result: Result<Vec<u8>, rusqlite::Error> = stmt.query_row(params![key], |row| row.get(0));
        
        match result {
            Ok(value) => Ok(Some(PyBytes::new(py, &value).into())),
            Err(rusqlite::Error::QueryReturnedNoRows) => Ok(None),
            Err(e) => Err(PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string())),
        }
    }

    fn put(&self, key: &str, value: Vec<u8>) -> PyResult<()> {
        let conn = self.conn.lock().unwrap();
        let insert_sql = format!(
            "INSERT OR REPLACE INTO {} (key, value) VALUES (?1, ?2)",
            self.table_name
        );
        
        conn.execute(&insert_sql, params![key, value])
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
        
        Ok(())
    }

    fn delete(&self, key: &str) -> PyResult<()> {
        let conn = self.conn.lock().unwrap();
        let delete_sql = format!("DELETE FROM {} WHERE key = ?1", self.table_name);
        
        conn.execute(&delete_sql, params![key])
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
        
        Ok(())
    }

    fn bulk_insert(&self, items: &PyDict) -> PyResult<()> {
        let conn = self.conn.lock().unwrap();
        let insert_sql = format!(
            "INSERT OR REPLACE INTO {} (key, value) VALUES (?1, ?2)",
            self.table_name
        );
        
        let tx = conn.unchecked_transaction()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
        
        {
            let mut stmt = tx.prepare(&insert_sql)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
            
            for (key, value) in items.iter() {
                let key_str: String = key.extract()?;
                let value_bytes: Vec<u8> = value.extract()?;
                stmt.execute(params![key_str, value_bytes])
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
            }
        }
        
        tx.commit()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
        
        Ok(())
    }

    fn keys(&self, py: Python) -> PyResult<Vec<String>> {
        let conn = self.conn.lock().unwrap();
        let query = format!("SELECT key FROM {}", self.table_name);
        
        let mut stmt = conn.prepare(&query)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
        
        let keys: Result<Vec<String>, rusqlite::Error> = stmt
            .query_map([], |row| row.get(0))?
            .collect();
        
        keys.map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))
    }
}

/// Python module initialization
#[pymodule]
fn dictsqlite_native(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<NativeCache>()?;
    m.add_class::<NativeSQLite>()?;
    Ok(())
}
