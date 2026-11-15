"""Toy decomposition work table from UNIVERSAL_SAT_SPEEDUP_PLAN §2."""
from veritas.research.sat_work_accounting import (
    DecompositionWorkLedger,
    aggregate_ledger,
    ledger_totals_summary,
    toy_child_sum_exponent,
)


def test_toy_rho_09_s_80_q_128_doubles_speedup():
    t = toy_child_sum_exponent(s=80, rho=0.9, q=128)
    assert t["w_children_total"] == 2**79
    assert t["speedup_ratio_before_overhead"] == 2.0


def test_toy_q_256_break_even():
    t = toy_child_sum_exponent(s=80, rho=0.9, q=256)
    assert t["w_children_total"] == t["w_old"]


def test_toy_q_1024_worse_than_parent():
    t = toy_child_sum_exponent(s=80, rho=0.9, q=1024)
    assert t["w_children_total"] > t["w_old"]


def test_ledger_includes_overhead():
    led = DecompositionWorkLedger(
        name="demo",
        w_old=2**80,
        w_transform=1,
        child_works=(2**72,) * 128,
        w_reconstruct=1,
        w_check=1,
    )
    assert led.w_new == led.w_transform + 128 * (2**72) + 2
    assert led.speedup_ratio() == 2**80 / led.w_new


def test_ledger_totals_summary():
    agg = aggregate_ledger(
        [
            DecompositionWorkLedger("a", w_old=10, w_transform=3),
            DecompositionWorkLedger("b", w_old=10, w_transform=5),
        ]
    )
    totals = ledger_totals_summary(agg)
    assert totals["w_total_reported"] == 8
    assert totals["w_by_step_name"]["a"] == 3
