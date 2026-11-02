"""Conformance of the finite reference to the pinned OpenAI preprint.

Every assertion here is traceable to a labelled object in `paper/`:

* `eq:tensor-parameters` (quantitative-contraction.tex, l.87-91) --
  the schedule `u_d`, `a_d`, `L`, `D_arr`.
* l.80-84 -- the leaf threshold `H` and degree bound `Delta`.
* `lem:tensor-packets` (l.114-171) -- packet and port bounds.
* `eq:tensor-packing-conditions` (l.106-109).
* `lem:tapered-hermite` (l.250-269) -- `h`, `q_t`, `D_t`, `p_t`, degree.
* `eq:tensor-mode-multiplicity` (l.443-447) and
  `eq:tensor-mode-budget` (l.452-455).
* `subsec:sharp-fixed-density` (quantitative-reduction.tex, l.86-97) --
  `P_0 = n+1` and the unused-variable factor.

The test re-derives each formula from the paper's text in plain integer
arithmetic and compares it with what the code computes. It checks numeric
agreement only: passing does not prove the paper's theorem, and it does not
upgrade any finite result to a uniform claim.
"""
from __future__ import annotations

from hashlib import sha256
from math import isqrt
from pathlib import Path

import pytest

from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.appendix_d_schedule import schedule_preflight, schedule_path_preflight
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_interpolation.tapered_hermite import make_tapered_plan
from veritas.research.eth_packing_v26.implicit import (
    audit_d3_child_wire_loads, check_implicit_packing, construct_implicit_packing,
    implicit_sparse_mode_source,
)
from veritas.research.eth_recursive_contraction_v39 import describe_integer_network
from veritas.research.eth_recursive_contraction_v39.point_modes import make_point_modes
from veritas.research.eth_recursive_contraction_v39.structural_tuples import structural_tuples
from veritas.research.eth_recursive_contraction_v39.tapered_described import run_tapered_finite

PAPER = Path(__file__).resolve().parents[1] / 'paper'

# Upstream SHA-256 values, as published with the preprint.
PAPER_HASHES = {
    'main_full_version.tex': 'b2e6159d4fb7ea6aa4f89ac15605152b0333a5f7cafe93323492bc20a5c066aa',
    'quantitative-reduction.tex': '0b2b136c4f37ee0583dda40ee0c0d692f4751537d3d18539a389cd467ea8359a',
    'quantitative-contraction.tex': '671642d7b53154d92344e8c4be0240f18929632ebcfdf73b07c3e9939b873860',
    'quantitative-circuits.tex': '0059668a666a35a6e0a67a7c5ed2e9b504862f4207d86e83ce5b7ab4b23fcc11',
}

# Exact formula fragments the assertions below encode. If the pinned source
# ever changes, these fail rather than silently decoupling code from paper.
REQUIRED_FORMULAS = {
    'quantitative-contraction.tex': [
        r'H=\left\lceil\frac{s}{\lfloor\sqrt\lambda\rfloor}\right\rceil',
        r'r=64',
        r'\varepsilon=\frac1{128\cdot1024}',
        r'\Delta=\lceil s^{9/10}\rceil',
        r'u=u_d=\left\lfloor\frac{\varepsilon\lambda}{2^d}\right\rfloor',
        r'a=a_d=2\sum_{j=0}^d u_j',
        r'L=2^a',
        r'D_{\rm arr}=r^{2a}',
        r'M\ge2D_{\rm arr}^{\,2}\Delta',
        r'M\ge L D_{\rm arr}',
        r'2L\le\Delta',
        r'\alpha=2^{a+1}',
        r'h=\lceil3M/u\rceil',
        r'q_t=q(i)=h\max(0,u-i)',
        r'D_t=L/2^i',
        r'p_t=p+8hD_t+8M(a+1)',
        r'M(2L-1)',
        r'(3M/L)2^{i+1}=6M/D',
        r'\sum_Zw_Z\beta_Z<p_t',
        r'6M/r=3M/32<M/8',
        r'a\le4\varepsilon\lambda',
        r'L,D_{\rm arr}\le s^{1/1000}',
    ],
    'quantitative-reduction.tex': [
        r'P_0=n+1',
        r'\ell=1',
        r'multiply the contraction by $2^u$ modulo',
    ],
    'main_full_version.tex': [
        r'r=\left\lfloor\frac{\sqrt\lambda}{\nu^2}\right\rfloor',
        r'Q=\left\lfloor\frac{\lambda}{128\nu}\right\rfloor',
        r'R=(\beta+3)\lceil\sqrt\lambda\rceil',
        r'\tau=\frac1{r\lambda}',
        r'\epsilon=\frac1{br^2\lambda}',
        r'D=r^{2Q}',
        r'2(b+w)D^2\le M',
        r'2Qr^2\le n',
        r'\mathcal B=([r]^Q)^2',
        r'W_0=\frac12\sum_{s=1}^Q(I-\Pi_s)',
        r'M_0=V_0f_{\mathcal I}(W_0)',
        r'\varphi_{u,y}(T)=\prod_{s\in E_{u,y}}\left(1-\frac Ts\right)',
        r'q=\left\lfloor\frac{d_H}{Q}\right\rfloor',
        r'\Phi_e((X_v)_{v\in I_e})',
    ],
}

