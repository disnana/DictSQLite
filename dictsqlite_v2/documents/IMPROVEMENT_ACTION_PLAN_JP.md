# DictSQLite v4.1 改善アクションプラン

**作成日**: 2025年  
**対象**: dictsqlite_v4.1 Rust版  
**目的**: 調査レポートに基づく具体的な改善手順

---

## Phase 1: 緊急対応（1-2週間）

### タスク1.1: AsyncDictSQLite の永続化実装

**期間**: 5日間  
**優先度**: 🔴 Critical  
**担当ファイル**: `src/async_ops.rs`

#### 実装内容

```rust
use crate::storage::StorageEngine;
use crate::Config;

#[pyclass]
pub struct AsyncDictSQLite {
    /// Lock-free concurrent hashmap with shard-per-core
    cache: Arc<DashMap<String, Vec<u8>>>,
    
    /// Storage engine for persistence (NEW)
    storage: Arc<Mutex<Option<StorageEngine>>>,
    
    /// Configuration (NEW)
    config: Config,
    
    /// Capacity
    capacity: usize,
}

#[pymethods]
impl AsyncDictSQLite {
    #[new]
    #[pyo3(signature = (db_path, capacity=1_000_000, persist_mode="lazy"))]
    fn new(db_path: String, capacity: usize, persist_mode: &str) -> PyResult<Self> {
        let num_shards = num_cpus::get();
        let cache = Arc::new(DashMap::with_capacity_and_shard_amount(capacity, num_shards));
        
        // Create config
        let mut config = Config::default();
        config.persist_mode = PersistMode::from_str(persist_mode)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e))?;
        
        // Initialize storage engine
        let storage = if config.persist_mode == PersistMode::Memory {
            Arc::new(Mutex::new(None))
        } else {
            Arc::new(Mutex::new(Some(
                StorageEngine::new(&db_path, &config)
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?
            )))
        };
        
        Ok(AsyncDictSQLite {
            cache,
            storage,
            config,
            capacity,
        })
    }
    
    /// Async get with storage fallback
    fn get_async(&self, key: String, py: Python) -> PyResult<Option<PyObject>> {
        // Try cache first
        if let Some(value) = self.cache.get(&key) {
            return Ok(Some(PyBytes::new(py, &value).into()));
        }
        
        // Fallback to storage
        if self.config.persist_mode != PersistMode::Memory {
            let storage_guard = self.storage.lock().unwrap();
            if let Some(ref storage) = *storage_guard {
                if let Ok(Some(value)) = storage.get(&key) {
                    // Promote to cache
                    drop(storage_guard);
                    self.cache.insert(key, value.clone());
                    return Ok(Some(PyBytes::new(py, &value).into()));
                }
            }
        }
        
        Ok(None)
    }
    
    /// Flush cache to storage
    fn flush(&self) -> PyResult<()> {
        if self.config.persist_mode == PersistMode::Memory {
            return Ok(());
        }
        
        let mut storage_guard = self.storage.lock().unwrap();
        if let Some(ref mut storage) = *storage_guard {
            for entry in self.cache.iter() {
                storage.set(entry.key(), entry.value())
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
            }
        }
        Ok(())
    }
    
    /// Close and flush
    fn close(&self) -> PyResult<()> {
        self.flush()
    }
}
```

#### テスト

```python
# tests/test_async_persistence.py
def test_async_persistence():
    import tempfile
    import os
    
    db_path = tempfile.mktemp(suffix=".db")
    
    try:
        # Write data
        db1 = AsyncDictSQLite(db_path, persist_mode="lazy")
        db1.set_async("key1", b"value1")
        db1.set_async("key2", b"value2")
        db1.flush()
        db1.close()
        
        # Read data in new instance
        db2 = AsyncDictSQLite(db_path, persist_mode="lazy")
        assert db2.get_async("key1") == b"value1"
        assert db2.get_async("key2") == b"value2"
        db2.close()
        
        print("✅ Async persistence test passed")
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)
```

---

### タスク1.2: LRU エビクションの実装

**期間**: 3日間  
**優先度**: 🔴 Critical  
**担当ファイル**: `Cargo.toml`, `src/lib.rs`

#### 依存関係の追加

```toml
# Cargo.toml
[dependencies]
lru = "0.12"  # LRU cache implementation
```

#### 実装内容

