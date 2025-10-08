#!/bin/bash
# Production Build Script for DictSQLite v4.2
# Optimized for maximum performance benchmarking

set -e
# 最後に一時停止するのはローカル実行時のみ
if [ -z "$CI" ]; then
    trap 'echo; read -p "Press Enter to exit..."' EXIT
fi

echo "================================"
echo "DictSQLite v4.2 Production Build"
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

# Navigate to dictsqlite_v4.2 directory
cd "$(dirname "$0")"

echo "🔨 Building DictSQLite v4.2 with production optimizations..."
echo ""
echo "Build configuration:"
echo "  - Optimization level: 3 (maximum)"
echo "  - LTO: fat (Link-Time Optimization)"
echo "  - Codegen units: 1 (maximum optimization)"
echo "  - Debug symbols: stripped"
echo "  - Panic: abort (no unwinding)"
echo ""

# Clean previous builds
if [ -d "target" ]; then
    echo "🧹 Cleaning previous builds..."
    cargo clean
fi

# Build with maturin in release mode
echo "🚀 Building..."
maturin build --release --strip

echo ""
echo "✅ Build completed successfully!"
echo ""
echo "📦 Wheels available in: target/wheels/"
ls -lh target/wheels/*.whl 2>/dev/null || echo "No wheels found"
echo ""

# Install the built package
echo "📥 Installing built package..."
pip install --force-reinstall target/wheels/*.whl

echo ""
echo "✅ Installed successfully!"
echo ""

# Verify installation
echo "🔍 Verifying installation..."
python3 -c "
from dictsqlite_v4 import DictSQLiteV4, AsyncDictSQLite
print('✅ DictSQLiteV4 imported successfully')
print('✅ AsyncDictSQLite imported successfully')

# Quick smoke test
import tempfile
import os

fd, db_path = tempfile.mkstemp(suffix='.db')
os.close(fd)
try:
    db = DictSQLiteV4(db_path)
    db['test'] = b'value'
    assert db['test'] == b'value'
    print('✅ Smoke test passed')
finally:
    os.unlink(db_path)
"

echo ""
echo "🎉 Production build ready!"
echo ""
echo "📊 To run performance tests:"
echo "   python tests/test_v4.2_comprehensive_performance.py"
echo ""
echo "🔬 To run specific tests:"
echo "   python tests/test_v4.2_comprehensive_performance.py --iterations 5"
echo ""
echo "📈 To run benchmarks:"
echo "   python examples/v4_benchmark.py"
echo ""
