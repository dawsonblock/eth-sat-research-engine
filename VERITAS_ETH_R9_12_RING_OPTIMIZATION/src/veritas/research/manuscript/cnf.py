"""Implicit equality-tree encoding from subsec:sharp-fixed-density.

There are no mathematical input-size caps. Operational allowances are shared
with the contraction executor and stop the calculation without a partial count.
"""
from dataclasses import dataclass
from .parameters import natural,Schedule
from .resources import Budget,Limits,ResourceLimit
from .model import ClauseTensor,EqualityTensor,Vertex,Network
from .executor import contract
from .sparse_query import common_zeros


@dataclass(frozen=True)
class Formula:
    n: int
    clauses: tuple[tuple[int,...],...]

    def __post_init__(self):
        natural(self.n,'declared variable count')
        if type(self.clauses) is not tuple or any(type(c) is not tuple for c in self.clauses):
            raise ValueError('immutable clause lists required')
        for clause in self.clauses:
            if any(type(x) is not int or x==0 or abs(x)>self.n for x in clause):
                raise ValueError('literal outside declared variables')

    def normalize(self,budget):
        clauses=set()
        for clause in self.clauses:
            budget.tick(len(clause)+1)
            terms=set(clause)
            if any(-x in terms for x in terms):continue
            if not terms:return Formula(self.n,((),))
            clauses.add(tuple(sorted(terms,key=lambda x:(abs(x),x))))
        return Formula(self.n,tuple(sorted(clauses)))


def parse_dimacs(text,budget=None):
    budget=Budget() if budget is None else budget
    header=None;clauses=[];current=[]
    budget.items(len(text),'DIMACS input characters')
    for line in text.splitlines():
        line=line.strip()
        if not line or line.startswith('c'):continue
        tokens=line.split();budget.tick(len(tokens))
        if tokens[0]=='p':
            if header is not None or len(tokens)!=4 or tokens[1]!='cnf':raise ValueError('invalid DIMACS header')
            n,m=map(int,tokens[2:]);natural(n,'variables');natural(m,'clauses')
            header=(n,m);continue
        if header is None:raise ValueError('DIMACS header must precede clauses')
        for token in tokens:
            literal=int(token)
            if literal:
                if abs(literal)>header[0]:raise ValueError('literal outside DIMACS variable range')
                current.append(literal)
            else:
                clauses.append(tuple(current));current=[]
                if len(clauses)>header[1]:raise ValueError('too many DIMACS clauses')
    if header is None or current or len(clauses)!=header[1]:raise ValueError('incomplete DIMACS formula')
    return Formula(header[0],tuple(clauses))


@dataclass(frozen=True)
class Encoding:
    network: Network
    unused: int
    s: int
    size_constant: int
    precision: int


def encode(formula,budget=None):
    budget=Budget() if budget is None else budget
    formula=formula.normalize(budget)
    if () in formula.clauses:raise ValueError('empty clause has immediate zero count')
    p=formula.n+1;ports=[];tensors=[];occurrences={};edges=[]
    def vertex(tensor):
        result=len(tensors);tensors.append(tensor);ports.append([]);return result
    def connect(left,right):
        budget.tick();edge=len(edges);edges.append((left,right));ports[left].append(2*edge);ports[right].append(2*edge+1)
    for clause in formula.clauses:
        v=vertex(ClauseTensor(tuple(x>0 for x in clause),p))
        for literal in clause:occurrences.setdefault(abs(literal),[]).append(v)
    # Connect in clause-port order, independent of the order variables occur.
    endpoints={}
    for variable,clause_vertices in sorted(occurrences.items()):
        d=len(clause_vertices)
        if d<=2:
            eq=vertex(EqualityTensor(d,p))
            for cv in clause_vertices:endpoints[(cv,variable)]=eq
        else:
            chain=[vertex(EqualityTensor(3,p)) for _ in range(d-2)]
            for cv in clause_vertices[:2]:endpoints[(cv,variable)]=chain[0]
            for j,cv in enumerate(clause_vertices[2:-2],1):endpoints[(cv,variable)]=chain[j]
            if d==3:
                endpoints[(clause_vertices[2],variable)]=chain[0]
            else:
                for cv in clause_vertices[-2:]:endpoints[(cv,variable)]=chain[-1]
            for left,right in zip(chain,chain[1:]):connect(left,right)
    for cv,clause in enumerate(formula.clauses):
        for literal in clause:connect(cv,endpoints[(cv,abs(literal))])
    budget.items(2*len(edges)+len(tensors),'CNF network description')
    rows=tuple(Vertex('row',j,tuple(ps),t) for j,(ps,t) in enumerate(zip(ports,tensors)))
    columns=tuple(Vertex('column',j,(2*j,2*j+1),EqualityTensor(2,p)) for j in range(len(edges)))
    k=max(map(len,formula.clauses),default=0)
    return Encoding(Network(2*len(edges),rows+columns),formula.n-len(occurrences),
                    max(2,formula.n+len(formula.clauses)),max(2,4*k),p)


