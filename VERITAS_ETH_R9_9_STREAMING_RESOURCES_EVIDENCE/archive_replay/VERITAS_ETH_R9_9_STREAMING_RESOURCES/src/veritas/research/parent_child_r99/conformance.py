"""Manuscript-bound development obligations, not self-issued qualifications."""
from veritas.research.paper_verification.source_registry import source_registry


def conformance_ledger():
    pin = source_registry()
    rows = [
        ('schedule', 'eq:tensor-parameters', 'paper_verification.exact_parameters',
         'paper_verification.exact_parameters.check_schedule',
         'FINITE_FORMULAS_CHECKED', 'source-size inputs and all recursive schedule hypotheses'),
        ('packing', 'lem:tensor-packets', 'parent_child_r98.packing',
         'paper_verification.packing_checker',
         'BOUNDED_LAYOUT_AUDIT', 'construct source-compliant padded packets under all three inequalities'),
        ('modes', 'eq:tensor-mode-expansion', 'parent_child_r99.basis',
         'parent_child_r98.modes.independent_modes',
         'BOUNDED_GENERAL_MODES', 'lazy general mode inventory and jet-length greater than one'),
        ('tuples', 'eq:tensor-mode-budget', 'parent_child_r98.modes.weighted_tuples',
         'parent_child_r98.modes.TupleChecker',
         'BOUNDED_COMPLETE_ENUMERATION', 'source partition-count and bit-operation proof'),
        ('children', 'subsec:tensor-children', 'parent_child_r98.constructor',
         'parent_child_r98.independent.reference_children',
         'BOUNDED_GENERAL_CONSTRUCTION', 'universal recipe and port refinement, arbitrary recursive jets'),
        ('identity', 'eq:tensor-recursion-identity', 'parent_child_r99.engine',
         'parent_child_r99.supported_verify',
         'BOUNDED_POINT_IDENTITIES', 'connected multislot full-Hermite two-active-level acceptance and independent recursive replay'),
        ('hermite', 'lem:tapered-hermite', 'parent_child_r99.recovery',
         'paper_verification.hermite_checker',
         'BOUNDED_COMPLETE_TAPERED_RECOVERY', 'recursive creation-lift and coefficientwise precision correspondence'),
        ('complexity', 'subsec:tensor-cost', 'parent_child_r99.preflight',
         'NONE_UNIVERSAL', 'COMPLEXITY_NOT_ESTABLISHED',
         'bit-operation and live-space proofs including lazy entries, modes and evidence'),
    ]
    return {'schema': 'VERITAS_R99_CONFORMANCE_LEDGER_V1', 'paper': pin,
            'obligations': [{'id': ident, 'label': label, 'statement': pin['labels'][label],
                             'implementation': impl, 'checker': check, 'scope': scope, 'remaining': remaining,
                             'universal_executable_correspondence_proved': False}
                            for ident, label, impl, check, scope, remaining in rows],
            'source_qualified': False, 'theorem_mode_enabled': False,
            'arbitrary_density_sat_pipeline': 'NOT_IMPLEMENTED',
            'formal_proof_gate': 'EXISTING_MODEL_THEOREMS_REQUIRE_SEPARATE_KERNEL_AND_AXIOM_REPORT'}
