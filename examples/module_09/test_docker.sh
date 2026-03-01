#!/usr/bin/env bash
# examples/module_09/test_docker.sh
#
# Verifies that the Module 09 Docker image builds correctly and that
# the container runs app.py, produces sentiment output, and exits cleanly.
#
# Run from the DisSysLab root directory:
#     bash examples/module_09/test_docker.sh
#
# Requirements:
#     Docker must be installed and running.
#     Install Docker Desktop: https://www.docker.com/products/docker-desktop/

set -euo pipefail   # exit on error, undefined variable, or pipe failure

IMAGE="dissyslab-monitor-test"
PASS=0
FAIL=0

# ── Helpers ───────────────────────────────────────────────────────────────────

green()  { echo "  ✅  $*"; }
red()    { echo "  ❌  $*"; }
header() { echo; echo "── $* ──────────────────────────────────────────────"; }

pass() { green "$1"; PASS=$((PASS + 1)); }
fail() { red   "$1"; FAIL=$((FAIL + 1)); }

# ── Preflight ─────────────────────────────────────────────────────────────────

header "Preflight"

if ! command -v docker &>/dev/null; then
    red "Docker not found. Install Docker Desktop and try again."
    red "https://www.docker.com/products/docker-desktop/"
    exit 1
fi
pass "Docker is installed"

if ! docker info &>/dev/null; then
    red "Docker daemon is not running. Start Docker Desktop and try again."
    exit 1
fi
pass "Docker daemon is running"

if [ ! -f "examples/module_09/Dockerfile" ]; then
    red "Dockerfile not found. Run this script from the DisSysLab root directory."
    exit 1
fi
pass "Dockerfile found"

# ── Test 1: Image builds without error ────────────────────────────────────────

header "Test 1: docker build"

if docker build \
       --tag  "$IMAGE" \
       --file examples/module_09/Dockerfile \
       --quiet \
       . ; then
    pass "Image built successfully"
else
    fail "docker build failed — check the output above"
    exit 1
fi

# ── Test 2: Container runs and exits cleanly ──────────────────────────────────

header "Test 2: docker run (may take up to 90 seconds)"

OUTPUT=$(docker run --rm "$IMAGE" 2>&1) || {
    fail "Container exited with a non-zero status code"
    echo
    echo "Container output:"
    echo "$OUTPUT"
    docker image rm "$IMAGE" &>/dev/null || true
    exit 1
}
pass "Container exited with status 0"

# ── Test 3: Output contains the network topology header ───────────────────────

header "Test 3: Output content"

if echo "$OUTPUT" | grep -q "BlueSky Sentiment Monitor"; then
    pass "Output contains app header"
else
    fail "Output missing app header 'BlueSky Sentiment Monitor'"
fi

# ── Test 4: Output contains at least one sentiment label ─────────────────────

if echo "$OUTPUT" | grep -qE "POSITIVE|NEGATIVE|NEUTRAL"; then
    pass "Output contains sentiment labels"
else
    fail "Output contains no sentiment labels (POSITIVE / NEGATIVE / NEUTRAL)"
fi

# ── Test 5: Output contains the done marker ───────────────────────────────────

if echo "$OUTPUT" | grep -q "Done"; then
    pass "Output contains clean-exit marker ('Done')"
else
    fail "Output missing clean-exit marker — container may have timed out"
fi

# ── Test 6: Output contains post count ────────────────────────────────────────

if echo "$OUTPUT" | grep -qE "[0-9]+ posts processed"; then
    pass "Output reports posts processed"
else
    fail "Output missing posts-processed count"
fi

# ── Test 7: Live vs demo source ───────────────────────────────────────────────

header "Test 7: Source used"

if echo "$OUTPUT" | grep -q "Connected to live BlueSky stream"; then
    pass "Used live BlueSky Jetstream"
elif echo "$OUTPUT" | grep -q "demo posts"; then
    pass "Used demo fallback (no network inside container — expected)"
else
    fail "Could not determine which source was used"
fi

# ── Cleanup ───────────────────────────────────────────────────────────────────

header "Cleanup"

docker image rm "$IMAGE" &>/dev/null && pass "Test image removed" \
    || fail "Could not remove test image (remove manually: docker image rm $IMAGE)"

# ── Summary ───────────────────────────────────────────────────────────────────

echo
echo "════════════════════════════════════════════════════════"
echo "  Results: ${PASS} passed, ${FAIL} failed"
echo "════════════════════════════════════════════════════════"
echo

if [ "$FAIL" -eq 0 ]; then
    echo "  ✅  All Docker tests passed."
    echo "      Your container builds and runs correctly."
    echo "      It is ready to deploy in Module 10."
    echo
    exit 0
else
    echo "  ❌  ${FAIL} test(s) failed."
    echo "      Check the output above for details."
    echo
    exit 1
fi
