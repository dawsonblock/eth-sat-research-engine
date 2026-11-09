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
n=$(printf '%s\n' "$out" | grep -c "depends on axioms: \[propext, Classical.choice, Quot.sound\]$" || true)
[[ "$n" -eq 27 ]] || { echo "expected 27 theorems on the standard axioms only, got $n" >&2; exit 1; }
if printf '%s\n' "$out" | grep -qiE 'error|sorryAx'; then exit 1; fi
echo 'PASS_MODE_COUNT_LEAN'
