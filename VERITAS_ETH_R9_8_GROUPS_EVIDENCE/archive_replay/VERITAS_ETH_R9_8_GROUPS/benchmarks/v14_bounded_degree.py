"""Run comparative representation benchmark; never interpret as ETH speedup."""
import json
from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.bounded_degree import bounded_degree_from_cnf
from veritas.research.minfill_contract import minfill_contract


def main():
    cases={
        'high_incidence_21':CNF.from_lists(2,[[1]]*21+[[-2]]),
        'short_chain':CNF.from_lists(3,[[1,2],[-2,3]]),
        'isolated_source':CNF.from_lists(5,[[1,2],[2,-3]]),
    }
    rows=[]
    for name,cnf in cases.items():
        try:
            baseline=from_cnf(cnf,max_degree=15)
            original_max=max(map(lambda f:len(f.ports),baseline.factors),default=0)
        except ValueError:
            original_max=None
        net,stats=bounded_degree_from_cnf(cnf)
        count,cstats=minfill_contract(net,timeout_s=15)
        rows.append(dict(case=name,formula_sha256=cnf.digest(),count=str(count),
                         old_dense_encoder_max_degree=original_max,
                         bounded_degree=stats.maximum_factor_degree,
                         new_wires=net.edges,peak_contract_entries=cstats.peak_intermediate_entries,
                         scope='bounded_exact_reference_not_ETH_recursion'))
    print(json.dumps(rows,indent=2))

if __name__=='__main__':main()