def direct_count(formula,budget):
    budget.bits(formula.n+1,'model count')
    total=0
    for assignment in range(1 << formula.n):
        budget.tick()
        satisfied=True
        for clause in formula.clauses:
            budget.tick(len(clause))
            if not any(bool((assignment>>(abs(x)-1))&1)==(x>0) for x in clause):
                satisfied=False;break
        total+=satisfied
    return total


def count_fixed_density(formula,*,limits=Limits(),budget=None,event_sink=None):
    budget=Budget(limits) if budget is None else budget
    try:
        formula=formula.normalize(budget);budget.bits(formula.n+1,'count modulus')
        if not formula.clauses or () in formula.clauses:
            count=0 if formula.clauses else 1 << formula.n
            return dict(status='PASS_EXACT_COUNT',count=count,route='TRIVIAL_CNF',ledger=budget.report(),source_qualified=False)
        encoded=encode(formula,budget)
        if type(encoded.precision) is not int or encoded.precision<formula.n+1:
            raise ArithmeticError('count residue modulo 2^P requires P >= n+1 for unique recovery')
        if encoded.network.maximum_degree>Schedule(encoded.s).delta:
            count=direct_count(formula,budget);route='BOUNDED_DEGREE_EXCEPTION'
        else:
            receipt=contract(encoded.network,s=encoded.s,precision=encoded.precision,
                size_constant=encoded.size_constant,budget=budget,event_sink=event_sink)
            if receipt['status']=='INCONCLUSIVE_RESOURCE_LIMIT':return receipt
            count=(receipt['result'][0][0] << encoded.unused)%(1 << encoded.precision)
            route=receipt['route']
        if count>1 << formula.n:raise ArithmeticError('exact count outside assignment range')
        return dict(status='PASS_EXACT_COUNT',count=count,route=route,encoding='CLAUSE_EQUALITY_TREE_SUBDIVISION',
                    ledger=budget.report(),source_qualified=False,complexity_proven=False,
                    fixed_density_bound_assumed=True)
    except ResourceLimit as exc:
        return dict(status='INCONCLUSIVE_RESOURCE_LIMIT',reason=str(exc),ledger=budget.report(),source_qualified=False)


def clause_violation_polynomial(clause):
    """Violation monomials over F2: prod_{pos} (1+x_v) * prod_{neg} x_u."""
    base = frozenset(-x - 1 for x in clause if x < 0)
    positives = sorted(x - 1 for x in clause if x > 0)
    monomials = [base]
    for v in positives:
        monomials += [m | frozenset({v}) for m in monomials]
    return monomials


def count(formula, *, limits=Limits(), budget=None, event_sink=None):
    """Original ordered-list reference dispatcher, unchanged by optimizations."""
    return _count(formula,limits=limits,budget=budget,event_sink=event_sink)