# A size with lambda = 524290 and Delta = 2**471861 exactly, chosen so the
# paper's power-of-two degree-limit shortcut applies and u_d >= 1 for d <= 2.
BIG_S = 2 ** 524290
BIG_LAMBDA = 524290
BIG_DELTA = 1 << (9 * 52429)
BIG_BITS = 2_000_000


def _squash(text):
    return ' '.join(text.split())


def _paper(name):
    return (PAPER / name).read_text(encoding='utf8')


# --------------------------------------------------------------------------
# Provenance: the vendored source is the pinned source.
# --------------------------------------------------------------------------

@pytest.mark.parametrize('name,expected', sorted(PAPER_HASHES.items()))
def test_vendored_paper_matches_upstream_hashes(name, expected):
    assert sha256((PAPER / name).read_bytes()).hexdigest() == expected


@pytest.mark.parametrize('name,fragments', sorted(REQUIRED_FORMULAS.items()))
def test_paper_contains_every_formula_this_suite_encodes(name, fragments):
    body = _squash(_paper(name))
    for fragment in fragments:
        assert _squash(fragment) in body, fragment


# --------------------------------------------------------------------------
# eq:tensor-parameters and the leaf/degree thresholds.
# --------------------------------------------------------------------------

def paper_lambda(s):
    """lambda = ceil(log_2 s), the paper's first display in subsec:tensor-packing."""
    lam = 0
    while (1 << lam) < s:
        lam += 1
    return lam


