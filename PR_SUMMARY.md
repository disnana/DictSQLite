# Pull Request: Fix Import Naming Issue - Document and Validate Package Configuration

## Issue Reference
Issue: "importが予定と違う" (Import is different from expected)

The import from `dictsqlite_v2/dictsqlite` should be `dictsqlite`, but there was concern it might be built as `dictsqlite_v2`.

## Problem Analysis

### Root Cause
The Python package name is determined by `pyproject.toml [project] name`, not the directory name. Given the directory structure `dictsqlite_v2/dictsqlite/`, there could be confusion about whether to use:
- Parent directory name: `dictsqlite_v2`
- Current directory name: `dictsqlite`
- Module name (from Rust): `dictsqlite`

If `pyproject.toml [project] name` were set to `"dictsqlite_v2"` (matching the parent directory), the wheel would be incorrectly named `dictsqlite_v2-*.whl`, causing import confusion.

### Current Status
The configuration was already correct with `name = "dictsqlite"`, but lacked:
- Clear documentation explaining WHY this must be the case
- Validation to prevent accidental misconfiguration
- Comments warning against changing to match directory name

## Changes Made

### 1. Documentation (3 files created)

#### `IMPORT_NAME_RESOLUTION.md` (English)
- Comprehensive explanation of the naming structure
- Root cause analysis
- Current configuration details
- Prevention measures
- Verification procedures

#### `IMPORT_NAME_RESOLUTION_JP.md` (Japanese)
- Same content as above, in Japanese
- For Japanese-speaking developers

#### `RESOLUTION_SUMMARY.md`
- Complete issue resolution summary
- Files modified and created
- Testing results
- Key learnings

### 2. Configuration Comments (2 files modified)

#### `pyproject.toml`
Added clear warning comments:
```toml
# IMPORTANT: This name determines the wheel package name and must match the
# Python module name defined in src/lib.rs (#[pymodule] fn dictsqlite).
# Do NOT use "dictsqlite_v2" here, even though the directory is dictsqlite_v2/dictsqlite.
# The correct import should be: from dictsqlite import DictSQLiteV4
name = "dictsqlite"
```

#### `Cargo.toml`
Added comprehensive explanation:
```toml
# IMPORTANT: The Python package name is primarily controlled by pyproject.toml [project] name.
# This 'name' field is kept for backward compatibility and documentation, but modern maturin
# (>= 0.14) uses pyproject.toml [project] name as the primary source.
# Both must be set to "dictsqlite" to match the Python module name (#[pymodule] fn dictsqlite).
# Do NOT change this to "dictsqlite_v2" even though the directory is dictsqlite_v2/dictsqlite.
name = "dictsqlite"
```

### 3. Validation Script (1 file created)

#### `validate_package_name.py`
Automated validation script that checks:
- ✅ `pyproject.toml [project] name = "dictsqlite"`
- ✅ `Cargo.toml [package] name = "dictsqlite"`
- ✅ `Cargo.toml [lib] name = "dictsqlite"`
- ✅ `Cargo.toml [package.metadata.maturin] name = "dictsqlite"`
- ✅ Built wheels start with `dictsqlite-` (not `dictsqlite_v2-`)

### 4. Build Script Integration (2 files modified)

#### `build.sh`
Added validation step before building:
```bash
# Validate package name configuration
echo "🔍 Validating package name configuration..."
if python validate_package_name.py; then
    echo ""
else
    echo ""
    echo "❌ Package name validation failed!"
    exit 1
fi
```

#### `build_production.sh`
- Added same validation step
- Fixed incorrect import path from `dictsqlite_v4` to `dictsqlite`

## Testing & Verification

### Build Verification
```bash
$ cd dictsqlite_v2/dictsqlite
$ ./build.sh
```

Output:
- ✅ Validation checks pass
- ✅ Wheel: `dictsqlite-2.0.4-cp39-abi3-manylinux_2_34_x86_64.whl`

### Import Verification
```python
from dictsqlite import DictSQLiteV4, AsyncDictSQLite
```
Result: ✅ Imports successfully

### Validation Script Test
```bash
$ python validate_package_name.py
```

Output:
```
✅ pyproject.toml [project] name = 'dictsqlite' (correct)
✅ Cargo.toml [package] name = 'dictsqlite' (correct)
✅ Cargo.toml [lib] name = 'dictsqlite' (correct)
✅ Cargo.toml [package.metadata.maturin] name = 'dictsqlite' (correct)
✅ Wheel name correct: dictsqlite-2.0.4-cp39-abi3-manylinux_2_34_x86_64.whl
✅ All validation checks passed!
```

### Integration Test
```python
✅ Import successful: from dictsqlite import DictSQLiteV4, AsyncDictSQLite
✅ Basic operations work correctly
✅ Package installed as 'dictsqlite' (version 2.0.4)
```

## Summary of Changes

### Files Modified (4)
1. `dictsqlite_v2/dictsqlite/pyproject.toml` - Added warning comments
2. `dictsqlite_v2/dictsqlite/Cargo.toml` - Added explanatory comments
3. `dictsqlite_v2/dictsqlite/build.sh` - Added validation step
4. `dictsqlite_v2/dictsqlite/build_production.sh` - Added validation, fixed import

### Files Created (4)
1. `dictsqlite_v2/dictsqlite/IMPORT_NAME_RESOLUTION.md` - English documentation
2. `dictsqlite_v2/dictsqlite/IMPORT_NAME_RESOLUTION_JP.md` - Japanese documentation
3. `dictsqlite_v2/dictsqlite/validate_package_name.py` - Validation script
4. `dictsqlite_v2/dictsqlite/RESOLUTION_SUMMARY.md` - Issue resolution summary

## Impact

### Positive
- ✅ Clear documentation prevents future confusion
- ✅ Automated validation prevents accidental misconfiguration
- ✅ Build scripts now verify configuration before building
- ✅ Bilingual documentation (English + Japanese)

### Risk
- ⚠️ None - Changes are additive (documentation and validation only)
- ⚠️ No changes to actual build configuration (already correct)
- ⚠️ No changes to source code

## Conclusion

The package was already configured correctly, but this PR adds:
1. **Documentation** to explain WHY the configuration must be this way
2. **Validation** to prevent future misconfiguration
3. **Build integration** to ensure validation runs automatically

**Status: ✅ Issue Resolved**

The import path is and will remain: `from dictsqlite import DictSQLiteV4`
