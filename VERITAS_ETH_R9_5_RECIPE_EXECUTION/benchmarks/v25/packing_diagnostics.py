"""Reproducible diagnostic: no complexity or speedup claim."""
import json,random,time
from veritas.research.eth_packing.packing import construct_packing
from veritas.research.eth_packing.checker import check_packing


def main():
    rng=random.Random(2500); rows=[]
    for n in (8,16,32,64):
        edges=[[rng.randrange(n),rng.randrange(n)] for _ in range(3*n)]
        start=time.perf_counter(); cert=construct_packing(edges,a=2,r=4)
        elapsed=time.perf_counter()-start
        report=check_packing(cert)
        rows.append({'vertices':n,'edges':len(edges),'packets':report['packet_count'],
                     'bound_met':report['all_bounds_satisfied'],'wall_seconds':round(elapsed,5)})
    print(json.dumps(rows,indent=2))

if __name__=='__main__':main()
