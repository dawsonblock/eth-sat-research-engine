"""Shared linear summaries: the polynomial-construction half of the preprint.

This package implements `sec:counting` and `sec:construction` of the pinned
OpenAI preprint (vendored in `paper/`), which the earlier `app:tensor`
contraction reference does not cover:

* `parameters` -- `lem:incidence-parameters`, the numerical schedule.
* `auxiliary` -- `subsec:incidence-layout`, `lem:swaps-matrix`,
  `lem:swaps-support`, the rows `P_u(T)`.
* `labels` -- `lem:incidence-labels`, deterministic schedules `a_v, d_f`.
* `embedding` -- `subsec:embedding`, copies, rows `P_{f,v}`, matrices `C_{t,g}`.
* `layout` -- `def:layout` verification.
* `separation` -- `lem:measurement-separation`.
* `taylor` -- `lem:boolean-differences` and `eq:full-taylor-sum`.
* `count` -- `H(0) = Z`, the end-to-end exact count.

Everything is exact over `Q` and bounded by explicit caps. This is a finite
reference: it does not establish the paper's subexponential running-time
bound, and the parameter tuples it can execute fail most of the numerical
hypotheses in `lem:incidence-parameters`.
"""
from .parameters import (FormParameters, ceil_log2, scaled_parameters,
                         theorem_parameters, theorem_parameters_from_lambda)
from .auxiliary import AuxiliaryLayout, build_auxiliary_layout
from .labels import Schedules, ScheduleBudgetExceeded, build_schedules, choose_schedules
from .instance import FactorInstance, PolynomialFactor, clause_factor, cnf_instance
from .embedding import EmbeddedForms, build_embedded_forms
from .layout import LayoutReport, in_row_space, verify_layout
from .separation import (SeparationBudgetExceeded, SeparationResult,
                         ring_add, ring_from_constant, ring_from_polynomial,
                         ring_mul, ring_one, ring_pow, ring_scale, ring_sub,
                         ring_zero, separation_sum)
from .taylor import TaylorResult, enumerate_restriction_pairs, taylor_series
from .count import (CountingBudgetExceeded, CountingFailure, CountingResult,
                    count_cnf, count_instance, solve_exact, taylor_equations)

__all__ = [
    'FormParameters', 'ceil_log2', 'scaled_parameters', 'theorem_parameters',
    'theorem_parameters_from_lambda',
    'AuxiliaryLayout', 'build_auxiliary_layout',
    'Schedules', 'ScheduleBudgetExceeded', 'build_schedules', 'choose_schedules',
    'FactorInstance', 'PolynomialFactor', 'clause_factor', 'cnf_instance',
    'EmbeddedForms', 'build_embedded_forms',
    'LayoutReport', 'in_row_space', 'verify_layout',
    'SeparationBudgetExceeded', 'SeparationResult', 'ring_add',
    'ring_from_constant', 'ring_from_polynomial', 'ring_mul', 'ring_one',
    'ring_pow', 'ring_scale', 'ring_sub', 'ring_zero', 'separation_sum',
    'TaylorResult', 'enumerate_restriction_pairs', 'taylor_series',
    'CountingBudgetExceeded', 'CountingFailure', 'CountingResult',
    'count_cnf', 'count_instance', 'solve_exact', 'taylor_equations',
]
