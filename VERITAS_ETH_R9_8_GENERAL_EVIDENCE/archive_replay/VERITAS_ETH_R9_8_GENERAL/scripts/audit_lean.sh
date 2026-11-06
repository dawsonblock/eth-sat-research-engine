#!/usr/bin/env bash
set -euo pipefail
# Accept ONLY a local checked-out OpenAI/math/lean directory; do not auto-clone
# moving branches, and never assert manuscript verification from a build alone.
if [[ $# -ne 1 ]]; then
  echo 'Usage: bash scripts/audit_lean.sh /path/to/pinned-openai-math/lean' >&2; exit 2
fi
cd "$1"
[[ -f lean-toolchain && -f lakefile.toml || -f lakefile.lean ]] || { echo 'Not a recognized Lean checkout' >&2; exit 2; }
command -v lake >/dev/null || { echo 'Install elan/Lean and lake first' >&2; exit 2; }
echo 'Git HEAD (record this revision in audit):'
git rev-parse HEAD
cat lean-toolchain
lake build
printf 'Lean build succeeded. Inspect exact theorem statement and #print axioms separately.\n'