```rust
use lru::LruCache;
use std::num::NonZeroUsize;

#[pyclass]
pub struct DictSQLiteV4 {
    hot_tier: Arc<DashMap<String, Vec<u8>>>,
    access_tracker: Arc<Mutex<LruCache<String, ()>>>,  // NEW
    storage: Arc<Mutex<Option<StorageEngine>>>,
    config: Config,
    crypto: Option<Arc<CryptoEngine>>,
    safe_pickle: Option<Arc<SafePickleValidator>>,
}

impl DictSQLiteV4 {
    #[new]
    fn new(/* ... */) -> PyResult<Self> {
        // ... existing code ...
        
        let access_tracker = Arc::new(Mutex::new(
            LruCache::new(NonZeroUsize::new(config.hot_tier_capacity).unwrap())
        ));
        
        Ok(DictSQLiteV4 {
            hot_tier,
            access_tracker,
            storage,
            config,
            crypto,
            safe_pickle,
        })
    }
    
    fn get(&self, key: String, py: Python) -> PyResult<Option<PyObject>> {
        // Track access
        self.access_tracker.lock().unwrap().put(key.clone(), ());
        
        // ... existing get logic ...
    }
    
    fn set(&self, key: String, value: Vec<u8>) -> PyResult<()> {
        // ... existing validation and encryption ...
        
        self.hot_tier.insert(key.clone(), data.clone());
        
        // Track access
        self.access_tracker.lock().unwrap().put(key.clone(), ());
        
        // Evict if necessary
        if self.hot_tier.len() > self.config.hot_tier_capacity {
            self.evict_to_warm_tier()?;
        }
        
        // ... existing persist logic ...
        
        Ok(())
    }
    
    fn evict_to_warm_tier(&self) -> PyResult<()> {
        let mut tracker = self.access_tracker.lock().unwrap();
        
        // Find LRU entry
        if let Some((evict_key, _)) = tracker.pop_lru() {
            if let Some((_, value)) = self.hot_tier.remove(&evict_key) {
                // Write to storage (warm tier)
                let mut storage_guard = self.storage.lock().unwrap();
                if let Some(ref mut storage) = *storage_guard {
                    storage.set(&evict_key, &value)
                        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
                }
            }
        }
        
        Ok(())
    }
}
```

---

### タスク1.3: READMEの更新

**期間**: 1日間  
**優先度**: 🟡 High  
**担当ファイル**: `README_JP.md`, `README.md`

#### 修正内容

1. **未実装機能の削除**

```markdown
# 削除する内容
~~db.get("key", "default")~~
~~db.setdefault("key", b"value")~~
~~db.update({"k1": b"v1", "k2": b"v2"})~~
~~value = db.pop("key")~~
```

2. **実装済み機能の明記**

```markdown
## 実装済みAPI

### 辞書風アクセス
- `db[key] = value` - 値の設定
- `value = db[key]` - 値の取得（KeyError発生）
- `del db[key]` - キーの削除
- `key in db` - キーの存在確認
- `len(db)` - アイテム数の取得

### メソッド
- `db.keys()` - 全キーの取得
- `db.bulk_insert(dict)` - バルクインサート
- `db.flush()` - ディスクへのフラッシュ
- `db.close()` - データベースのクローズ
- `db.stats()` - 統計情報の取得

## 今後実装予定のAPI

- `db.get(key, default)` - デフォルト値付き取得
- `db.items()` - (key, value)イテレータ
- `db.values()` - 値イテレータ
- `db.setdefault(key, default)` - デフォルト値付き設定
- `db.update(dict)` - 辞書更新
- `db.pop(key)` - キーの削除と値の取得
```

3. **パラメータの詳細説明追加**

