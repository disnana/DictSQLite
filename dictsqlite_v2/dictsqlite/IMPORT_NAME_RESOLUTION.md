# Import Name Resolution - Why `dictsqlite` not `dictsqlite_v2`

## Issue Summary

**Directory Structure:** `dictsqlite_v2/dictsqlite/`  
**Expected Import:** `from dictsqlite import DictSQLiteV4`  
**Problem:** Risk of being built as `dictsqlite_v2` instead of `dictsqlite`

## Root Cause

The Python package name for the wheel is determined by **`pyproject.toml` `[project]` `name` field**, NOT by the directory name. 

Given the directory structure `dictsqlite_v2/dictsqlite/`, there might be confusion about which name to use:
- Directory name: `dictsqlite_v2` (parent) / `dictsqlite` (current)
- Python module name (from Rust `#[pymodule]`): `dictsqlite`
- Desired package name: `dictsqlite`

If `pyproject.toml` were configured with `name = "dictsqlite_v2"` (matching the parent directory), the wheel would be named `dictsqlite_v2-x.x.x.whl`, causing import confusion even though the internal module is still `dictsqlite`.

## Solution

### Current Configuration (Correct)

**pyproject.toml:**
```toml
[project]
name = "dictsqlite"  # ✅ Must match the Python module name
```

**Cargo.toml:**
```toml
[package]
name = "dictsqlite"

[lib]
name = "dictsqlite"

[package.metadata.maturin]
name = "dictsqlite"  # For consistency (redundant in modern maturin >= 0.14)
```

**src/lib.rs:**
```rust
#[pymodule]
fn dictsqlite(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Module name is "dictsqlite"
}
```

### Key Points

1. **pyproject.toml `[project]` `name`** controls the wheel package name
2. **Rust `#[pymodule]` attribute** controls the Python module name
3. **Both must match** for `from dictsqlite import ...` to work
4. **`[package.metadata.maturin]` `name`** is kept for backward compatibility but is redundant in maturin >= 0.14

### What Builds

✅ **Correct:**
- Wheel: `dictsqlite-2.0.4-cp39-abi3-linux_x86_64.whl`
- Import: `from dictsqlite import DictSQLiteV4`

❌ **Incorrect** (if pyproject.toml had `name = "dictsqlite_v2"`):
- Wheel: `dictsqlite_v2-2.0.4-cp39-abi3-linux_x86_64.whl`
- Import attempts: `from dictsqlite_v2 import ...` ← would fail!
- Actual module inside: still `dictsqlite/` ← mismatch!

## Verification

To verify the configuration:

```bash
# Build the wheel
maturin build --release

# Check the wheel name (should be dictsqlite-*.whl, not dictsqlite_v2-*.whl)
ls target/wheels/

# Install and test
pip install target/wheels/dictsqlite-*.whl
python -c "from dictsqlite import DictSQLiteV4; print('✅ Import successful')"
```

## Why the Directory is Named `dictsqlite_v2`

The parent directory `dictsqlite_v2` is used for:
- **Repository organization**: Separate v2 implementation from v1
- **Development clarity**: Indicate this is the v2 codebase
- **NOT** for the package name

The package name remains `dictsqlite` for:
- **User simplicity**: Consistent import path across versions
- **Backward compatibility**: Same import path as v1
- **PyPI naming**: Keep the same package name on PyPI

## Prevention

To prevent this issue:
1. ✅ Always keep `pyproject.toml [project] name = "dictsqlite"`
2. ✅ Keep `Cargo.toml [package.metadata.maturin] name = "dictsqlite"`  
3. ✅ Ensure `#[pymodule] fn dictsqlite` matches
4. ⚠️ Never change these to match the directory name `dictsqlite_v2`

## References

- Maturin Documentation: https://www.maturin.rs/
- PEP 621 (Project Metadata): https://peps.python.org/pep-0621/
- PyO3 Documentation: https://pyo3.rs/

---

**Resolution Date:** 2025-10-09  
**Status:** ✅ Resolved (configuration verified correct)
