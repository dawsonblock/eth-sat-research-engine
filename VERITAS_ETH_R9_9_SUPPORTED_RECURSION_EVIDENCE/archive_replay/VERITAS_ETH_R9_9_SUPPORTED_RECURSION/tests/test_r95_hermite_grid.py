import pytest
from veritas.research.independent_r95.hermite_grid import check_grid
from veritas.research.eth_interpolation.source_hermite import make_source_tapered_plan


@pytest.mark.parametrize('a,u,M',[(1,1,1),(1,1,3),(2,1,2),(2,2,2),(3,1,1),(3,2,2),(3,3,3),(4,3,5),(5,5,7),(6,4,10)])
def test_source_hermite_loss_from_independent_grid(a,u,M):
    report=check_grid(a=a,u=u,M=M,p=5)
    assert all(r['guard_margin']>=0 for r in report['rows'])
    if a<=3 and M*(2*2**a-1)<=31:
        plan=make_source_tapered_plan(M=M,a=a,u=u,p=5,max_precision_bits=4096,max_terms=256)
        assert [(n.t,n.multiplicity,n.precision_bits) for n in plan.nodes]==[(r['t'],r['multiplicity'],r['precision']) for r in report['rows']]


@pytest.mark.parametrize('a,u,M,p',[(0,1,1,3),(2,3,3,3),(3,3,2,3),(7,1,1,3),(2,1,2,0)])
def test_hermite_grid_rejects_unsupported_hypotheses(a,u,M,p):
    with pytest.raises(ValueError):check_grid(a=a,u=u,M=M,p=p)