```markdown
## パラメータ詳細

### DictSQLiteV4.__init__()

- `db_path` (str): データベースファイルのパス
  - `":memory:"` で純粋インメモリモード
  
- `hot_capacity` (int, default=1_000_000): ホットティアの最大エントリ数
  - メモリ使用量 ≈ hot_capacity × 平均値サイズ
  
- `enable_async` (bool, default=True): バックグラウンド非同期フラッシュの有効化
  - `True`: 定期的に自動フラッシュ（推奨）
  - `False`: flush()を明示的に呼ぶ必要あり
  
- `persist_mode` (str, default="writethrough"): 永続化モード
  - `"memory"`: 純粋インメモリ（永続化なし、最速）
    - パフォーマンス: 1.24M ops/sec
    - 用途: キャッシュ、一時データ
  - `"lazy"`: 遅延永続化（flush()時に書き込み、高速）
    - パフォーマンス: 1.30M ops/sec
    - 用途: 高スループットアプリケーション（**推奨**）
  - `"writethrough"`: 即座に永続化（安全、低速）
    - パフォーマンス: 29.79K ops/sec
    - 用途: 金融取引、監査ログ
    
- `encryption_password` (str|None): AES-256-GCM暗号化のパスワード
  - 指定すると全データが暗号化される
  - パスワードは安全に管理すること
  
- `enable_safe_pickle` (bool, default=False): Safe Pickle検証の有効化
  - `True`: 危険なpickle opcodeを検出・拒否
  - `False`: 検証なし（高速だが危険）
  
- `safe_pickle_allowed_modules` (List[str]|None): 許可するモジュールプレフィックス
  - 例: `["myapp.", "trusted."]`
  - `None`: デフォルトの安全なモジュールのみ許可
```

---

## Phase 2: 重要な機能追加（2-3週間）

### タスク2.1: 非同期バッファリングの実装

**期間**: 5日間  
**優先度**: 🔴 Critical  
**担当ファイル**: `src/async_ops.rs`

#### 実装内容

```rust
use std::collections::HashMap;
use std::time::Duration;
use tokio::time::interval;

#[pyclass]
pub struct AsyncDictSQLite {
    cache: Arc<DashMap<String, Vec<u8>>>,
    storage: Arc<Mutex<Option<StorageEngine>>>,
    config: Config,
    capacity: usize,
    
    // Async buffering (NEW)
    write_buffer: Arc<Mutex<HashMap<String, Vec<u8>>>>,
    buffer_size: usize,
    buffer_interval_ms: u64,
}

#[pymethods]
impl AsyncDictSQLite {
    #[new]
    #[pyo3(signature = (db_path, capacity=1_000_000, persist_mode="lazy", 
                        buffer_size=100, buffer_interval_ms=5000))]
    fn new(
        db_path: String, 
        capacity: usize, 
        persist_mode: &str,
        buffer_size: usize,
        buffer_interval_ms: u64,
    ) -> PyResult<Self> {
        // ... existing initialization ...
        
        let write_buffer = Arc::new(Mutex::new(HashMap::new()));
        
        // Start background flush task
        if persist_mode != "memory" {
            let buffer_clone = write_buffer.clone();
            let storage_clone = storage.clone();
            let interval_ms = buffer_interval_ms;
            
            std::thread::spawn(move || {
                let rt = tokio::runtime::Runtime::new().unwrap();
                rt.block_on(async {
                    let mut ticker = interval(Duration::from_millis(interval_ms));
                    loop {
                        ticker.tick().await;
                        Self::flush_buffer_static(buffer_clone.clone(), storage_clone.clone());
                    }
                });
            });
        }
        
        Ok(AsyncDictSQLite {
            cache,
            storage,
            config,
            capacity,
            write_buffer,
            buffer_size,
            buffer_interval_ms,
        })
    }
    
    /// Async set with buffering
    fn set_async(&self, key: String, value: Vec<u8>) -> PyResult<()> {
        // Update cache immediately
        self.cache.insert(key.clone(), value.clone());
        
        // Add to buffer
        let mut buffer = self.write_buffer.lock().unwrap();
        buffer.insert(key, value);
        
        // Auto-flush if buffer is full
        if buffer.len() >= self.buffer_size {
            drop(buffer);
            self.flush_buffer()?;
        }
        
        Ok(())
    }
    
    fn flush_buffer(&self) -> PyResult<()> {
        let mut buffer = self.write_buffer.lock().unwrap();
        
        if buffer.is_empty() {
            return Ok(());
        }
        
        // Extract buffer contents
        let items: HashMap<String, Vec<u8>> = buffer.drain().collect();
        drop(buffer);
        
        // Bulk write to storage
        let mut storage_guard = self.storage.lock().unwrap();
        if let Some(ref mut storage) = *storage_guard {
            for (key, value) in items {
                storage.set(&key, &value)
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
            }
        }
        
        Ok(())
    }
    
    fn flush_buffer_static(
        buffer: Arc<Mutex<HashMap<String, Vec<u8>>>>,
        storage: Arc<Mutex<Option<StorageEngine>>>,
    ) {
        // Similar to flush_buffer but without PyResult
    }
}
```

