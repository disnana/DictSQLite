# Fix for DictSQLite v2 Fatal Errors

## Issue Summary
The GitHub Actions workflow for DictSQLite v2 was encountering two critical errors when running the v4.2 comprehensive performance tests:

### Error 1: AttributeError
```
AttributeError: 'AsyncDictSQLite' object has no attribute 'set_async'
```

### Error 2: ModuleNotFoundError
```
thread '<unnamed>' panicked at src/lib.rs:79:21:
called `Result::unwrap()` on an `Err` value: PyErr { type: <class 'ModuleNotFoundError'>, 
value: ModuleNotFoundError("No module named 'safe_pickle'"), traceback: None }
```

## Root Cause Analysis

### Error 1: Missing `set_async` and `get_async` Methods
The test file `test_v4.2_comprehensive_performance.py` was calling `db.set_async()` and `db.get_async()` methods on `AsyncDictSQLite` instances. However, these methods were only available internally on the native Rust object (`self._db`), not exposed as public methods in the Python wrapper.

The Python wrapper only had:
- `aset()` and `aget()` - async awaitable methods
- `set()` and `get()` - synchronous wrapper methods

But not the `set_async()` and `get_async()` methods that the test was using.

### Error 2: Incorrect `safe_pickle` Import Path
The Rust code had two issues related to `safe_pickle` import:

1. **Incorrect Import Path**: The code was trying to import the module as `safe_pickle` after adding `"modules"` to `sys.path`. However, when the package is installed via maturin, the correct module path is `dictsqlite.modules.safe_pickle`.

2. **Immutable Tuple Mutation**: The `with_module_prefix()` method was trying to call `.append()` on `allowed_module_prefixes`, which is a tuple in the SafePolicy class and therefore immutable.

## Solutions Implemented

### Fix 1: Expose `set_async` and `get_async` in AsyncDictSQLite
Added public `set_async()` and `get_async()` methods to the `AsyncDictSQLite` Python wrapper class in `dictsqlite_v2/dictsqlite/python/dictsqlite/__init__.py`:

```python
def get_async(self, key):
    """Get value asynchronously (non-blocking, synchronous method)
    
    Note: Despite the name, this is a synchronous method that calls
    the underlying non-blocking implementation. For true async/await
    support, use aget() instead.
    """
    return self._db.get_async(str(key))

def set_async(self, key, value):
    """Set value asynchronously (non-blocking, synchronous method)
    
    Note: Despite the name, this is a synchronous method that calls
    the underlying non-blocking implementation. For true async/await
    support, use aset() instead.
    """
    if isinstance(value, str):
        value = value.encode('utf-8')
    elif not isinstance(value, bytes):
        import pickle
        value = pickle.dumps(value)
    self._db.set_async(str(key), value)
```

### Fix 2: Correct safe_pickle Import Path
Modified all `safe_pickle` imports in `dictsqlite_v2/dictsqlite/src/lib.rs` to use the full module path:

```rust
// Before:
let sys = py.import("sys")?;
let path = sys.getattr("path")?;
path.call_method1("append", ("modules",))?;
let safe_pickle = py.import("safe_pickle")?;

// After:
let safe_pickle = py.import("dictsqlite.modules.safe_pickle")?;
```

### Fix 3: Correct Tuple Handling in with_module_prefix
Rewrote the `with_module_prefix()` method to create a new `SafePolicy` object with updated prefixes instead of trying to mutate the immutable tuple:

```rust
pub fn with_module_prefix(self, prefix: String) -> PyResult<Self> {
    Python::with_gil(|py| {
        let policy_bound = self.policy.bind(py);
        let current_prefixes = policy_bound.getattr("allowed_module_prefixes")?;
        
        // Convert tuple to list of strings
        let prefixes_list: Vec<String> = current_prefixes.extract()?;
        
        let mut new_prefixes = prefixes_list;
        new_prefixes.push(prefix);
        
        // Create a new policy with the updated prefixes and copy all other attributes
        let safe_pickle = py.import("dictsqlite.modules.safe_pickle")?;
        let policy_class = safe_pickle.getattr("SafePolicy")?;
        let kwargs = pyo3::types::PyDict::new(py);
        kwargs.set_item("allowed_module_prefixes", new_prefixes)?;
        // ... copy other attributes ...
        
        let new_policy = policy_class.call((), Some(&kwargs))?;
        
        Ok(SafePicklePolicy {
            policy: new_policy.unbind(),
        })
    })
}
```

## Verification

### Test Results
1. Created comprehensive test suite in `tests/test_issue_fixes.py` that validates:
   - `set_async()` and `get_async()` methods work correctly
   - `safe_pickle` import and initialization works
   - Backward compatibility is maintained

2. Successfully ran the original failing test:
   ```bash
   python tests/test_v4.2_comprehensive_performance.py --iterations 3
   ```
   Result: ✅ All performance tests completed!

3. All new tests pass:
   ```bash
   pytest tests/test_issue_fixes.py -v
   ```
   Result: 3 passed

## Impact Assessment

### Changes Made
- **Python wrapper** (`__init__.py`): Added 23 lines (2 new methods with documentation)
- **Rust code** (`lib.rs`): Modified 3 functions to fix import paths and tuple handling
- **Tests**: Added comprehensive test file to prevent regression

### Backward Compatibility
✅ All changes are backward compatible:
- Existing `set()` and `get()` methods continue to work
- Existing `aset()` and `aget()` async methods continue to work
- New `set_async()` and `get_async()` methods are additions, not replacements

### Security
✅ No security impact:
- The safe_pickle functionality now works correctly
- Import path corrections improve package isolation
- No new attack vectors introduced

## Conclusion

Both critical errors have been resolved with minimal, surgical changes:
1. Added missing public methods to AsyncDictSQLite wrapper
2. Corrected safe_pickle module import paths
3. Fixed tuple mutation issue in safe_pickle policy handling

The changes are non-breaking, well-tested, and maintain full backward compatibility while enabling the v4.2 performance tests to run successfully in the GitHub Actions environment.
