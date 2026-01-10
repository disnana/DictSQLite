#!/bin/bash
# ローカルでベンチマークワークフローをテストするスクリプト
# このスクリプトはworkflowの一部の動作を検証します

set -e

echo "=================================="
echo "Benchmark Workflow Local Test"
echo "=================================="
echo ""

# カラーコード
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# テスト結果
TESTS_PASSED=0
TESTS_FAILED=0

# テスト関数
test_step() {
    local name="$1"
    local command="$2"
    
    echo -e "${YELLOW}Testing: ${name}${NC}"
    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ PASS${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}✗ FAIL${NC}"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
    echo ""
}

# ディレクトリ確認
cd "$(dirname "$0")"
cd ../..

echo "1. ディレクトリ構造の検証"
echo "-----------------------------------"
test_step "dictsqlite_v2/dictsqlite exists" "test -d dictsqlite_v2/dictsqlite"
test_step "dictsqlite_v4.1 exists" "test -d others/beta-versions/dictsqlite_v4.1"
test_step "benchmark scripts exist" "test -f others/benchmark/run_benchmark.py"
test_step "version_manager exists" "test -f others/benchmark/version_manager.py"

echo "2. ファイル構造の検証"
echo "-----------------------------------"
test_step "v2 Cargo.toml exists" "test -f dictsqlite_v2/dictsqlite/Cargo.toml"
test_step "v2 pyproject.toml exists" "test -f dictsqlite_v2/dictsqlite/pyproject.toml"
test_step "v4.1 Cargo.toml exists" "test -f others/beta-versions/dictsqlite_v4.1/Cargo.toml"
test_step "benchmark.yml exists" "test -f .github/workflows/benchmark.yml"

echo "3. バージョン情報の検証"
echo "-----------------------------------"
test_step "v2 version in pyproject.toml" "grep -q '2.0.6' dictsqlite_v2/dictsqlite/pyproject.toml"
test_step "Original version accessible" "test -f dictsqlite/main.py && grep -q '__version__' dictsqlite/main.py"

echo "4. Python スクリプトの構文チェック"
echo "-----------------------------------"
test_step "version_manager.py syntax" "python -m py_compile others/benchmark/version_manager.py"
test_step "run_benchmark.py syntax" "python -m py_compile others/benchmark/run_benchmark.py"
test_step "benchmark_all_versions.py syntax" "python -m py_compile others/benchmark/benchmark_all_versions.py"

echo "5. YAML 構文の検証"
echo "-----------------------------------"
test_step "benchmark.yml YAML syntax" "python -c 'import yaml; yaml.safe_load(open(\".github/workflows/benchmark.yml\"))'"

echo "6. 結果ディレクトリ作成テスト"
echo "-----------------------------------"
test_step "Create results directories" "
    TEST_DIR=/tmp/test_benchmark_results_$$
    mkdir -p \$TEST_DIR/versions && \
    mkdir -p \$TEST_DIR/graphs && \
    mkdir -p \$TEST_DIR/comparisons && \
    test -d \$TEST_DIR/versions && \
    test -d \$TEST_DIR/graphs && \
    test -d \$TEST_DIR/comparisons && \
    rm -rf \$TEST_DIR
"

echo "=================================="
echo "Test Summary"
echo "=================================="
echo -e "${GREEN}Passed: ${TESTS_PASSED}${NC}"
echo -e "${RED}Failed: ${TESTS_FAILED}${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed!${NC}"
    exit 1
fi
