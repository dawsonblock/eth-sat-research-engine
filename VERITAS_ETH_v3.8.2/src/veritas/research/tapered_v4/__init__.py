"""Bounded experimental tapered recursion; no theorem-level runtime claim."""
from .model import RecursionPolicy, TaperedState
from .recursor import contract_recursive, replay_certificate
from .parameters import inspect_active_theorem_capacity, inspect_finite_schedule
from .cnf_count import count_source_cnf_finite
from .child_audit import (build_finite_child_size_certificate,
                          check_finite_child_size_certificate)

__all__ = ['RecursionPolicy', 'TaperedState', 'contract_recursive', 'replay_certificate',
           'inspect_finite_schedule', 'inspect_active_theorem_capacity', 'count_source_cnf_finite', 'build_finite_child_size_certificate',
           'check_finite_child_size_certificate']
