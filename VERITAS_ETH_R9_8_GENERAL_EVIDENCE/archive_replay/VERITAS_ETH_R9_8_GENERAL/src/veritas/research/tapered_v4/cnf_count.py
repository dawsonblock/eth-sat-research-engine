"""Source-shaped CNF reduction connected to the finite recursive reference."""
from veritas.core.cnf import CNF
from veritas.research.source_cnf import source_cnf_network
from veritas.research.source_cnf_check import check_source_cnf_network
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_arithmetic.boolean_count import recover_boolean_count
from veritas.research.math_exact.oracle import exhaustive_count
from veritas.research.eth_recursive_contraction_v39.described_network import describe_integer_network
from .model import RecursionPolicy, TaperedState
from .recursor import contract_recursive


def count_source_cnf_finite(cnf: CNF, policy: RecursionPolicy, *, extension_degree=5,
                            max_clause_width=8, max_wires=64, max_factors=10000,
                            verify_exhaustive=False, oracle_max_variables=16,
                            oracle_max_work=2_000_000):
    """Return an exact integer count only on completed finite contraction.

    The user-supplied finite policy controls leaves and any nonshrinking
    fallback. This entry point never enables either automatically. A failure
    or unsupported input carries no partial count. No theorem claim is made.
    """
    if not isinstance(cnf, CNF) or not isinstance(policy, RecursionPolicy):
        raise TypeError('CNF and RecursionPolicy required')
    if type(extension_degree) is not int or not 1 <= extension_degree <= 8:
        raise ValueError('extension degree must be in 1..8')
    if type(verify_exhaustive) is not bool:
        raise ValueError('verify_exhaustive must be Boolean')
    if type(oracle_max_variables) is not int or not 0 <= oracle_max_variables <= 24:
        raise ValueError('oracle_max_variables must be in 0..24')
    if type(oracle_max_work) is not int or not 1 <= oracle_max_work <= 10_000_000:
        raise ValueError('oracle_max_work must be in 1..10000000')
    if verify_exhaustive and cnf.n > oracle_max_variables:
        return {'status': 'INCONCLUSIVE_RESOURCE_LIMIT', 'reason': 'independent oracle variable cap exceeded'}
    if verify_exhaustive and (1 << cnf.n) * (1 + cnf.n + sum(1 + len(c) for c in cnf.clauses)) > oracle_max_work:
        return {'status': 'INCONCLUSIVE_RESOURCE_LIMIT', 'reason': 'independent oracle work cap exceeded'}
    try:
        encoded = source_cnf_network(cnf, max_clause_width=max_clause_width,
                                     max_wires=max_wires, max_factors=max_factors)
        structural = check_source_cnf_network(cnf, encoded, max_wires=max_wires,
                                             max_factors=max_factors)
        if structural.get('valid') is not True:
            return {'status': 'INCONCLUSIVE_INVARIANT_FAILURE',
                    'reason': 'source CNF structure did not pass independent checking',
                    'structural_check': structural}
        if encoded.network.edges > 64:
            return {'status': 'INCONCLUSIVE_RESOURCE_LIMIT', 'reason': 'described network edge cap exceeded'}
        precision = cnf.n + 1
        if precision > policy.max_precision_bits:
            return {'status': 'INCONCLUSIVE_RESOURCE_LIMIT', 'reason': 'root precision cap exceeded'}
        polynomial = first_irreducible(extension_degree)
        network = describe_integer_network(encoded.network, creation_precision=precision,
                                            defining_polynomial=polynomial)
        state = TaperedState(network, 0, precision, polynomial, 1, network.edges)
        result = contract_recursive(state, policy)
    except (MemoryError, RecursionError):
        return {'status': 'INCONCLUSIVE_RESOURCE_LIMIT', 'reason': 'construction resources exhausted'}
    except ValueError as exc:
        return {'status': 'INCONCLUSIVE_INPUT_OR_CAP', 'reason': str(exc)}
    if result['status'] != 'EXACT_MODULAR_CONTRACTION_FINITE':
        return result
    residue = result['result']
    if len(residue) != 1 or len(residue[0]) != extension_degree or any(residue[0][1:]):
        return {'status': 'INCONCLUSIVE_INVARIANT_FAILURE',
                'reason': 'integer network contraction has non-scalar coordinates',
                'ledger': result['ledger']}
    full_residue = (residue[0][0] << len(encoded.unused_variables)) % (1 << precision)
    try:
        count = recover_boolean_count(full_residue, precision=precision, num_variables=cnf.n)
    except ValueError as exc:
        return {'status': 'INCONCLUSIVE_INVARIANT_FAILURE', 'reason': str(exc),
                'ledger': result['ledger']}
    if verify_exhaustive and exhaustive_count(cnf, max_variables=oracle_max_variables) != count:
        return {'status': 'INCONCLUSIVE_INVARIANT_FAILURE',
                'reason': 'independent exhaustive model count disagrees',
                'ledger': result['ledger']}
    return {'status': 'EXACT_COUNT_FINITE', 'count': count,
            'formula_sha256': encoded.formula_digest,
            'unused_variables': encoded.unused_variables,
            'network_edges': network.edges, 'original_edges': encoded.original_edges,
            'residue_before_unused': residue[0][0], 'precision': precision,
            'independent_exhaustive_oracle_used': verify_exhaustive,
            'independent_structure_checked': True,
            'point_identities_checked': result['ledger']['counters'].get('oracle_point_checks', 0),
            'tuple_identities_checked': result['ledger']['counters'].get('oracle_tuple_checks', 0),
            'ledger': result['ledger'], 'certificate': result['certificate'],
            'subexponential_runtime_proven': False}
