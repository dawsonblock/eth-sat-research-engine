"""Full formal mode domain from eq:tensor-mode-expansion and -mode-budget.

Coefficients are computed on demand. No coefficient arrays, support polynomials,
or complete Cartesian product are materialized. Zero source modes are included.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Mode:
    packet: int
    tile: int
    exponent: int
    source: int
    target: int

    @property
    def weight(self):return self.exponent+1


class Domain:
    def __init__(self,layout,point,budget):
        self.layout,self.point,self.budget=layout,point,budget
        self.B=1 << (point.coordinate+1)
        self.active_packets=tuple(k for k,p in enumerate(layout.packets)
            if p.pattern[point.coordinate][0]!=p.pattern[point.coordinate][1])
        self.packet_rank={pid:k for k,pid in enumerate(self.active_packets)}
        self.per_weight=len(self.active_packets)*self.B
        self.size=self.per_weight*(point.precision-1)
        budget.items(self.size,'complete exponent vector')

    def weight(self,index):return index//self.per_weight+1

    def mode(self,index):
        if not 0<=index<self.size:raise IndexError('mode index')
        b,channel=divmod(index,self.per_weight)
        packet_index,y0=divmod(channel,self.B);pid=self.active_packets[packet_index]
        pair=self.layout.packets[pid].pattern[self.point.coordinate]
        bit=(y0 >> self.point.coordinate)&1
        return Mode(pid,y0,b,pair[1-bit],pair[bit])

    def packet_modes(self,pid,beta,budget=None):
        if pid not in self.packet_rank:return
        budget=self.budget if budget is None else budget
        start=self.packet_rank[pid]*self.B
        for b in range(self.point.precision-1):
            for y0 in range(self.B):
                budget.tick()
                index=b*self.per_weight+start+y0
                if beta[index]:yield self.mode(index),beta[index]

    def tuples(self):
        """Lexicographic weighted odometer, O(number of modes) live state.

        This enumerates every nonnegative beta with weighted sum < p, including
        zero contributions. Carry/reset implements the full budget constraint;
        it does not impose a binary exponent or row-degree support bound.
        """
        beta=[0]*self.size;used=0
        while True:
            self.budget.tick();self.budget.tuples+=1
            yield tuple(beta)
            for j in range(self.size-1,-1,-1):
                self.budget.tick();weight=self.weight(j)
                if used+weight<self.point.precision:
                    beta[j]+=1;used+=weight
                    break
                used-=beta[j]*weight;beta[j]=0
            else:return

    def count(self):
        """Separate generating-function DP for finite completeness checks."""
        p=self.point.precision;counts=[1]+[0]*(p-1)
        self.budget.items(p,'partition coefficient vector')
        for weight in range(1,p):
            for _ in range(self.per_weight):
                for n in range(weight,p):
                    self.budget.tick();counts[n]+=counts[n-weight]
        return sum(counts)
