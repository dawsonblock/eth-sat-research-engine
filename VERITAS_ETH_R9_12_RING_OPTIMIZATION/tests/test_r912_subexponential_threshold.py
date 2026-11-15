"""Arithmetic checks for the explicit subexponential threshold.

These mirror the Nat inequalities in ModeCount/Subexponential.lean without
materialising 2^(lamZero).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "threshold", ROOT / "scripts" / "report_subexponential_threshold.py"
)
threshold = importlib.util.module_from_spec(spec)
spec.loader.exec_module(threshold)


def log2(n: int) -> int:
    return n.bit_length() - 1


def test_lam_zero_34_bit_length():
    lam = threshold.lam_zero(34)
    assert 50 <= lam.bit_length() <= 80
    assert lam == 2**34 * 34**2 * (threshold.poly_U(threshold.schedule_B(34)) + 1) ** 2


def test_log_linear_range():
    for S in list(range(64, 201)) + [2**k for k in range(6, 16)]:
        assert 8 * log2(S + 1) + 15 <= S


def test_cube_base():
    for lam in (32, 64):
        assert 256 * lam**3 <= 2 ** (lam - 2)


def test_absorption_exponent():
    for lam in (64, 80, 128):
        n = 8 * log2(lam + 1) + 8
        assert lam * (8 * n + 1) * (lam + 1) <= 2 ** (lam - 2)
        assert lam * (8 * n + 1) <= 2 ** (lam - 2) // (lam + 1)
