#!/usr/bin/env bash
# demo.sh — the whole pipeline, end to end, reproducibly.
#
# Runs on the STAND-IN plate screenshots in sources/, because the real source
# plates cannot be fetched from a cloud session. Everything here is the real
# machinery; only the inputs are placeholders.
set -e
cd "$(dirname "$0")"
rm -rf out/history.json out/proof-calavera-v*

echo "== 1. compose v1 =="
python3 compose.py --recipe recipes/_proof.json >/dev/null 2>&1 || true

echo "== 2. mockup v1 =="
python3 mockup.py --design proof-calavera --version 1 \
  --print out/proof-calavera-onlight.png \
  --note "pipeline proof on stand-in plates" >/dev/null

echo "== 3. inspect v1 (expected: BLOCKED) =="
python3 inspect.py --design proof-calavera --version 1 \
  --recipe recipes/_proof.json || true

echo
echo "== 4. gate check: v2 without answering findings must refuse =="
python3 mockup.py --design proof-calavera --version 2 \
  --print out/proof-calavera-onlight.png 2>&1 | head -3 || true

echo
echo "== 5. compose v2, answering the finding =="
python3 compose.py --recipe recipes/_proof_v2.json >/dev/null 2>&1 || true

echo "== 6. mockup v2 =="
python3 mockup.py --design proof-calavera --version 2 \
  --print out/proof-calavera-v2src-onlight.png \
  --change "ink0 #1A1A1A -> #4A4A4A, ink1 #C4661F -> #E8A94A: average ink measured 2.69:1 on black, under the 3:1 WCAG floor" \
  --change "gamma 1.0 -> 0.8 on both layers, so the lighter palette keeps its coverage" \
  --note "answers the contrast-on-black failure from v1" >/dev/null

echo "== 7. inspect v2 (expected: PASS) =="
python3 inspect.py --design proof-calavera --version 2 --recipe recipes/_proof_v2.json

echo
echo "== 8. change history =="
python3 history.py --report