def _count(formula, *, limits=Limits(), budget=None, event_sink=None, sparse_counter=None):
    """Arbitrary-density #SAT via quantitative-reduction's sparse branch.

    Normalize on the original n variables; trivial cases; bounded sizes
    (n<20) by exhaustive search; otherwise lem:sparsify with
    sigma=1/ceil(sqrt(lambda)), lambda=ceil(log2 n), then per-leaf
    sparse-checks + greedy-hashes + lem:tensor-sparse-query. This is the
    arbitrary-density branch only; the fixed-density branch is
    count_fixed_density. At paper scales the greedy candidate enumeration
    exceeds the configured practical allowance and the result is
    INCONCLUSIVE; the paper-scale expander/active recursion path is not
    validated by bounded finite checks.
    """
    from .hashes import count_sparse_formula
    if sparse_counter is None:sparse_counter=count_sparse_formula
    from .sparsify import sparsification_leaves

    budget = Budget(limits) if budget is None else budget
    try:
        formula = formula.normalize(budget)
        n = formula.n
        if not formula.clauses or () in formula.clauses:
            if not formula.clauses:
                budget.bits(n + 1, 'trivial clause count')
            total = 0 if formula.clauses else 1 << n
            return dict(status='PASS_EXACT_COUNT', count=total, route='TRIVIAL_CNF',
                        ledger=budget.report(), source_qualified=False)
        if n < 20:
            total = direct_count(formula, budget)
            return dict(status='PASS_EXACT_COUNT', count=total,
                        route='BOUNDED_EXHAUSTIVE_SEARCH', ledger=budget.report(),
                        source_qualified=False, complexity_proven=False)
        lam = max(1, (n - 1).bit_length())  # ceil(log2 n)
        sigma_den = 1  # ceil(sqrt(lam))
        while sigma_den * sigma_den < lam:
            sigma_den += 1
        k_bound = max((len(c) for c in formula.clauses), default=0)
        if k_bound < 2:
            # unit clauses only: each variable forced once; exact answer
            forced = {}
            dead = False
            for c in formula.clauses:
                lit = c[0]
                v, val = abs(lit), lit > 0
                if v in forced and forced[v] != val:
                    dead = True
                    break
                forced[v] = val
            if not dead:
                budget.bits(n - len(forced) + 1, 'unit propagation count')
            total = 0 if dead else 1 << (n - len(forced))
            return dict(status='PASS_EXACT_COUNT', count=total,
                        route='UNIT_CLAUSE_PROPAGATION',
                        ledger=budget.report(), source_qualified=False,
                        complexity_proven=False)
        from .sparsify import occurrence_bound, select_M
        M = select_M(k_bound, 1, sigma_den, budget)
        B = occurrence_bound(k_bound, M)
        total = 0
        leaf_count = 0
        degree_fallback_leaves = degree_fallback_branches = 0
        for leaf in sparsification_leaves(
                [tuple(clause) for clause in formula.clauses], k_bound,
                1, sigma_den, limits=limits, budget=budget):
            leaf_count += 1
            if not leaf:
                total += 1 << n
                continue
            if any(len(c) == 0 for c in leaf):
                continue
            receipt = sparse_counter(
                n, tuple(tuple(sorted(c)) for c in leaf), B, k_bound,
                limits=limits, budget=budget, event_sink=event_sink)
            if receipt['status'] != 'PASS_EXACT_COUNT':
                return receipt
            total += receipt['count']
            if receipt.get('final_query_degree_fallback'):
                budget.tick()
                degree_fallback_leaves += 1
                degree_fallback_branches += receipt['final_query_degree_fallback']['degree_admission_fallback_branches']
            budget.bits(total.bit_length() + 1, 'leaf count accumulator')
        if total > 1 << n:
            raise ArithmeticError('exact count outside assignment range')
        receipt = dict(status='PASS_EXACT_COUNT', count=total,
                       route='SPARSIFY_SPARSE_QUERY', leaves=leaf_count,
                       occurrence_bound=B, ledger=budget.report(),
                       source_qualified=False, complexity_proven=False,
                       arbitrary_density=True)
        if degree_fallback_leaves:
            receipt.update(final_query_degree_fallback_leaves=degree_fallback_leaves,
                final_query_degree_fallback_branches=degree_fallback_branches,
                degree_fallback_summary_scope='FINAL_QUERY_PER_SPARSE_LEAF_EXCLUDES_GREEDY_SCORING_QUERIES')
        return receipt
    except ResourceLimit as exc:
        return dict(status='INCONCLUSIVE_RESOURCE_LIMIT', reason=str(exc),
                    ledger=budget.report(), source_qualified=False)
