"""Bounded, independently checked *finite* implicit tensor references.

NOT the D.4.4 geometric-tile weighted-mode recursion or a subexponential solver.
"""
from .implicit_children import (make_child_certificate, check_child_certificate,
                                make_bipartite_edges, ImplicitBudgetExceeded)
__all__ = ['make_child_certificate','check_child_certificate',
           'make_bipartite_edges','ImplicitBudgetExceeded']
