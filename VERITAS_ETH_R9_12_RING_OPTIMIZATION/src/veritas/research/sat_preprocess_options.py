"""Options for bounded Phase C preprocessing stages."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PreprocessOptions:
    remove_tautology_clauses: bool = True
    enable_unit_propagation: bool = True
    # Experimental: only for single-component formulas; default off (#SAT fragile).
    enable_safe_pure_literals: bool = False
    max_pure_literal_steps: int = 64

    def to_dict(self) -> dict:
        return {
            "remove_tautology_clauses": self.remove_tautology_clauses,
            "enable_unit_propagation": self.enable_unit_propagation,
            "enable_safe_pure_literals": self.enable_safe_pure_literals,
            "max_pure_literal_steps": self.max_pure_literal_steps,
        }


DEFAULT_PREPROCESS_OPTIONS = PreprocessOptions()