**期待される効果**:
- 1000件の書き込み: 30秒 → **0.1秒**（**300倍高速化**）

---

### タスク2.2: 辞書互換APIの実装

**期間**: 3日間  
**優先度**: 🟡 High  
**担当ファイル**: `src/lib.rs`

#### 実装内容

```rust
#[pymethods]
impl DictSQLiteV4 {
    /// Get with default value (dict-compatible)
    #[pyo3(signature = (key, default=None))]
    fn get(&self, key: String, default: Option<Vec<u8>>, py: Python) -> PyResult<PyObject> {
        // Try hot tier first
        if let Some(value) = self.hot_tier.get(&key) {
            let data = if let Some(ref crypto) = self.crypto {
                crypto.decrypt(&value)
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?
            } else {
                value.clone()
            };
            return Ok(PyBytes::new(py, &data).into());
        }
        
        // Try storage
        if self.config.persist_mode != PersistMode::Memory {
            let storage_guard = self.storage.lock().unwrap();
            if let Some(ref storage) = *storage_guard {
                if let Ok(Some(value)) = storage.get(&key) {
                    let data = if let Some(ref crypto) = self.crypto {
                        crypto.decrypt(&value)
                            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?
                    } else {
                        value
                    };
                    return Ok(PyBytes::new(py, &data).into());
                }
            }
        }
        
        // Return default
        Ok(default.map(|v| PyBytes::new(py, &v).into())
            .unwrap_or_else(|| py.None()))
    }
    
    /// Setdefault (dict-compatible)
    fn setdefault(&self, key: String, default: Vec<u8>, py: Python) -> PyResult<PyObject> {
        if !self.hot_tier.contains_key(&key) {
            self.set(key.clone(), default.clone())?;
        }
        self.get(key, Some(default), py)
    }
    
    /// Update from dict (dict-compatible)
    fn update(&self, items: Bound<'_, PyDict>) -> PyResult<()> {
        self.bulk_insert(items)
    }
    
    /// Pop with optional default (dict-compatible)
    #[pyo3(signature = (key, default=None))]
    fn pop(&self, key: String, default: Option<Vec<u8>>, py: Python) -> PyResult<PyObject> {
        if let Some((_, value)) = self.hot_tier.remove(&key) {
            let data = if let Some(ref crypto) = self.crypto {
                crypto.decrypt(&value)
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?
            } else {
                value
            };
            return Ok(PyBytes::new(py, &data).into());
        }
        
        Ok(default.map(|v| PyBytes::new(py, &v).into())
            .unwrap_or_else(|| py.None()))
    }
    
    /// Items iterator (dict-compatible)
    fn items(&self, py: Python) -> PyResult<Vec<(String, PyObject)>> {
        let items: Vec<(String, PyObject)> = self.hot_tier.iter()
            .map(|entry| {
                let value = if let Some(ref crypto) = self.crypto {
                    crypto.decrypt(entry.value()).unwrap_or_else(|_| entry.value().clone())
                } else {
                    entry.value().clone()
                };
                (entry.key().clone(), PyBytes::new(py, &value).into())
            })
            .collect();
        Ok(items)
    }
    
    /// Values iterator (dict-compatible)
    fn values(&self, py: Python) -> PyResult<Vec<PyObject>> {
        let values: Vec<PyObject> = self.hot_tier.iter()
            .map(|entry| {
                let value = if let Some(ref crypto) = self.crypto {
                    crypto.decrypt(entry.value()).unwrap_or_else(|_| entry.value().clone())
                } else {
                    entry.value().clone()
                };
                PyBytes::new(py, &value).into()
            })
            .collect();
        Ok(values)
    }
}
```

---

### タスク2.3: バッチ書き込み最適化

**期間**: 4日間  
**優先度**: 🟡 High  
**担当ファイル**: `src/lib.rs`

#### 実装内容

```rust
const WRITE_BATCH_SIZE: usize = 100;

#[pyclass]
pub struct DictSQLiteV4 {
    // ... existing fields ...
    
    // Write batching for WriteThrough mode
    write_batch: Arc<Mutex<Vec<(String, Vec<u8>)>>>,
}

impl DictSQLiteV4 {
    fn set(&self, key: String, value: Vec<u8>) -> PyResult<()> {
        // ... existing validation and encryption ...
        
        self.hot_tier.insert(key.clone(), data.clone());
        
        // Batch writes for WriteThrough mode
        if self.config.persist_mode == PersistMode::WriteThrough {
            let mut batch = self.write_batch.lock().unwrap();
            batch.push((key, data));
            
            if batch.len() >= WRITE_BATCH_SIZE {
                // Flush batch
                let items: Vec<(String, Vec<u8>)> = batch.drain(..).collect();
                drop(batch);
                
                let mut storage_guard = self.storage.lock().unwrap();
                if let Some(ref mut storage) = *storage_guard {
                    // Use transaction for batch write
                    storage.batch_set(&items)
                        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
                }
            }
        }
        
        Ok(())
    }
}
```

