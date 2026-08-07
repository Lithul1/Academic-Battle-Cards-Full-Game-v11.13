#!/bin/bash
# tools/run_tests.sh — every ABC check, one command. Run from anywhere:
#     ./tools/run_tests.sh
#
# Builds a stub (no assets needed), compiles every script block, then runs the
# static card-text checks and the battle suites. Needs: npm i jsdom
set -u
cd "$(dirname "$0")/.."          # repo root
SRC="src/game.src.html"
STUB="dist/stub.html"

[ -f "$SRC" ] || { echo "no $SRC — run this from the repo root"; exit 1; }

if ! command -v node >/dev/null 2>&1; then
  cat <<'MSG'
node is not installed, so the checks cannot run.

  You do not need it for the normal loop — python3 build.py works without it,
  and these suites are run for you before each delivery.

  If you want them locally:
      brew install node        (or the installer at nodejs.org, v18+)
      npm i jsdom              (from the repo root, once)
MSG
  exit 127
fi

if [ ! -d node_modules/jsdom ]; then
  echo "jsdom is missing — run:  npm i jsdom"
  exit 127
fi

mkdir -p dist

python3 - "$SRC" "$STUB" <<'PY'
import re, sys
src, out = sys.argv[1], sys.argv[2]
s = open(src, encoding='utf-8').read()
STUB = ('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNg'
        'YGBgAAAABQABpfZFQAAAAABJRU5ErkJggg==')
open(out, 'w', encoding='utf-8').write(re.sub(r'__ABCASSET_\d+__', STUB, s))
print(f'  stub built: {out}')
PY

fail=0
printf '%-26s ' "compile"
if node tools/compile.js "$SRC" | grep -q "17/17"; then echo "17/17 script blocks OK"
else echo "FAILED"; fail=1; fi

echo "-- card text (static) --"
for t in textcheck glyphcheck condtxt codecheck; do
  printf '%-26s ' "$t"
  out=$(timeout 90 node "tools/$t.js" 2>&1)
  line=$(echo "$out" | grep -E "passed," | tail -1)
  if echo "$out" | grep -qE "  FAIL|ERROR"; then echo "${line:-no result}   <-- FAILURES"; fail=1
  else echo "${line:-no result}"; fi
done

echo "-- engine (boots a real battle) --"
for t in mechanics conditionals lenses gekokujo coverage; do
  printf '%-26s ' "$t"
  out=$(timeout 120 node "tools/$t.test.js" 2>&1)
  line=$(echo "$out" | grep -E "passed,|fulfillable" | tail -1)
  if echo "$out" | grep -qE "  FAIL|ERROR"; then echo "${line:-no result}   <-- FAILURES"; fail=1
  else echo "${line:-no result}"; fi
done

echo
if [ $fail -eq 0 ]; then echo "ALL GREEN"; else echo "SOMETHING FAILED — see above"; fi
exit $fail
