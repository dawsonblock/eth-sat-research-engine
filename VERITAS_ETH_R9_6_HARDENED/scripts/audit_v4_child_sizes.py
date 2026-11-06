"""Replay the recorded finite eight-edge child-size witness."""
import argparse
import json
from hashlib import sha256
from pathlib import Path

from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_recursive_contraction_v39 import describe_integer_network
from veritas.research.eth_recursive_contraction_v39.point_modes import make_point_modes
from veritas.research.eth_packing_v26.implicit import (
    construct_implicit_packing, implicit_mode_source,
)
from veritas.research.tapered_v4 import (
    build_finite_child_size_certificate, check_finite_child_size_certificate,
)
from veritas.research.tapered_v4.certificates import canonical


EXPECTED_MODE_SHA256 = '5ffc1f0f1489ef1902e5e801aa4fe9c29019d2e3d9de6f33b88acdafa14fbeb8'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    args = parser.parse_args()

    cnf = CNF.from_lists(8, [[i] for i in range(1, 9)])
    polynomial = first_irreducible(5)
    parent = describe_integer_network(from_cnf(cnf), creation_precision=9,
                                      defining_polynomial=polynomial)
    packing = construct_implicit_packing(parent.bipartite_edges(), r=4, a=1)
    source = implicit_mode_source(packing)
    mode_certificate = make_point_modes(
        source, node=-1, precision=521, extension_degree=5,
        zeta=(0, 0, 0, 0, 0), max_parent_wires=8)
    mode_hash = sha256(canonical(mode_certificate)).hexdigest()
    if mode_hash != EXPECTED_MODE_SHA256:
        raise SystemExit('reconstructed point certificate differs from the recorded run')

    certificate = build_finite_child_size_certificate(parent, mode_certificate, ())
    verdict = check_finite_child_size_certificate(parent, mode_certificate, (), certificate)
    if not verdict['valid']:
        raise SystemExit('finite child audit failed replay')
    record = {'cnf': cnf.as_dict(), 'audit': certificate, 'replay': verdict}
    args.output.write_text(json.dumps(record, sort_keys=True, separators=(',', ':')) + '\n',
                           encoding='utf8')
    print(json.dumps({
        'status': verdict['status'],
        'parent_edges': certificate['parent_edges'],
        'witness_child_edges': certificate['child_edges'],
        'witness_group': certificate['witness_group'],
        'shrink_ratio': certificate['shrink_ratio'],
        'finite_six_M_over_r_bound': certificate['all_children_meet_finite_six_M_over_r'],
        'theorem_premises_verified': certificate['theorem_premises_verified'],
        'uniform_shrink_verified': certificate['uniform_shrink_verified'],
        'result': certificate['result'],
        'certificate': str(args.output),
    }, sort_keys=True))


if __name__ == '__main__':
    main()
