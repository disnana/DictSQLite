# Native Extension for DictSQLite

## Overview

DictSQLite now supports optional native extensions written in Rust for significantly improved performance. The native extension provides 10-100x speedup for core operations while maintaining full API compatibility.

## Features

- **High Performance**: 10-100x faster than pure Python implementation
- **Memory Efficient**: Optimized memory usage with native Rust data structures
- **Thread Safe**: Built with Rust's safety guarantees
- **Zero Runtime Dependencies**: Statically compiled, no additional dependencies
- **Automatic Fallback**: Seamlessly falls back to pure Python if native extension unavailable
- **Full Compatibility**: 100% API compatible with existing DictSQLite code

## Installation

### Option 1: With Pre-built Wheels (Recommended)

```bash
pip install dictsqlite
```

Pre-built wheels will be available for common platforms (Linux, macOS, Windows) on x86_64.

### Option 2: Build from Source

If you want to build the native extension yourself:

1. Install Rust from https://rustup.rs/

2. Clone the repository:
```bash
git clone https://github.com/disnana/DictSQLite.git
cd DictSQLite
```

3. Build the native extension:
```bash
./build_native.sh
```

Or manually:
```bash
pip install maturin
cd dictsqlite_native
maturin build --release
pip install target/wheels/*.whl
```

## Usage

The native extension is transparent to the user. Simply use DictSQLite as normal:

```python
from dictsqlite import DictSQLite

# The native extension will be used automatically if available
db = DictSQLite('mydb.db')
db['key'] = 'value'
```

### Checking Native Extension Status

```python
from dictsqlite.native_wrapper import is_native_available

if is_native_available():
    print("🚀 Using high-performance native Rust extension")
else:
    print("⚠️ Using pure Python fallback")
```

## Performance Comparison

Based on benchmarks from `dictsqlite-fastest/beta/investigate_v2_speedup.py`:

| Operation | Pure Python | Native Rust | Speedup |
|-----------|-------------|-------------|---------|
| Cache Read | 1M ops/sec | 50-100M ops/sec | **50-100x** |
| Cache Write | 800K ops/sec | 40-80M ops/sec | **50-100x** |
| SQLite Read | 100K ops/sec | 2-5M ops/sec | **20-50x** |
| SQLite Write | 50K ops/sec | 1-2M ops/sec | **20-40x** |
| Bulk Insert | 200K ops/sec | 5-10M ops/sec | **25-50x** |

*Note: Actual performance may vary based on hardware, data size, and workload patterns.*

## Architecture

The native extension consists of two main components:

### 1. NativeCache
- High-performance LRU cache using Rust's `lru` crate
- Lock-free read operations when possible
- Thread-safe with minimal contention

### 2. NativeSQLite  
- Optimized SQLite wrapper using `rusqlite`
- Prepared statement caching
- Batch operations optimization
- Connection pooling support

## Technical Details

### Why Rust?

- **Performance**: Comparable to C/C++ without manual memory management
- **Safety**: Memory safety without garbage collection
- **Concurrency**: Fearless concurrency with Rust's ownership model
- **Interop**: Excellent Python integration via PyO3
- **Tooling**: Cargo provides robust build and dependency management

### Alternative Considered

As noted in `investigate_v2_speedup.py`, we considered:
- ✅ **Rust** (chosen): Best performance/safety tradeoff, excellent Python interop
- ❌ Cython: Good performance but less safe, harder to maintain
- ❌ C++: Excellent performance but requires manual memory management
- ❌ Go: Good performance but larger runtime overhead
- ❌ Node.js: Not suitable for CPU-bound operations

## Development

### Building for Development

```bash
cd dictsqlite_native
maturin develop
```

### Running Tests

```bash
python -m pytest tests/ -v
```

### Benchmarking

```bash
python dictsqlite-fastest/beta/performance_benchmark.py
```

## Troubleshooting

### Native Extension Not Loading

If the native extension fails to load:

1. Check Python version (requires Python 3.9+)
2. Verify architecture compatibility (x86_64, aarch64)
3. Check for error messages in logs
4. The pure Python fallback will be used automatically

### Build Issues

If building from source fails:

1. Ensure Rust is installed: `rustc --version`
2. Update Rust: `rustup update`
3. Install build dependencies (varies by platform)
4. Check error messages for missing system libraries

## Contributing

Contributions to the native extension are welcome! Please ensure:

- Code follows Rust best practices
- All tests pass
- Performance improvements are benchmarked
- Changes maintain API compatibility

## License

The native extension is licensed under the same MIT license as DictSQLite.

## Future Enhancements

Planned improvements:
- [ ] Async/await support
- [ ] SIMD optimizations for bulk operations
- [ ] Custom allocator for better memory efficiency
- [ ] Zero-copy serialization where possible
- [ ] Advanced prefetching based on access patterns
