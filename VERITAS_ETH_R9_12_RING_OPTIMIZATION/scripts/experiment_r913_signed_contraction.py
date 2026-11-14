#!/usr/bin/env python3
"""One-level signed crossing rewrite economics (external evidence only)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from veritas.research.anthropic_signed_contraction import crossing_rewrite_economics

if __name__ == '__main__':
    report = crossing_rewrite_economics()
    out = ROOT / 'validation' / 'anthropic_signed_one_level.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps(report, indent=2))
