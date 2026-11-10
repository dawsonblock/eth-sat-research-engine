"""Top-level recursive work census on growing degree-three networks.

For one recursive call this measures, without contracting any child, the
quantities the call would request: interpolation points, the exact affine-row
support size at each point (counted by the factorized circuit, never
expanded), children per support tuple and their wire counts. It then probes
which modes each child actually depends on by single-mode flips from beta=0
and recomputes the cache key of every child. If those dependency sets are
exact, the sum over beta is itself a contraction over mode variables whose
interaction graph is the union of the sets; its elimination width is reported
beside the parent's wire elimination width.

Dependency sets are measured on the flips performed, plus a consistency check
on random support tuples. They are empirical, not a factorization certificate.
Nothing here is a source-qualified call or evidence for a complexity bound.
"""
import argparse
from math import log2
from pathlib import Path
import random
import sys
from time import monotonic
from dataclasses import replace

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent/'src'))
sys.path.insert(0, str(ROOT))
from experiment_r912_interaction import graph, separated_layout
from veritas.research.parent_child_r98.constructor import construct_children
from veritas.research.parent_child_r98.model import Budget, ExponentTuple, canonical
from veritas.research.parent_child_r98.shrinking_cli import load_input, _check_output
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
from veritas.research.parent_child_r99.basis import build_packet_modes
from veritas.research.parent_child_r99.resources import computation_key
from veritas.research.parent_child_r99.row_degree import certify_row_degree
from veritas.research.parent_child_r99.support import fold_source_forms
from veritas.research.parent_child_r99.support_circuit import SupportCircuit
from veritas.research.parent_child_r912.elimination import EliminationBudget, plan_order, verify_order, call_scopes
from veritas.research.parent_child_r912.jet_recovery import JetRecovery
from veritas.research.parent_child_r912.layout import finite_layout

CENSUS_BUDGET = EliminationBudget(max_width=30, max_table_entries=1 << 30, max_live_entries=1 << 32, max_work=1 << 40)


def _table(rng):
    """Positive 2x2x2 table with every flattening of rank > 1."""
    while True:
        table = [rng.randrange(1, 5) for _ in range(8)]
        if all(any(table[i]*table[j | 1 << bit] != table[j]*table[i | 1 << bit]
                   for i in range(8) for j in range(8) if not (i | j) & 1 << bit) for bit in range(3)):
            return table


def random_cubic(n, seed):
    """Simple random 3-regular bipartite graph: the union of three disjoint perfect matchings."""
    if n < 4:
        raise ValueError('at least four vertices per side required')
    rng = random.Random(seed)
    while True:
        used, edges = set(), []
        for _ in range(3):
            for _ in range(1000):
                perm = list(range(n))
                rng.shuffle(perm)
                if all((r, perm[r]) not in used for r in range(n)):
                    break
            else:
                break
            used.update((r, perm[r]) for r in range(n))
            edges += [(r, perm[r]) for r in range(n)]
        if len(edges) == 3*n:
            break
    edges.sort()
    vertices = []
    for side in (0, 1):
        for v in range(n):
            vertices.append({'side': 'column' if side else 'row',
                             'ports': [e for e, pair in enumerate(edges) if pair[side] == v], 'table': _table(rng)})
    return {'root_s': 4*n, 'edges': 3*n, 'precision': 512, 'extension_degree': 10, 'vertices': vertices}


def instance(family, n, seed):
    if family == 'circulant':
        return graph(n, seed)
    if family == 'random_cubic':
        return random_cubic(n, 9120 + 1000*n + seed)
    raise ValueError('unknown family')


def child_keys(call, layout, folded, beta, budget):
    children = construct_children(call, layout, folded, ExponentTuple(folded.content_digest, tuple(beta)),
                                  budget=budget, _admitted=True, require_shrink=True)
    return [computation_key(child.as_parent(call), ()) for child in children], [c.edge_count for c in children]