def paper_leaf_threshold(s):
    """H = ceil(s / floor(sqrt(lambda)))."""
    return -(-s // isqrt(paper_lambda(s)))


def paper_degree_limit(s):
    """Delta = ceil(s**(9/10)), by exact integer tenth root."""
    target = s ** 9
    low, high = 1, 2
    while high ** 10 < target:
        high *= 2
    while low < high:
        middle = (low + high) // 2
        if middle ** 10 < target:
            low = middle + 1
        else:
            high = middle
    return low


def paper_u(lam, depth):
    """u_d = floor(eps * lambda / 2**d) with eps = 1/(128*1024)."""
    return lam // (128 * 1024 * (1 << depth))


def paper_a(lam, depth):
    """a_d = 2 * sum_{j=0}^{d} u_j."""
    return 2 * sum(paper_u(lam, j) for j in range(depth + 1))


@pytest.mark.parametrize('s', [2, 3, 7, 16, 17, 1000, 2 ** 20 + 1, 2 ** 40, 2 ** 60])
def test_lambda_leaf_and_degree_match_the_paper(s):
    check = schedule_preflight(s, 0, 0, 0, max_size_bits=BIG_BITS)
    assert check['lambda'] == paper_lambda(s)
    assert check['leaf_threshold'] == paper_leaf_threshold(s)
    assert check['degree_limit'] == paper_degree_limit(s)


def test_degree_limit_matches_the_analytic_value_for_powers_of_two():
    # For s = 2**(10k), ceil(s**(9/10)) = 2**(9k) exactly.
    s = 2 ** 524290
    check = schedule_preflight(s, 0, 0, 0, max_size_bits=BIG_BITS)
    assert check['degree_limit'] == 1 << (9 * 52429)


@pytest.mark.parametrize('depth', [0, 1, 2])
def test_schedule_u_and_a_match_the_paper(depth):
    # Above the leaf threshold H and below s/8**depth: an active call.
    edges = 1 << 524281
    check = schedule_preflight(BIG_S, edges, 0, depth, max_size_bits=BIG_BITS)
    assert check['status'] == 'ACTIVE_NUMERIC_PRECONDITIONS_MET'
    assert check['u'] == paper_u(BIG_LAMBDA, depth)
    assert check['a'] == paper_a(BIG_LAMBDA, depth)
    assert check['packet_size_exponent'] == paper_a(BIG_LAMBDA, depth)
    assert check['label_class_exponent'] == 12 * paper_a(BIG_LAMBDA, depth)


def test_derived_parameter_bounds_hold_for_the_paper_regime():
    """a <= 4*eps*lambda and L, D_arr <= s**(1/1000), for large s."""
    lam = BIG_LAMBDA
    a = paper_a(lam, 0)
    assert a <= 4 * lam // (128 * 1024)
    assert (1 << a) ** 1000 <= BIG_S
    assert (64 ** (2 * a)) ** 1000 <= BIG_S


def test_degree_limit_of_the_big_size_is_the_analytic_value():
    check = schedule_preflight(BIG_S, 0, 0, 0, max_size_bits=BIG_BITS)
    assert check['degree_limit'] == BIG_DELTA


def test_d3_preconditions_are_the_paper_inequalities():
    """eq:tensor-packing-conditions, exactly, including both boundaries."""
    from veritas.research.eth_packing_v26 import d3_preconditions

    a = paper_a(BIG_LAMBDA, 0)
    L, D_arr, delta = 1 << a, 64 ** (2 * a), BIG_DELTA
    first = 2 * D_arr ** 2 * delta      # M >= 2 D_arr**2 Delta
    second = L * D_arr                  # M >= L D_arr
    assert d3_preconditions(first, 64, a, delta)['M_ge_2_D_squared_delta'] is True
    assert d3_preconditions(first - 1, 64, a, delta)['M_ge_2_D_squared_delta'] is False
    assert d3_preconditions(second, 64, a, delta)['M_ge_LD'] is True
    assert d3_preconditions(second - 1, 64, a, delta)['M_ge_LD'] is False
    assert d3_preconditions(second, 64, a, 2 * L)['2L_le_delta'] is True
    assert d3_preconditions(second, 64, a, 2 * L - 1)['2L_le_delta'] is False


def test_active_call_reports_the_paper_preconditions():
    edges = 1 << 524281
    check = schedule_preflight(BIG_S, edges, 0, 0, max_size_bits=BIG_BITS)
    assert check['status'] == 'ACTIVE_NUMERIC_PRECONDITIONS_MET'
    assert check['numeric_preconditions'] == {
        'M_ge_2_D_squared_delta': True, 'M_ge_LD': True, '2L_le_delta': True}


def test_path_preflight_enforces_the_paper_child_bound():
    """6M/r = 3M/32 < M/8, so a child has at most 3M/32 edges."""
    parent = 1 << 524282  # active at depth 0, and 3M/32 already below H
    allowed = 3 * parent // 32
    path = schedule_path_preflight(BIG_S, [(parent, 0), (allowed, 0)],
                                   max_size_bits=BIG_BITS)
    assert path['status'] == 'FINITE_SCHEDULE_PATH_NUMERICS_CHECKED'
    assert path['ends_at_leaf'] is True
    rejected = schedule_path_preflight(BIG_S, [(parent, 0), (allowed + 1, 0)],
                                       max_size_bits=BIG_BITS)
    assert rejected['status'] == 'INVALID_CHILD_SHRINK'
    # 3M/32 is strictly below M/8, which is the paper's stronger phrasing.
    assert 3 * parent // 32 < parent // 8


# --------------------------------------------------------------------------
# lem:tapered-hermite.
# --------------------------------------------------------------------------

def paper_tapered_nodes(M, a, u, p):
    L = 1 << a
    h = -(-3 * M // u)
    nodes = {}
    for t in range(-L, L):
        if t == 0:
            continue
        i = (abs(t) & -abs(t)).bit_length() - 1
        q = h * max(0, u - i)
        if q:
            nodes[t] = (i, q, p + 8 * h * (L >> i) + 8 * M * (a + 1))
    return nodes


@pytest.mark.parametrize('M,a,u,p', [
    (3, 1, 1, 5), (4, 1, 1, 5), (5, 1, 1, 7), (6, 1, 1, 9),
    (2, 2, 1, 5), (4, 2, 2, 5), (3, 2, 2, 7),
])
def test_tapered_plan_matches_lemma_tapered_hermite(M, a, u, p):
    plan = make_tapered_plan(M=M, a=a, u=u, p=p)
    expected = paper_tapered_nodes(M, a, u, p)
    assert plan.alpha == 1 << (a + 1)
    assert plan.degree_bound == M * (2 * (1 << a) - 1)
    assert {node.t: (node.valuation, node.multiplicity, node.precision_bits)
            for node in plan.nodes} == expected
    # The paper requires sum_t q_t >= 3ML > M(2L-1).
    assert sum(q for _, q, _ in expected.values()) >= 3 * M * (1 << a)
    # q_t > 0 forces i < u, hence D_t >= 2**(a_{d-1}+u).
    for i, q, _ in expected.values():
        assert (q > 0) == (i < u)


def test_tapered_plan_rejects_violations_of_the_lemma_hypotheses():
    with pytest.raises(ValueError):
        make_tapered_plan(M=2, a=1, u=2, p=5)   # needs 1 <= u <= a and u <= M
    with pytest.raises(ValueError):
        make_tapered_plan(M=2, a=1, u=1, p=5, max_target_precision=4)


# --------------------------------------------------------------------------
# lem:tensor-packets and the mode budget.
# --------------------------------------------------------------------------

def test_packing_count_and_port_bounds_follow_the_paper_formulas():
    """At most 3M/L packets and 3M/r real ports, on an instance that meets them."""
    edges = [(i % 3, i % 4) for i in range(9)]
    packing = construct_implicit_packing(edges, r=2, a=1)
    checked = check_implicit_packing(packing, max_work=None)
    assert checked['valid'] is True
    M, L, r = len(edges), packing.L, packing.r
    D_arr = r ** (2 * packing.a)                               # D_arr = r**(2a)
    assert checked['packet_count'] == D_arr * packing.H // L
    assert checked['packing_count_bound'] is True              # D_arr*H <= 3M
    assert D_arr * packing.H <= 3 * M
    assert checked['symbol_port_bound'] is True                # max_ports*r <= 3M
    assert checked['max_side_symbol_load'] * r <= 3 * M
    assert checked['packet_count'] <= 3 * M // L


def test_child_wire_bound_holds_when_the_packing_hypotheses_hold():
    """lem:tensor-packets(3) => at most 6M/r child wires."""
    edges = [(i % 3, i % 4) for i in range(9)]
    packing = construct_implicit_packing(edges, r=2, a=1)
    checked = check_implicit_packing(packing, max_work=None)
    assert checked['packing_count_bound'] and checked['symbol_port_bound']
    audit = audit_d3_child_wire_loads(packing, coordinate=0, max_work=None)
    assert audit['valid'] is True
    assert audit['status'] == 'FINITE_D3_CHILD_SHRINK_REPLAYED'
    M = len(edges)
    for child in audit['children']:
        assert 2 * child['child_wire_count'] <= 6 * M          # <= 6M/r
        assert child['meets_6M_over_r'] is True
    assert audit['sum_child_wires'] == 2 * M
    assert audit['universal_theorem_proven'] is False


def test_child_bound_definitions_for_the_theorem_radix():
    """r=64: the audit reports 6M/r and the stricter 3M/32 exactly."""
    edges = [(i % 5, (3 * i) % 7) for i in range(11)]
    packing = construct_implicit_packing(edges, r=64, a=1)
    audit = audit_d3_child_wire_loads(packing, coordinate=0, max_work=None)
    assert audit['valid'] is True
    M = len(edges)
    for child in audit['children']:
        assert child['child_wire_count'] == (child['row_half_wire_count'] +
                                            child['column_half_wire_count'])
        assert child['meets_6M_over_r'] == (64 * child['child_wire_count'] <= 6 * M)
        assert child['meets_3M_over_32'] == (32 * child['child_wire_count'] <= 3 * M)
    assert audit['per_child_6M_over_r_bound'] == all(
        child['meets_6M_over_r'] for child in audit['children'])
    assert audit['all_children_meet_3M_over_32'] == all(
        child['meets_3M_over_32'] for child in audit['children'])
    expected = ('FINITE_D3_CHILD_SHRINK_REPLAYED'
                if audit['per_child_6M_over_r_bound'] and
                audit['per_side_port_bound'] else
                'FINITE_D3_CHILD_SHRINK_BOUND_NOT_MET')
    assert audit['status'] == expected


def test_mode_multiplicity_and_budget_are_the_paper_inequalities():
    """6M/D multiplicity and sum w_Z beta_Z < p_t."""
    edges = [(i % 3, (2 * i) % 4) for i in range(6)]
    packing = construct_implicit_packing(edges, r=2, a=2)
    source = implicit_sparse_mode_source(packing, max_work=None)
    precision = 7
    certificate = make_point_modes(source, node=1, precision=precision,
                                   extension_degree=3)
    M, L = len(edges), source['L']
    D = L >> 1                                                # D_t = L/2**i, i=1
    counts = {}
    for mode in certificate['modes']:
        counts[mode['weight']] = counts.get(mode['weight'], 0) + 1
        assert mode['weight'] == mode['exponent'] + 1          # w_Z = b+1
        assert mode['weight'] < precision                      # b+1 < p_t
    assert all(count * D <= 6 * M for count in counts.values())  # 6M/D
    for beta in structural_tuples(certificate['modes'], precision, max_tuples=5000):
        assert sum(exponent * mode['weight']
                   for exponent, mode in zip(beta, certificate['modes'])) < precision


# --------------------------------------------------------------------------
# subsec:sharp-fixed-density -- P_0 = n+1 and the unused-variable factor.
# --------------------------------------------------------------------------

@pytest.mark.parametrize('clauses,expected', [
    ([[1, 2]], 3),
    ([[1, -1]], 4),          # tautology; variable 2 unused
    ([[1, 2], [-1, -2]], 2),
])
def test_count_recovery_uses_paper_precision_and_unused_variables(clauses, expected):
    cnf = CNF.from_lists(2, clauses)
    described = describe_integer_network(from_cnf(cnf), creation_precision=cnf.n + 1,
                                         defining_polynomial=first_irreducible(5))
    outcome = run_tapered_finite(described, target_precision=cnf.n + 1, max_work=2_000_000)
    assert outcome['status'] == 'FINITE_TAPERED_CHILD_RECOVERY_VERIFIED'
    residue = outcome['result'][0][0]
    # 0 <= #F <= 2**n and the residue is taken modulo 2**(n+1).
    assert 0 <= residue <= 2 ** cnf.n
    assert residue == expected


# --------------------------------------------------------------------------
# sec:counting and sec:construction -- the shared-linear-summary half.
# --------------------------------------------------------------------------

def test_parameter_schedule_matches_lemma_incidence_parameters():
    """`eq:parameter-QR` at theorem scale, all numerical hypotheses checked."""
    from math import isqrt
    from veritas.research.eth_counting_v39 import theorem_parameters_from_lambda

    lam = 2 ** 34
    nu = 34
    root = isqrt(lam)
    result = theorem_parameters_from_lambda(lam, b=3, w=3, M=3, d=3, beta=1)
    assert result['status'] == 'THEOREM_PARAMETERS_COMPUTED'
    assert (result['r'], result['Q'], result['R']) == (
        root // (nu * nu), lam // (128 * nu), 4 * root)
    assert result['checks'] == {
        'r_ge_2': True, 'R_ge_32': True, '6R_le_Q': True,
        'interval_in_0_Q': True, 'log2_D_le_lambda_over_128': True,
        'balance_2_b_plus_w_D2_le_M': True, 'balance_2Qr2_le_n': True,
        'tau_le_half': True,
    }
    assert result['runtime_bound_proven'] is False


def test_swap_matrix_remark_is_the_papers_worked_example():
    """The Remark at `main_full_version.tex` l. 2381-2400, verbatim."""
    from fractions import Fraction
    from veritas.research.eth_counting_v39 import build_auxiliary_layout, scaled_parameters

    parameters = scaled_parameters(4, 3, 3, 12, 12, r=2, Q=2, R=2)
    layout = build_auxiliary_layout(parameters)
    u = layout.encode([(0, 1), (0, 1)])            # (00, 11)
    zeta_0 = u
    zeta_1 = layout.encode([(1, 0), (0, 1)])       # (10, 01)
    zeta_2 = layout.encode([(0, 1), (1, 0)])       # (01, 10)
    assert layout.row_polynomial(u) == {
        zeta_0: (Fraction(1),),
        zeta_1: (Fraction(0), Fraction(-1, 2)),
        zeta_2: (Fraction(0), Fraction(-1)),
    }


@pytest.mark.parametrize('clauses,n,expected', [
    ([[1, 2]], 3, 6),
    ([[1, 2], [-1, -2]], 3, 4),
    ([[1, 2, 3]], 3, 7),
    ([[1, 2], [-1, 3], [2, -3]], 4, 6),
])
def test_shared_linear_summaries_count_matches_enumeration(clauses, n, expected):
    """The full `sec:counting` pipeline against exhaustive enumeration."""
    from itertools import product as _product
    from veritas.research.eth_counting_v39 import cnf_instance, count_cnf

    instance = cnf_instance(clauses, n)
    result = count_cnf(clauses, n, r=2, Q=2, R=2, max_work=50_000_000,
                       max_pairs=5_000_000)
    assert result.value == expected
    brute = 0
    for bits in _product((0, 1), repeat=n):
        value = 1
        for scope, factor in zip(instance.scopes, instance.factors):
            value *= factor.evaluate([bits[v] for v in scope])
        brute += value
    assert result.value == brute
    assert result.layout['valid_identity'] is True
    assert result.layout['runtime_bound_proven'] is False
