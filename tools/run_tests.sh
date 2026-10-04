#!/bin/bash
# tools/run_tests.sh — every ABC check, one command. Run from anywhere:
#     ./tools/run_tests.sh
#
# Builds a stub (no assets needed), compiles every script block, then runs the
# static card-text checks, the battle suites and tests/. Needs: npm install
set -u
cd "$(dirname "$0")/.."          # repo root
SRC="src/game.src.html"
STUB="dist/stub.html"

[ -f "$SRC" ] || { echo "no $SRC — run this from the repo root"; exit 1; }

if ! command -v node >/dev/null 2>&1; then
  cat <<'MSG'
node is not installed, so the checks cannot run.

  You do not need it for the normal loop — python3 build.py works without it.

  If you want the checks locally:
      install Node v18+        (brew install node, or nodejs.org)
      npm install              (from the repo root, once)
MSG
  exit 127
fi

if [ ! -d node_modules/jsdom ]; then
  echo "jsdom is missing — run:  npm install"
  exit 127
fi

# python3 on macOS/Linux, python on Windows
PY=$(command -v python3 || command -v python) || { echo "python is not installed"; exit 127; }

mkdir -p dist
"$PY" build.py --stub --out "$STUB" >/dev/null || { echo "stub build FAILED"; exit 1; }
echo "  stub built: $STUB"

fail=0
printf '%-26s ' "compile"
out=$(node tools/compile.js "$SRC" 2>&1)
if [ $? -eq 0 ]; then echo "$(echo "$out" | tail -1)"
else echo "$out"; fail=1; fi

echo "-- card text (static) --"
for t in textcheck glyphcheck condtxt codecheck; do
  printf '%-26s ' "$t"
  out=$(timeout 90 node "tools/$t.js" 2>&1)
  line=$(echo "$out" | grep -E "passed," | tail -1)
  if echo "$out" | grep -qE "  FAIL|ERROR"; then echo "${line:-no result}   <-- FAILURES"; fail=1
  else echo "${line:-no result}"; fi
done

echo "-- engine (boots a real battle) --"
for t in mechanics conditionals lenses gekokujo coverage timer; do
  printf '%-26s ' "$t"
  out=$(timeout 120 node "tools/$t.test.js" 2>&1)
  line=$(echo "$out" | grep -E "passed,|fulfillable" | tail -1)
  if echo "$out" | grep -qE "  FAIL|ERROR"; then echo "${line:-no result}   <-- FAILURES"; fail=1
  else echo "${line:-no result}"; fi
done

echo "-- UI + regression (tests/) --"
for f in tests/*.test.js; do
  t=$(basename "$f" .test.js)
  printf '%-26s ' "$t"
  out=$(timeout 120 node "$f" 2>&1)
  line=$(echo "$out" | grep -E "passed" | tail -1)
  if echo "$out" | grep -qE "  FAIL|ERROR"; then echo "${line:-no result}   <-- FAILURES"; fail=1
  else echo "${line:-no result}"; fi
done

echo
if [ $fail -eq 0 ]; then echo "ALL GREEN"; else echo "SOMETHING FAILED — see above"; fi
exit $fail