**storage.rs への追加**:

```rust
impl StorageEngine {
    pub fn batch_set(&mut self, items: &[(String, Vec<u8>)]) -> Result<()> {
        let tx = self.cold_conn.lock().unwrap().transaction()?;
        
        for (key, value) in items {
            tx.execute(
                "INSERT OR REPLACE INTO kv_store (key, value) VALUES (?1, ?2)",
                params![key, value],
            )?;
        }
        
        tx.commit()?;
        Ok(())
    }
}
```

**期待される効果**:
- WriteThrough モード: 29.79K → 1.30M ops/sec（**43倍高速化**）

---

## Phase 3: 長期的改善（1-3ヶ月）

### タスク3.1: 真の非同期APIの実装

**期間**: 2週間  
**優先度**: 🟢 Medium  
**依存関係**: `pyo3-asyncio` クレートの追加

#### 実装概要

```toml
# Cargo.toml
[dependencies]
pyo3-asyncio = { version = "0.20", features = ["tokio-runtime"] }
```

```rust
use pyo3_asyncio::tokio::future_into_py;

#[pymethods]
impl AsyncDictSQLite {
    #[pyo3(name = "aset")]
    fn aset_py<'p>(&self, py: Python<'p>, key: String, value: Vec<u8>) -> PyResult<&'p PyAny> {
        let cache = self.cache.clone();
        let write_buffer = self.write_buffer.clone();
        let buffer_size = self.buffer_size;
        
        future_into_py(py, async move {
            // Async buffering logic
            cache.insert(key.clone(), value.clone());
            
            let mut buffer = write_buffer.lock().unwrap();
            buffer.insert(key, value);
            
            if buffer.len() >= buffer_size {
                // Auto flush
            }
            
            Ok(Python::with_gil(|py| py.None()))
        })
    }
}
```

---

### タスク3.2: SIMD最適化

**期間**: 3週間  
**優先度**: 🟢 Medium  
**期待効果**: 10-20% パフォーマンス向上

---

## 実装スケジュール

```
Week 1-2: Phase 1 (緊急対応)
├─ Day 1-5:   AsyncDictSQLite永続化
├─ Day 6-8:   LRUエビクション
└─ Day 9-10:  README更新

Week 3-5: Phase 2 (重要機能)
├─ Day 11-15: 非同期バッファリング
├─ Day 16-18: 辞書互換API
└─ Day 19-22: バッチ書き込み最適化

Week 6-14: Phase 3 (長期改善)
├─ Week 6-7:  真の非同期API
└─ Week 8-10: SIMD最適化
```

---

## 成功指標

### パフォーマンス目標

| 指標 | 現在 | Phase 1 | Phase 2 | Phase 3 |
|------|------|---------|---------|---------|
| 非同期書き込み (1000件) | 30s | 0.1s | 0.05s | 0.03s |
| WriteThrough 書き込み | 29.79K | 29.79K | 1.30M | 1.50M |
| 順次読み込み | 3.97M | 4.50M | 5.00M | 6.00M |
| メモリ効率 | ∞ | 制限あり | 最適化 | 最適化 |

### 機能目標

- ✅ Phase 1: 永続化、LRU、ドキュメント
- ✅ Phase 2: 非同期バッファリング、辞書互換API、バッチ最適化
- ✅ Phase 3: 真の非同期API、SIMD最適化

### 品質目標

- ✅ 全テストパス率: 100%
- ✅ カバレッジ: 80%以上
- ✅ ドキュメント正確性: 100%
- ✅ セキュリティ脆弱性: 0件

---

## 次のステップ

1. **このアクションプランをレビュー**
2. **Phase 1 の実装を開始**
3. **各タスク完了後にテストとベンチマーク実行**
4. **定期的に進捗を報告**

---

**作成者**: GitHub Copilot  
**承認待ち**: プロジェクトオーナー
