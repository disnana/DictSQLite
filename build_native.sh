#!/bin/bash
# Build script for native Rust extension

set -e

echo "Building DictSQLite native extension..."

# Check if Rust is installed
if ! command -v cargo &> /dev/null; then
    echo "Error: Rust is not installed. Please install Rust from https://rustup.rs/"
    exit 1
fi

# Check if maturin is installed
if ! command -v maturin &> /dev/null; then
    echo "Installing maturin..."
    pip install maturin
fi

# Build the extension
cd dictsqlite_native
echo "Building in release mode..."
maturin build --release

# Install the built wheel
echo "Installing built wheel..."
pip install --force-reinstall target/wheels/*.whl

echo "Native extension built and installed successfully!"
echo ""
echo "To verify, run: python -c 'from dictsqlite.native_wrapper import is_native_available; print(f\"Native extension available: {is_native_available()}\")'"
