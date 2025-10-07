use dashmap::DashMap;
use std::sync::Arc;
use std::sync::atomic::{AtomicU64, Ordering};

/// High-performance hybrid cache with LRU eviction
pub struct HybridCache {
    /// Lock-free concurrent hashmap
    cache: Arc<DashMap<String, CacheEntry>>,
    
    /// Maximum capacity
    capacity: usize,
    
    /// Access counter for LRU
    access_counter: Arc<AtomicU64>,
}

#[derive(Clone)]
struct CacheEntry {
    value: Vec<u8>,
    last_access: u64,
    access_count: u64,
}

impl HybridCache {
    pub fn new(capacity: usize) -> Self {
        HybridCache {
            cache: Arc::new(DashMap::with_capacity(capacity)),
            capacity,
            access_counter: Arc::new(AtomicU64::new(0)),
        }
    }
    
    /// Get value (lock-free read)
    pub fn get(&self, key: &str) -> Option<Vec<u8>> {
        self.cache.get_mut(key).map(|mut entry| {
            let access_time = self.access_counter.fetch_add(1, Ordering::Relaxed);
            entry.last_access = access_time;
            entry.access_count += 1;
            entry.value.clone()
        })
    }
    
    /// Set value (lock-free write)
    pub fn set(&self, key: String, value: Vec<u8>) {
        let access_time = self.access_counter.fetch_add(1, Ordering::Relaxed);
        let entry = CacheEntry {
            value,
            last_access: access_time,
            access_count: 1,
        };
        
        self.cache.insert(key, entry);
        
        // Evict if over capacity
        if self.cache.len() > self.capacity {
            self.evict_lru();
        }
    }
    
    /// Evict least recently used entry
    fn evict_lru(&self) {
        let mut oldest_key: Option<String> = None;
        let mut oldest_access: u64 = u64::MAX;
        
        // Find LRU entry
        for entry in self.cache.iter() {
            if entry.value().last_access < oldest_access {
                oldest_access = entry.value().last_access;
                oldest_key = Some(entry.key().clone());
            }
        }
        
        // Remove oldest entry
        if let Some(key) = oldest_key {
            self.cache.remove(&key);
        }
    }
    
    /// Remove entry
    pub fn remove(&self, key: &str) -> Option<Vec<u8>> {
        self.cache.remove(key).map(|(_, entry)| entry.value)
    }
    
    /// Clear cache
    pub fn clear(&self) {
        self.cache.clear();
    }
    
    /// Get cache size
    pub fn len(&self) -> usize {
        self.cache.len()
    }
    
    /// Check if empty
    pub fn is_empty(&self) -> bool {
        self.cache.is_empty()
    }
}
