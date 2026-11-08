from dataclasses import replace
from math import comb
import pytest
from veritas.research.parent_child_r98.model import Budget
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
from veritas.research.parent_child_r99.row_degree import certify_row_degree
from veritas.research.parent_child_r910.recovery import Recovery


@pytest.mark.parametrize('u',[1,2])
def test_node_specific_precision_and_independent_functional(u):
    from test_r99_general_packets import fixture
    parent,layout=fixture(u=u,degree=5)
    budget=Budget(replace(DEFAULT_SHRINKING_POLICY,max_work=1000000000))
    degree=certify_row_degree(parent,layout.a,budget=budget)
    a=Recovery(parent,layout,degree,budget=budget,max_points=256)
    b=Recovery(parent,layout,degree,budget=budget,max_points=256,independent=True)
    assert a.description==b.description
    if u==2:
        assert any(n.valuation==1 for n in a.plan.nodes)
        assert len({n.precision_bits for n in a.plan.nodes})==2
    for k in [0,1,7,14]:
        a=Recovery(parent,layout,degree,budget=budget,max_points=256)
        b=Recovery(parent,layout,degree,budget=budget,max_points=256,independent=True)
        for t,z,p in a.points():
            from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
            ring=ExtensionRing(p,parent.defining_polynomial)
            x=ring.add(ring.elem([t]),ring.mul(ring.elem([8]),z));y=ring.one
            for _ in range(k):y=ring.mul(y,x)
            a.add(t,z,p,y);b.add(t,z,p,y)
        assert a.finish()==b.finish()==((int(k==0),)+(0,)*4,)
