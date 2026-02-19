#!/bin/bash
# run_all_demo_tests.sh — No API key needed

echo ""
echo "=============================================="
echo "  DisSysLab: Running All Demo Tests"
echo "=============================================="
echo ""

PASS=0
FAIL=0

run_test() {
    local name=$1
    local path=$2
    echo "─── $name ───"
    if pytest "$path" -v --tb=short 2>&1; then
        PASS=$((PASS + 1))
    else
        FAIL=$((FAIL + 1))
    fi
    echo ""
}

run_test "Module 1: Describe & Build"       "examples/module_01/test_module_01.py"
run_test "Module 2: AI Integration"         "examples/module_02/test_module_02.py"
run_test "Module 3: Multiple Sources/Dests" "examples/module_03/test_module_03.py"
run_test "Module 4: Smart Routing (Split)"  "examples/module_04/test_module_04.py"

echo "=============================================="
echo "  Test Results: $PASS suites passed, $FAIL failed"
echo "=============================================="
echo ""

echo "=============================================="
echo "  Running Demo Examples"
echo "=============================================="
echo ""

for mod in \
    "examples.module_01.example_generated" \
    "examples.module_01.example_modified" \
    "examples.module_02.example_demo" \
    "examples.module_03.example_demo" \
    "examples.module_04.example_demo"; do
    echo "─── $mod ───"
    python3 -m "$mod" 2>&1 && echo "  ✓ OK" || echo "  ✗ FAILED"
    echo ""
done

echo "=============================================="
echo "  All demo tests and examples complete!"
echo "=============================================="