def analyse_point(call, layout, folded, row_certificate, budget, rng, checks):
    modes, precision = folded.certificate['modes'], folded.certificate['precision']
    circuit = SupportCircuit(modes, precision, budget=budget, row_certificate=row_certificate,
                             max_local_states=2_000_000)
    support = circuit.count()
    out = {'modes': len(modes), 'precision': precision, 'log2_support': log2(support),
           'support_size_bits': support.bit_length(), 'components': circuit.summary()['components'],
           'largest_local_support': circuit.summary()['largest_local_support'],
           'max_total_weight': sum(m['weight'] * max(part[circuit.components[c][0].index(j)] for part, _ in
                                   circuit.components[c][2]) for c in range(len(circuit.components))
                                   for j in circuit.components[c][0] for m in [modes[j]]),
           'weights': sorted({m['weight'] for m in modes})}
    out['precision_cutoff_prunes'] = out['max_total_weight'] >= precision
    zero = (0,)*len(modes)
    base, wires = child_keys(call, layout, folded, zero, budget)
    out.update(children_per_tuple=len(base), child_wires=sorted(set(wires)), parent_wires=call.edge_count)
    depends = [set() for _ in base]
    for j in range(len(modes)):
        beta = list(zero)
        beta[j] = 1
        if not circuit.contains(tuple(beta)):
            continue
        keys, _ = child_keys(call, layout, folded, beta, budget)
        if len(keys) != len(base):
            raise ValueError('child count depends on beta')
        for k, (a, b) in enumerate(zip(base, keys)):
            if a != b:
                depends[k].add(j)
    # Children whose measured dependency set misses supp(beta) must be unchanged.
    tuples = circuit.tuples(limit=10**6) if support <= 10**6 else None
    consistent = True
    for _ in range(checks):
        if tuples is not None:
            beta = list(rng.choice(tuples))
        else:
            beta = [rng.randrange(2) for _ in modes]
            if not circuit.contains(tuple(beta)):
                continue
        keys, _ = child_keys(call, layout, folded, beta, budget)
        on = {j for j, x in enumerate(beta) if x}
        consistent &= all(a == b for a, b, dep in zip(base, keys, depends) if not dep & on)
    variables = tuple(range(len(modes)))
    scopes = tuple(tuple(sorted(d)) for d in depends if d)
    isolated = [(j,) for j in variables if not any(j in d for d in depends)]
    order = plan_order(scopes + tuple(isolated), variables)
    width = verify_order(scopes + tuple(isolated), variables, order, CENSUS_BUDGET)['width'] if variables else 0
    out.update(dependency_set_sizes=sorted(len(d) for d in depends),
               log2_distinct_children_if_factorized=log2(sum(2**len(d) for d in depends)) if depends else 0.0,
               mode_graph_elimination_width=width, random_tuple_consistency=consistent,
               dependency_method='SINGLE_MODE_FLIPS_FROM_ZERO_WITH_RANDOM_CONSISTENCY_CHECKS')
    return out


