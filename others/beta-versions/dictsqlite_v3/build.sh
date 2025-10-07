#!/bin/bash
# Build script for DictSQLite v3.0

set -e

echo "================================"
echo "DictSQLite v3.0 Build Script"
echo "================================"
echo ""

# Check if Rust is installed
if ! command -v cargo &> /dev/null; then
    echo "❌ Error: Rust is not installed."
    echo "Please install Rust from: https://rustup.rs/"
    exit 1
fi

echo "✅ Rust found: $(rustc --version)"

# Check if maturin is installed
if ! command -v maturin &> /dev/null; then
    echo "📦 Installing maturin..."
    pip install maturin
fi

echo "✅ Maturin found: $(maturin --version)"
echo ""

# Navigate to dictsqlite_v3 directory
cd "$(dirname "$0")"

echo "🔨 Building DictSQLite v3.0 in release mode..."
echo ""

# Build with maturin
maturin build --release

echo ""
echo "✅ Build completed successfully!"
echo ""
echo "📦 Wheels available in: target/wheels/"
ls -lh target/wheels/*.whl 2>/dev/null || echo "No wheels found"
echo ""

# Optionally install
read -p "Install the built package? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "📥 Installing..."
    pip install --force-reinstall target/wheels/*.whl
    echo "✅ Installed successfully!"
    echo ""
    echo "Test installation:"
    python -c "from dictsqlite_v3 import DictSQLiteV3, is_native_available; print(f'Native available: {is_native_available()}')"
fi

echo ""
echo "🎉 Done!"
echo ""
echo "To run benchmarks:"
echo "  python examples/benchmark.py"
echo ""
echo "To run Rust benchmarks:"
echo "  cargo bench"
