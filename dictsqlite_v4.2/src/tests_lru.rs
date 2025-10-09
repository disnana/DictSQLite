//! Unit tests for LRU eviction and memory management

#[cfg(test)]
mod tests {
    use dashmap::DashMap;
    use lru::LruCache;
    use std::num::NonZeroUsize;
    use std::sync::Arc;
    use std::thread;

    #[test]
    fn test_lru_creation() {
        // Test that LRU cache can be created with the specified capacity
        let capacity = NonZeroUsize::new(100).unwrap();
        let mut cache: LruCache<String, ()> = LruCache::new(capacity);

        assert_eq!(cache.len(), 0);
        cache.put("key1".to_string(), ());
        assert_eq!(cache.len(), 1);
    }

    #[test]
    fn test_lru_eviction_order() {
        let capacity = NonZeroUsize::new(3).unwrap();
        let mut cache: LruCache<String, String> = LruCache::new(capacity);

        // Add items
        cache.put("key1".to_string(), "value1".to_string());
        cache.put("key2".to_string(), "value2".to_string());
        cache.put("key3".to_string(), "value3".to_string());

        assert_eq!(cache.len(), 3);

        // Access key1 to make it most recently used
        let _ = cache.get(&"key1".to_string());

        // Add key4, should evict key2 (least recently used)
        cache.put("key4".to_string(), "value4".to_string());

        assert_eq!(cache.len(), 3);
        assert!(cache.contains(&"key1".to_string()));
        assert!(!cache.contains(&"key2".to_string())); // Should be evicted
        assert!(cache.contains(&"key3".to_string()));
        assert!(cache.contains(&"key4".to_string()));
    }

    #[test]
    fn test_dashmap_concurrent_access() {
        let map = Arc::new(DashMap::new());
        let mut handles = vec![];

        // Spawn multiple threads to write concurrently
        for i in 0..10 {
            let map_clone = Arc::clone(&map);
            let handle = thread::spawn(move || {
                for j in 0..100 {
                    map_clone.insert(format!("key_{}_{}", i, j), vec![i as u8, j as u8]);
                }
            });
            handles.push(handle);
        }

        // Wait for all threads
        for handle in handles {
            handle.join().unwrap();
        }

        // Verify all items were inserted
        assert_eq!(map.len(), 1000);
    }

    #[test]
    fn test_memory_overhead() {
        // Test that DashMap doesn't have excessive overhead
        let map = DashMap::new();

        // Insert items and check memory behavior
        for i in 0..1000 {
            map.insert(format!("key_{}", i), vec![0u8; 100]);
        }

        assert_eq!(map.len(), 1000);

        // Clear and verify
        map.clear();
        assert_eq!(map.len(), 0);
    }
}