def census(family, n, seed, layout_name, samples, checks, max_seconds):
    started = monotonic()
    data = instance(family, n, seed)
    rng = random.Random(seed)
    path = Path('/dev/shm' if Path('/dev/shm').is_dir() else '/tmp')/f'r912_census_{family}_{n}_{seed}.json'
    path.write_bytes(canonical(data))
    try:
        call = load_input(path, max_extension_degree=12)
    finally:
        path.unlink()
    policy = replace(DEFAULT_SHRINKING_POLICY, max_work=2_000_000_000, max_seconds=max_seconds,
                     max_edges=1024, max_tuples=100_000, max_precision=65536,
                     max_certificate_bytes=1_000_000_000)
    budget = Budget(policy)
    scopes, variables = call_scopes(call)
    wire_width = verify_order(scopes, variables, plan_order(scopes, variables), CENSUS_BUDGET)['width']
    layout = (separated_layout if layout_name == 'separated' else finite_layout)(call, 1, 1, budget)
    row_certificate = certify_row_degree(call, 1, budget=budget)
    recovery = JetRecovery(call, layout, row_certificate, budget=budget, max_points=4096)
    nodes = {node['t']: node['multiplicity'] for node in recovery.description['nodes']}
    record = {'schema': 'VERITAS_R912_CHILD_GROWTH_CENSUS_V1', 'family': family, 'n': n, 'seed': seed,
              'layout': layout_name, 'wires': call.edge_count, 'wire_elimination_width': wire_width,
              'interpolation_points': recovery.description['actual_point_count'], 'nodes': nodes,
              'source_qualified': False, 'complexity_evidence': False}
    per_node, seen = {}, {}
    for t, zeta, precision in recovery.points():
        if seen.get(t, 0) >= samples:
            continue
        original = build_packet_modes(call, layout, t, zeta, budget=budget, row_certificate=row_certificate)
        folded = fold_source_forms(call, layout, original, budget=budget)
        if not folded.certificate['modes']:
            continue
        seen[t] = seen.get(t, 0) + 1
        result = analyse_point(call, layout, folded, row_certificate, budget, rng, checks)
        per_node.setdefault(str(t), []).append(result)
    record['sampled_points'] = per_node
    record['sampled_points_agree'] = all(
        all(canonical({k: v for k, v in r.items()}) == canonical(rs[0]) for r in rs) for rs in per_node.values())
    first = [rs[0] for rs in per_node.values()]
    if first:
        terms = max(r['log2_support'] for r in first)
        children = max(r['children_per_tuple'] for r in first)
        record['log2_child_requests_top_call_estimate'] = log2(record['interpolation_points']) + terms + log2(children)
        record['estimate_rule'] = 'POINT_COUNT_TIMES_LARGEST_SAMPLED_SUPPORT_TIMES_CHILDREN_PER_TUPLE'
        record['mode_graph_elimination_width'] = max(r['mode_graph_elimination_width'] for r in first)
        record['log2_distinct_children_if_factorized'] = max(r['log2_distinct_children_if_factorized'] for r in first)
    record['elapsed_seconds'] = monotonic() - started
    return record


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output-dir', type=Path, required=True)
    ap.add_argument('--family', choices=('circulant', 'random_cubic'), action='append')
    ap.add_argument('--sizes', type=int, nargs='+', default=[22, 24, 28, 32, 40, 48, 64, 80, 96, 112])
    ap.add_argument('--seeds', type=int, nargs='+', default=[5])
    ap.add_argument('--layout', choices=('default', 'separated'), default='default')
    ap.add_argument('--samples-per-node', type=int, default=2)
    ap.add_argument('--consistency-checks', type=int, default=8)
    ap.add_argument('--max-seconds', type=int, default=1800)
    args = ap.parse_args(argv)
    _check_output(args.output_dir)
    args.output_dir.mkdir(parents=True, exist_ok=False)
    rows = []
    for family in args.family or ['circulant', 'random_cubic']:
        for n in args.sizes:
            for seed in args.seeds:
                name = f'{family}_n{n:03d}_s{seed}'
                try:
                    record = census(family, n, seed, args.layout, args.samples_per_node,
                                    args.consistency_checks, args.max_seconds)
                except Exception as exc:
                    record = {'family': family, 'n': n, 'seed': seed, 'status': 'INCONCLUSIVE',
                              'reason': f'{type(exc).__name__}: {exc}'}
                (args.output_dir/f'{name}.json').write_bytes(canonical(record))
                rows.append(record)
                keys = ('wires', 'wire_elimination_width', 'interpolation_points',
                        'log2_child_requests_top_call_estimate', 'mode_graph_elimination_width',
                        'log2_distinct_children_if_factorized', 'sampled_points_agree', 'reason')
                print(name, {k: (round(record[k], 2) if type(record[k]) is float else record[k])
                             for k in keys if k in record}, flush=True)
    (args.output_dir/'summary.json').write_bytes(canonical({'schema': 'VERITAS_R912_CHILD_GROWTH_SUMMARY_V1',
        'layout': args.layout, 'rows': rows, 'source_qualified': False, 'complexity_evidence': False}))


if __name__ == '__main__':
    main()
