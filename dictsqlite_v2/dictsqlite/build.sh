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

# Validate package name configuration
echo "🔍 Validating package name configuration..."
if python validate_package_name.py; then
    echo ""
else
    echo ""
    echo "❌ Package name validation failed!"
    echo "Please fix the configuration before building."
    exit 1
fi

# Navigate to dictsqlite_v4 directory
cd "$(dirname "$0")"

echo "🔨 Building DictSQLite v4.0 in release mode..."
echo ""

# Optional: clean wheels directory before build
# Default: CLEAN_WHEELS=1 (clean by default)
# Use --no-clean-wheels to skip cleaning, or --clean-wheels to force it
CLEAN_WHEELS=1
for arg in "$@"; do
    case "$arg" in
        --no-clean-wheels)
            CLEAN_WHEELS=0
            ;;
        --clean-wheels)
            CLEAN_WHEELS=1
            ;;
    esac
done

WHEELS_DIR="$(pwd)/target/wheels"
if [ $CLEAN_WHEELS -eq 1 ]; then
    echo "🧹 Cleaning wheels directory: $WHEELS_DIR"
    if [ -d "$WHEELS_DIR" ]; then
        rm -f "$WHEELS_DIR"/*.whl 2>/dev/null || true
    else
        echo "ℹ️  Wheels directory does not exist, skipping cleanup"
    fi
else
    echo "ℹ️  Skipping wheels cleanup (use --clean-wheels to force)"
fi

# Build with maturin
maturin build --release

echo ""
echo "✅ Build completed successfully!"
echo ""
echo "📦 Wheels available in: target/wheels/"
if compgen -G "target/wheels/*.whl" > /dev/null; then
    ls -lh target/wheels/*.whl
else
    echo "No wheels found"
fi
echo ""

# Optionally install
if [ -n "$CI" ]; then
    # In CI environment, automatically install
    echo "📥 Installing built package (CI mode)..."
    if compgen -G "target/wheels/*.whl" > /dev/null; then
        pip install --force-reinstall target/wheels/*.whl
        echo "✅ Installed successfully!"
    else
        echo "⚠️  No wheel found to install. Skipping installation."
    fi
    echo ""
    echo "🔍 Verifying installation..."
    python -c "from dictsqlite import DictSQLiteV4, AsyncDictSQLite; print('✅ DictSQLiteV4 imported successfully'); print('✅ AsyncDictSQLite imported successfully')"
else
    # In local environment, ask user
    read -p "Install the built package? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "📥 Installing..."
        if compgen -G "target/wheels/*.whl" > /dev/null; then
            pip install --force-reinstall target/wheels/*.whl
            echo "✅ Installed successfully!"
        else
            echo "⚠️  No wheel found to install. Skipping installation."
        fi
        echo ""
        echo "Test installation:"
        python -c "from dictsqlite import DictSQLiteV4; print('✅ DictSQLiteV4 imported successfully')"
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
