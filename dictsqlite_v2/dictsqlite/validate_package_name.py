#!/usr/bin/env python3
"""
Validation script to ensure the package is built with the correct name.

This script verifies that:
1. pyproject.toml [project] name is "dictsqlite"
2. Cargo.toml [package.metadata.maturin] name is "dictsqlite"
3. The built wheel has the correct name format

Run this before releasing to ensure no accidental misconfiguration.
"""

import sys
import tomli
from pathlib import Path

def validate_pyproject_toml():
    """Validate pyproject.toml configuration."""
    pyproject_path = Path(__file__).parent / "pyproject.toml"
    
    with open(pyproject_path, "rb") as f:
        data = tomli.load(f)
    
    project_name = data.get("project", {}).get("name")
    
    if project_name != "dictsqlite":
        print(f"❌ ERROR: pyproject.toml [project] name is '{project_name}', expected 'dictsqlite'")
        print("   This will cause the wheel to be built with the wrong name.")
        print(f"   Please update {pyproject_path} to set name = 'dictsqlite'")
        return False
    
    print(f"✅ pyproject.toml [project] name = '{project_name}' (correct)")
    return True

def validate_cargo_toml():
    """Validate Cargo.toml configuration."""
    cargo_path = Path(__file__).parent / "Cargo.toml"
    
    with open(cargo_path, "rb") as f:
        data = tomli.load(f)
    
    # Check [package] name
    package_name = data.get("package", {}).get("name")
    if package_name != "dictsqlite":
        print(f"❌ ERROR: Cargo.toml [package] name is '{package_name}', expected 'dictsqlite'")
        return False
    print(f"✅ Cargo.toml [package] name = '{package_name}' (correct)")
    
    # Check [lib] name
    lib_name = data.get("lib", {}).get("name")
    if lib_name != "dictsqlite":
        print(f"❌ ERROR: Cargo.toml [lib] name is '{lib_name}', expected 'dictsqlite'")
        return False
    print(f"✅ Cargo.toml [lib] name = '{lib_name}' (correct)")
    
    # Check [package.metadata.maturin] name (optional but recommended)
    maturin_name = data.get("package", {}).get("metadata", {}).get("maturin", {}).get("name")
    if maturin_name and maturin_name != "dictsqlite":
        print(f"⚠️  WARNING: Cargo.toml [package.metadata.maturin] name is '{maturin_name}', expected 'dictsqlite'")
        print("   This may cause issues. It's recommended to set it to 'dictsqlite' or remove it.")
        return False
    elif maturin_name:
        print(f"✅ Cargo.toml [package.metadata.maturin] name = '{maturin_name}' (correct)")
    else:
        print("ℹ️  Cargo.toml [package.metadata.maturin] name not set (using pyproject.toml name)")
    
    return True

def validate_wheel_name():
    """Validate that built wheels have the correct name."""
    wheels_dir = Path(__file__).parent / "target" / "wheels"
    
    if not wheels_dir.exists():
        print("ℹ️  No wheels directory found. Build the project first with: maturin build --release")
        return True
    
    wheels = list(wheels_dir.glob("*.whl"))
    if not wheels:
        print("ℹ️  No wheels found in target/wheels/. Build the project first.")
        return True
    
    all_correct = True
    for wheel in wheels:
        if wheel.name.startswith("dictsqlite-"):
            print(f"✅ Wheel name correct: {wheel.name}")
        elif wheel.name.startswith("dictsqlite_v2-"):
            print(f"❌ ERROR: Wheel has wrong name: {wheel.name}")
            print(f"   Expected to start with 'dictsqlite-', not 'dictsqlite_v2-'")
            all_correct = False
        else:
            print(f"⚠️  WARNING: Unexpected wheel name: {wheel.name}")
    
    return all_correct

def main():
    """Run all validation checks."""
    print("=" * 70)
    print("DictSQLite Package Name Validation")
    print("=" * 70)
    print()
    
    results = []
    
    print("Checking pyproject.toml...")
    results.append(validate_pyproject_toml())
    print()
    
    print("Checking Cargo.toml...")
    results.append(validate_cargo_toml())
    print()
    
    print("Checking built wheels...")
    results.append(validate_wheel_name())
    print()
    
    print("=" * 70)
    if all(results):
        print("✅ All validation checks passed!")
        print()
        print("The package is configured correctly to build as 'dictsqlite'.")
        print("Import should work as: from dictsqlite import DictSQLiteV4")
        print("=" * 70)
        return 0
    else:
        print("❌ Validation failed!")
        print()
        print("Please fix the configuration errors above.")
        print("See IMPORT_NAME_RESOLUTION.md for detailed explanation.")
        print("=" * 70)
        return 1

if __name__ == "__main__":
    sys.exit(main())
