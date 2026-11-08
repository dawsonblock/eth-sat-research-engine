"""Check every supported folded coefficient against independent parent elimination."""
import argparse
from pathlib import Path

from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.jets import JetRing
from veritas.research.parent_child_r98.model import Budget, ExponentTuple, ModeSet, canonical
from veritas.research.parent_child_r98.shrinking_cli import load_input
from veritas.research.parent_child_r98.constructor import construct_children
from veritas.research.parent_child_r98.engine import leaf
from veritas.research.parent_child_r98.shrinking_oracle import tuple_coefficient
from veritas.research.parent_child_r99.cli import load_layout
from veritas.research.parent_child_r99 import build_packet_modes
from veritas.research.parent_child_r99.support import fold_source_forms, build_support
from veritas.research.parent_child_r99.support_check import verify_support
from veritas.research.tapered_v4.provenance import source_binding


def run(root):
    budget = Budget()
    parent = load_input(root/'examples/r99_multislot_crossing2.json')
    layout = load_layout(parent, root/'examples/r99_multislot_crossing2_layout.json', budget)
    original = build_packet_modes(parent, layout, 1, (1 << 40, 0, 0, 0), budget=budget)
    folded = fold_source_forms(parent, layout, original, budget=budget)
    support = build_support(original, folded, budget=budget)
    verify_support(parent, layout, original, folded, support, budget=budget)
    ring = JetRing(ExtensionRing(original.certificate['precision'], parent.defining_polynomial), 1)
    checked = []
    for values in support.record['tuples']:
        beta = ExponentTuple(folded.content_digest, tuple(values))
        children = construct_children(parent, layout, folded, beta, budget=budget, _admitted=True)
        product = ring.one
        for child in children:
            product = ring.mul(product, leaf(child.as_parent(parent), budget))
        reference = tuple_coefficient(parent, layout, folded, beta, budget=budget)
        if product != reference:
            raise ValueError('folded child product differs from independent parent coefficient')
        checked.append({'beta': values, 'value': product})
    if not any(2 in row['beta'] and row['value'] != ring.zero for row in checked):
        raise ValueError('fixture lost its nonzero exponent-two coefficient')
    return {'status': 'PASS_INDEPENDENT_FOLDED_COEFFICIENTS', 'coefficients': checked,
            'parent_digest': parent.content_digest, 'source_qualified': False,
            'implementation_source_sha256': source_binding()['digest']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.output.resolve().is_relative_to(root) or args.output.exists():
        parser.error('select a new evidence file outside the source tree')
    report = run(root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical(report))
    print(report['status'])
