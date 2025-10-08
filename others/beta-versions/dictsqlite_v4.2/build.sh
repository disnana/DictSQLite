#!/bin/bash
# Build script for DictSQLite v4.0

set -e
# 最後に一時停止するのはローカル実行時のみ
if [ -z "$CI" ]; then
    trap 'echo; read -p "Press Enter to exit..."' EXIT
fi

echo "================================"
echo "DictSQLite v4.0 Build Script"
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

# Navigate to dictsqlite_v4 directory
cd "$(dirname "$0")"

echo "🔨 Building DictSQLite v4.0 in release mode..."
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
if [ -n "$CI" ]; then
    # In CI environment, automatically install
    echo "📥 Installing built package (CI mode)..."
    pip install --force-reinstall target/wheels/*.whl
    echo "✅ Installed successfully!"
    echo ""
    echo "🔍 Verifying installation..."
    python -c "from dictsqlite_v4 import DictSQLiteV4, AsyncDictSQLite; print('✅ DictSQLiteV4 imported successfully'); print('✅ AsyncDictSQLite imported successfully')"
else
    # In local environment, ask user
    read -p "Install the built package? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "📥 Installing..."
        pip install --force-reinstall target/wheels/*.whl
        echo "✅ Installed successfully!"
        echo ""
        echo "Test installation:"
        python -c "from dictsqlite_v4 import DictSQLiteV4; print('✅ DictSQLiteV4 imported successfully')"
    fi
fi

echo ""
echo "🎉 Done!"
echo ""
echo "To run examples:"
echo "  python examples/v4_usage_examples.py"
echo ""
echo "To run benchmarks:"
echo "  python examples/v4_benchmark.py"
echo ""
echo "To run tests:"
echo "  pytest tests/test_v4_security.py -v"
echo ""
