"""Reproducible bounded benchmark; illustrative, not an asymptotic claim."""
from time import perf_counter
from veritas.core.cnf import CNF
from veritas.solvers.weighted_dag import make_weighted_dag_certificate, check_weighted_dag_certificate


def main():
    # 12 disconnected constraints and two unused variables: independent factors.
    cnf=CNF.from_lists(26,[[2*i+1,2*i+2] for i in range(12)])
    weights={str(i):['1/3','2/3'] for i in range(1,27)}
    t=perf_counter();result=make_weighted_dag_certificate(cnf,weights)
    build_ms=round(1000*(perf_counter()-t),3)
    t=perf_counter();ok,why,count,nodes=check_weighted_dag_certificate(cnf,weights,result.certificate)
    verify_ms=round(1000*(perf_counter()-t),3)
    assert ok and result.count==count,why
    print({'status':result.status,'count':count,'nodes':nodes,'cache_hits':result.cache_hits,
           'build_ms':build_ms,'verify_ms':verify_ms,
           'note':'Structure-specific measurement; not an ETH subexponential benchmark'})


if __name__=='__main__':main()
