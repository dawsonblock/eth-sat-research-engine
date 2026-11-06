"""Produce a replayable, bounded point-child certificate for a small XOR CNF."""
import json

from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_packing_v26.implicit import construct_implicit_packing, implicit_mode_source
from veritas.research.eth_recursive_contraction_v39 import (
    check_point_child_expansion_certificate, contract_point_child_expansion,
    describe_integer_network, make_point_modes, run_tapered_finite,
)


def main():
    cnf = CNF.from_lists(2, [[1, 2], [-1, -2]])
    network = describe_integer_network(from_cnf(cnf), creation_precision=3,
                                       defining_polynomial=first_irreducible(4))
    packing = construct_implicit_packing(network.bipartite_edges(), r=2, a=1)
    modes = make_point_modes(implicit_mode_source(packing), node=1, precision=5,
                             extension_degree=4, zeta=(1, 0, 0, 0))
    proof = contract_point_child_expansion(network, modes, max_work=2_000_000)
    # JSON is the intended transport: replay after tuple-to-list conversion.
    transported = json.loads(json.dumps(proof))
    checked = check_point_child_expansion_certificate(network, modes, transported,
                                                      max_work=2_000_000)
    if not checked.get('valid'):
        raise ArithmeticError('transported point-child certificate failed replay')
    strict = run_tapered_finite(network, target_precision=3,
                                require_one_eighth_shrink=True, max_work=2_000_000)
    if strict.get('status') != 'INCONCLUSIVE_CHILD_SIZE_INVARIANT' or 'result' in strict:
        raise ArithmeticError('scaled example did not fail closed on the claimed child bound')
    print(json.dumps({'schema': 'VERITAS_FINITE_CHILD_AUDIT_V1', 'cnf': cnf.as_dict(),
                      'creation_precision': 3, 'mode_certificate': modes,
                      'point_child_certificate': transported,
                      'replay_status': checked, 'strict_run': strict,
                      'scope': 'finite point identity only; no uniform runtime proof'},
                     sort_keys=True))


if __name__ == '__main__':
    main()
