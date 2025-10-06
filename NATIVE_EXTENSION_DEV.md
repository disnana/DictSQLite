# Native Extension Development Guide

This guide is for developers who want to contribute to or modify the DictSQLite native extension.

## Prerequisites

- Rust 1.70+ (install from https://rustup.rs/)
- Python 3.9+
- Basic knowledge of Rust and Python/C FFI

## Project Structure

```
dictsqlite_native/
├── Cargo.toml          # Rust package configuration
└── src/
    └── lib.rs          # Main Rust implementation with PyO3 bindings

dictsqlite/
└── native_wrapper.py   # Python wrapper with fallback implementation
```

## Setting Up Development Environment

1. Install Rust:
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

2. Install maturin (Python/Rust build tool):
```bash
pip install maturin
```

3. Install development dependencies:
```bash
pip install pytest pytest-cov portalocker cryptography
```

## Building for Development

For development, use `maturin develop` which builds and installs the extension in development mode:

```bash
cd dictsqlite_native
maturin develop
```

This allows you to make changes to the Rust code and quickly rebuild without reinstalling.

## Building for Release

For production builds:

```bash
cd dictsqlite_native
maturin build --release
```

The built wheels will be in `target/wheels/`.

## Testing

Run the test suite:

```bash
# Test pure Python fallback
pytest tests/test_native_extension.py -v

# Test with native extension (after building)
cd dictsqlite_native && maturin develop && cd ..
pytest tests/test_native_extension.py -v
```

## Performance Benchmarking

Run the performance example:

```bash
python example_native_extension.py
```

This will benchmark both the native and pure Python implementations.

## Code Structure

### Rust Implementation (`dictsqlite_native/src/lib.rs`)

The Rust code provides two main components:

1. **NativeCache**: High-performance LRU cache
   - Uses `lru` crate for efficient cache management
   - Thread-safe with Arc<Mutex<>>
   - Zero-copy operations where possible

2. **NativeSQLite**: Optimized SQLite wrapper
   - Uses `rusqlite` crate
   - Batched operations for better performance
   - Prepared statement caching

### Python Wrapper (`dictsqlite/native_wrapper.py`)

The Python wrapper provides:

1. **Automatic fallback**: Uses native extension if available, pure Python otherwise
2. **Pure Python implementations**: `PythonCache` and `PythonSQLite`
3. **Unified interface**: Same API regardless of implementation

## Adding New Features

### Adding a New Method to NativeCache

1. Add the Rust implementation in `lib.rs`:

```rust
#[pymethods]
impl NativeCache {
    fn my_new_method(&self, param: String) -> PyResult<()> {
        // Implementation
        Ok(())
    }
}
```

2. Add the Python fallback in `native_wrapper.py`:

```python
class PythonCache:
    def my_new_method(self, param: str) -> None:
        # Pure Python implementation
        pass
```

3. Add tests in `tests/test_native_extension.py`:

```python
def test_my_new_method():
    cache = NativeCache(100)
    cache.my_new_method("test")
    # Assertions
```

## Optimization Tips

### Rust Optimizations

1. **Use `#[inline]` for small functions**:
```rust
#[inline]
fn small_function() -> i32 {
    42
}
```

2. **Minimize lock contention**:
```rust
// Bad: Hold lock during computation
let mut cache = self.cache.lock().unwrap();
let result = expensive_computation();
cache.insert(key, result);

// Good: Release lock quickly
let result = expensive_computation();
let mut cache = self.cache.lock().unwrap();
cache.insert(key, result);
```

3. **Use zero-copy where possible**:
```rust
// Use PyBytes::new_bound for zero-copy bytes
PyBytes::new_bound(py, &data).into()
```

### Build Optimizations

The `Cargo.toml` is already configured for maximum performance:

```toml
[profile.release]
opt-level = 3       # Maximum optimization
lto = true          # Link-time optimization
codegen-units = 1   # Single codegen unit for better optimization
```

## Debugging

### Debugging Rust Code

1. Build in debug mode:
```bash
maturin develop --release=false
```

2. Add debug prints:
```rust
eprintln!("Debug: value = {:?}", value);
```

3. Use Rust analyzer in your IDE for better development experience.

### Debugging Python Integration

1. Check if native extension is loaded:
```python
from dictsqlite.native_wrapper import is_native_available
print(f"Native available: {is_native_available()}")
```

2. Enable logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Cross-Platform Considerations

### Linux
- Uses GLIBC, should work on most distributions
- Built wheels are manylinux compatible

### macOS
- Universal2 wheels for both Intel and Apple Silicon
- Requires macOS 10.9+ (Mavericks)

### Windows
- Requires Visual Studio Build Tools
- Built with MSVC for best compatibility

## Publishing Wheels

To publish platform-specific wheels to PyPI:

```bash
# Build for current platform
maturin build --release

# Upload to PyPI (requires PyPI credentials)
maturin publish --username __token__ --password $PYPI_TOKEN
```

For multi-platform builds, use CI/CD (see `.github/workflows/native-extension.yml`).

## Common Issues

### Build fails with "error: linking with `cc` failed"

Make sure you have a C compiler installed:
- Linux: `sudo apt-get install build-essential`
- macOS: `xcode-select --install`
- Windows: Install Visual Studio Build Tools

### Import fails with "cannot import name 'dictsqlite_native'"

The native extension wasn't built or installed correctly. Try:
```bash
cd dictsqlite_native
maturin develop --release
```

### Tests fail with "Native extension should be available"

The native extension didn't build properly. Check the build output for errors.

## Contributing

When contributing to the native extension:

1. Ensure all tests pass
2. Add tests for new features
3. Benchmark performance improvements
4. Update documentation
5. Follow Rust best practices (run `cargo clippy`)
6. Format code (`cargo fmt`)

## Resources

- [PyO3 Documentation](https://pyo3.rs/)
- [Maturin Documentation](https://www.maturin.rs/)
- [Rusqlite Documentation](https://docs.rs/rusqlite/)
- [LRU Crate Documentation](https://docs.rs/lru/)

## License

The native extension code is licensed under the same MIT license as DictSQLite.
