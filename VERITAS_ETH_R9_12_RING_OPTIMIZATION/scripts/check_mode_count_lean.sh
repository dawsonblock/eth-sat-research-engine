#!/usr/bin/env bash
set -euo pipefail
# Builds the Mathlib mode-count proofs and fails on sorry or any nonstandard axiom.
cd "$(dirname "$0")/../proofs_mathlib"
command -v lake >/dev/null || { echo 'Install elan with leanprover/lean4:v4.35.0 first' >&2; exit 2; }
if grep -nE '\b(sorry|admit)\b|^axiom ' ModeCount/*.lean; then
  echo 'sorry, admit or axiom present' >&2; exit 1
fi
lake exe cache get >/dev/null
lake build
out=$(lake env lean Axioms.lean 2>&1)
printf '%s\n' "$out"
std='(propext|Classical\.choice|Quot\.sound)'
n=$(printf '%s\n' "$out" | grep -cE "(depends on axioms: \[$std(, $std)*\]|does not depend on any axioms)$" || true)
[[ "$n" -eq 37 ]] || { echo "expected 37 theorems using at most the standard axioms, got $n" >&2; exit 1; }
if printf '%s\n' "$out" | grep -qiE 'error|sorryAx'; then exit 1; fi
echo 'PASS_MODE_COUNT_LEAN'
