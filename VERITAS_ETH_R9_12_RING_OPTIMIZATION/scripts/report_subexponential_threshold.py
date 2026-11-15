#!/usr/bin/env python3
"""Explicit schedule threshold matching ModeCount.lamZero.

Prints lamZero(C) and its bit length. s0 = 2^(lamZero-1) is the smallest
ceiling-log window the absorption uses; it is reported by bit length only.
"""

from __future__ import annotations

import argparse


def schedule_B(C: int) -> int:
    return (C + 8) ** 3 * 50 * (2**34 * C**2 + 1) ** 4


def poly_U(B: int) -> int:
    if B <= 0:
        raise ValueError("B must be positive")
    S = B.bit_length()  # Nat.log2 B + 1
    return max(128, S + 8 * ((S + 1).bit_length() - 1 + 2))


def lam_zero(C: int) -> int:
    return 2**34 * C**2 * (poly_U(schedule_B(C)) + 1) ** 2


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--C", type=int, default=34)
    args = parser.parse_args()
    if args.C < 1:
        raise SystemExit("C must be positive")
    lam = lam_zero(args.C)
    print(f"C={args.C}")
    print(f"lamZero={lam}")
    print(f"lamZero_bit_length={lam.bit_length()}")
    print(f"s0_bit_length={lam}")
    print("s0 = 2^(lamZero-1) is not printed")


if __name__ == "__main__":
    main()
