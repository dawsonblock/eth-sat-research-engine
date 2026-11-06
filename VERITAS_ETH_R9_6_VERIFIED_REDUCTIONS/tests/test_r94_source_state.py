from dataclasses import replace

import pytest

from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.tapered_v4.source_state import (
    MANUSCRIPT_SHA256, SourceAdmissionError, SourceContext, SourceLimits,
    SourceNode, SourceTensorReference, SourceVertex, inspect_source_node,
    check_source_transition,
)


def context(s=8, **kwargs):
    values = dict(size_parameter=s, size_constant=2, entry_time_constant=1,
                  entry_polynomial_exponent=2, initial_precision=3,
                  jet_length=1, defining_polynomial=first_irreducible(4 * (s-1).bit_length()))
    values.update(kwargs)
    return SourceContext(**values)


def vertices(ctx, m=1):
    tensor = SourceTensorReference(1, ctx.initial_precision, ctx.defining_polynomial,
                                   ctx.jet_length, "test-reference", b"[0,1]")
    return tuple(SourceVertex(side, e, (e,), tensor)
                 for side in ("row", "column") for e in range(m))


def test_s_is_not_m_and_source_degree_is_not_the_finite_cap():
    ctx = context(s=8)
    node = SourceNode(ctx, 1, vertices(ctx), 0, 3)
    report = inspect_source_node(node)
    assert (report["s"], report["M"], report["extension_degree"]) == (8, 1, 12)
    assert ctx.leaf_threshold == 8
    assert report["schedule"]["status"] == "DIRECT_LEAF_ALLOWED"
    assert report["entry_cost_contract_proven"] is False
    assert report["count_available"] is False and report["theorem_mode_enabled"] is False


@pytest.mark.parametrize("s,lam,H", [(2,1,2), (3,2,3), (4,2,4), (8,3,8), (9,4,5), (16,4,8)])
def test_exact_context_logarithm_and_leaf_boundaries(s, lam, H):
    ctx = context(s)
    assert (ctx.lambda_value, ctx.extension_degree, ctx.leaf_threshold) == (lam, 4*lam, H)


def test_ring_cap_precedes_irreducibility(monkeypatch):
    import veritas.research.tapered_v4.source_state as module
    monkeypatch.setattr(module, "is_irreducible", lambda f: pytest.fail("uncapped algebra invoked"))
    with pytest.raises(SourceAdmissionError):
        SourceContext(1 << 1000, 1, 1, 1, 1, 1, 3)


@pytest.mark.parametrize("field,value", [("size_parameter", True), ("size_constant", 0),
    ("initial_precision", 100), ("jet_length", 100), ("defining_polynomial", 19),
    ("manuscript_sha256", "0"*64)])
def test_invalid_context_parameters_fail(field, value):
    with pytest.raises(ValueError):
        context(**{field:value})


def test_reducible_extension_rejected():
    with pytest.raises(ValueError, match="reducible"):
        context(s=4, defining_polynomial=(1 << 8) | 1)


def test_duplicate_edges_are_distinct_occurrences_and_sides_are_tagged():
    ctx=context()
    tensor=SourceTensorReference(2,3,ctx.defining_polynomial,1,"test",b"parallel")
    vs=(SourceVertex("row",0,(0,1),tensor),SourceVertex("column",0,(0,1),tensor))
    assert SourceNode(ctx,2,vs,0,3).maximum_degree == 2
    with pytest.raises(ValueError, match="owned"):
        SourceNode(ctx,2,(replace(vs[0],ports=(0,0)),vs[1]),0,3)


def test_preserve_creation_ring_and_precision():
    ctx=context(s=16); vs=vertices(ctx)
    child=SourceNode(ctx,1,vs,1,20)
    assert child.vertices[0].tensor.creation_precision == 3
    for tensor in (replace(vs[0].tensor,creation_precision=21),
                   replace(vs[0].tensor,defining_polynomial=19),
                   replace(vs[0].tensor,jet_length=2)):
        with pytest.raises(ValueError,match="creation ring"):
            SourceNode(ctx,1,(replace(vs[0],tensor=tensor),vs[1]),1,20)
    with pytest.raises(ValueError,match="root node precision"):
        SourceNode(ctx,1,vs,0,20)


def test_all_ports_and_vertex_identity_are_checked():
    ctx=context();vs=vertices(ctx)
    with pytest.raises(ValueError,match="endpoint"):
        SourceNode(ctx,1,vs[:1],0,3)
    with pytest.raises(ValueError):
        SourceNode(ctx,1,(replace(vs[0],ports=(True,)),vs[1]),0,3)
    with pytest.raises(ValueError,match="M <="):
        SourceNode(ctx,1,vs,3,3)


def test_entry_byte_budget_and_unknown_semantics_do_not_produce_counts():
    ctx=context(limits=SourceLimits(max_description_bytes=4))
    with pytest.raises(SourceAdmissionError):
        SourceNode(ctx,1,vertices(ctx),0,3)
    ctx=context();node=SourceNode(ctx,0,(),0,3)
    assert not inspect_source_node(node)["entry_semantics_verified"]


def test_scalar_vertices_are_retained():
    ctx=context();scalar=SourceTensorReference(0,3,ctx.defining_polynomial,1,"scalar",b"0")
    node=SourceNode(ctx,0,(SourceVertex("row",0,(),scalar),),0,3)
    assert len(node.vertices) == 1 and not inspect_source_node(node)["count_available"]


def test_leaf_cannot_generate_child_and_context_cannot_change():
    ctx=context(s=16);parent=SourceNode(ctx,1,vertices(ctx),0,3)
    child=SourceNode(ctx,0,(),1,4)
    with pytest.raises(ValueError,match="leaf"):
        check_source_transition(parent,child)
    other=replace(ctx,entry_time_constant=2)
    with pytest.raises(ValueError,match="context"):
        check_source_transition(parent,replace(child,context=other))


def test_changed_pin_fails_before_admission_claim(monkeypatch):
    from pathlib import Path
    ctx=context();node=SourceNode(ctx,0,(),0,3)
    original=Path.read_bytes
    monkeypatch.setattr(Path,"read_bytes",lambda p: b"changed" if p.name == "quantitative-contraction.tex" else original(p))
    with pytest.raises(SourceAdmissionError) as caught:
        inspect_source_node(node)
    assert caught.value.status == "INCONCLUSIVE_SOURCE_MISMATCH"


def test_small_nonleaf_is_not_an_eligible_active_call():
    ctx = context(s=16)
    parent = SourceNode(ctx, 9, vertices(ctx, 9), 0, 3)
    child = SourceNode(ctx, 0, (), 1, 4)
    assert inspect_source_node(parent)["schedule"]["status"] == "INCONCLUSIVE_SCHEDULE"
    with pytest.raises(SourceAdmissionError) as caught:
        check_source_transition(parent, child)
    assert caught.value.status == "INCONCLUSIVE_SCHEDULE"
