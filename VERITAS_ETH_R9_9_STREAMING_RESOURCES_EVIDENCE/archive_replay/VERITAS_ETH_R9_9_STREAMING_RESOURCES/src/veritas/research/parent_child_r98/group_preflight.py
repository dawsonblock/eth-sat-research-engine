"""Independent structural feasibility for fixed finite group counts.

Only incidence, ordered ports, precision and budgets enter this calculation.
It supplies no tensor entries or contraction values. The projection duplicates
the mathematical whole-vertex packing rule, not the production child builder.
Actual children must subsequently match its complete topology inventory.
"""

from dataclasses import dataclass
from math import comb

from .model import ParentCall, Refusal, Semantics, canonical, digest


LEAF_EDGES = 4


@dataclass(frozen=True)
class Topology:
    edges: int
    depth: int
    precision: int
    # Ordered (side, vertex identity, ordered ports), with no tensor references.
    vertices: tuple

    @property
    def content_digest(self):
        return digest((self.edges, self.depth, self.precision, self.vertices))

    @property
    def maximum_degree(self):
        return max((len(v[2]) for v in self.vertices), default=0)


def topology_of(node):
    """A content-bound view of the actual node's incidence, never its value."""
    return Topology(node.edge_count, node.depth, node.precision,
                    tuple((v.side, v.vertex_id, tuple(v.ports)) for v in node.vertices))


@dataclass(frozen=True)
class TopologyExpectation:
    parent_topology: str
    depth: int
    precision: int
    parent_edges: int
    child_topologies: tuple
    child_edges: tuple
    crossing_packets: int
    nonzero_point_tuples: int
    point_terms: int
    required_calls: int

    def record(self):
        return {
            "parent_topology": self.parent_topology,
            "depth": self.depth,
            "precision": self.precision,
            "parent_edges": self.parent_edges,
            "child_topologies": self.child_topologies,
            "child_edges": self.child_edges,
            "crossing_packets": self.crossing_packets,
            "nonzero_point_tuples": self.nonzero_point_tuples,
            "point_terms": self.point_terms,
            "required_calls": self.required_calls,
        }


@dataclass(frozen=True)
class GroupPreflight:
    root_digest: str
    root_topology: str
    groups: int
    general: bool
    required_calls: int
    maximal_precision: int
    maximal_depth: int
    topology_nodes_visited: int
    expectations: tuple

    def report(self):
        return {
            "status": "PASS_FINITE_GROUP_STRUCTURAL_PREFLIGHT",
            "root_digest": self.root_digest,
            "root_topology": self.root_topology,
            "groups": self.groups,
            "execution_family": "GENERAL_COMPLETE_GRID" if self.general else "CONSTANT_DEFORMATION",
            "leaf_threshold": LEAF_EDGES,
            "descendant_packing": "PASS_TO_FOUR_EDGE_LEAVES",
            "actual_children_require_topology_replay": True,
            "required_calls": self.required_calls,
            "call_count_scope": "EXACT_IF_EVERY_ARITHMETIC_ADMISSION_SUCCEEDS",
            "maximal_precision": self.maximal_precision,
            "maximal_depth": self.maximal_depth,
            "topology_nodes_visited": self.topology_nodes_visited,
            "unique_active_topologies": len(self.expectations),
            "nodes": [e.record() for e in self.expectations],
            "tensor_values_checked": False,
            "source_qualified": False,
        }

    def verify_children(self, parent, children, *, budget):
        """Compare every generated child before any recursive invocation."""
        budget.tick()
        if type(children) not in (tuple, list) or len(children) != self.groups:
            raise ValueError("preflight complete child inventory differs")
        signature = topology_of(parent).content_digest
        if signature == self.root_topology and parent.content_digest != self.root_digest:
            raise ValueError("actual root differs from preflight parent binding")
        expected = next((e for e in self.expectations if e.parent_topology == signature), None)
        if expected is None:
            raise ValueError("actual parent topology was not admitted by preflight")
        for group, (child, child_digest, edges) in enumerate(zip(
            children, expected.child_topologies, expected.child_edges
        )):
            budget.tick(len(child.vertices) + child.edge_count + 1)
            if (child.group != group or child.edge_count != edges
                    or topology_of(child).content_digest != child_digest):
                raise ValueError("actual child differs from independent topology projection")
            if self.groups * child.edge_count > 6 * parent.edge_count or child.edge_count >= parent.edge_count:
                raise ValueError("actual child violates preflight decreasing measure")
        return {
            "groups": self.groups,
            "parent_topology": signature,
            "all_actual_child_topologies_match": True,
            "descendants_structurally_packable": True,
        }


def _project(node, groups, budget):
    """Derive children from ordered original occurrences and singleton edges."""
    M = node.edges
    capacity = 3 * M // groups
    if capacity == 0:
        raise Refusal("INCONCLUSIVE_DESCENDANT_PACKING", "nonleaf descendant has zero per-side group capacity")
    labels = {}
    side_loads = {side: [0] * groups for side in ("row", "column")}
    for side in side_loads:
        for _, identity, ports in sorted(
            (v for v in node.vertices if v[0] == side and v[2]),
            key=lambda v: (-len(v[2]), v[1]),
        ):
            budget.tick(groups + len(ports))
            group = next((g for g, load in enumerate(side_loads[side])
                          if load + len(ports) <= capacity), None)
            if group is None:
                raise Refusal("INCONCLUSIVE_DESCENDANT_PACKING", "nonleaf descendant whole vertex exceeds available group capacity")
            labels[side, identity] = group
            side_loads[side][group] += len(ports)
    owners = {side: {} for side in side_loads}
    inherited = [[] for _ in range(groups)]
    for side, identity, ports in node.vertices:
        group = labels.get((side, identity), 0)
        inherited[group].append((side, identity, ports))
        for edge in ports:
            budget.tick()
            if type(edge) is not int or not 0 <= edge < M or edge in owners[side]:
                raise ValueError("preflight duplicate or invalid endpoint")
            owners[side][edge] = group
    if any(set(owners[side]) != set(range(M)) for side in owners):
        raise ValueError("preflight endpoint coverage differs")
    variables = [[] for _ in range(groups)]
    for side, kind in (("row", "Y"), ("column", "X")):
        for edge in range(M):
            variables[owners[side][edge]].append((kind, edge))
            budget.tick()
    mappings = [{key: index for index, key in enumerate(keys)} for keys in variables]
    vertices = []
    for group in range(groups):
        rows = []
        for side, _, ports in inherited[group]:
            kind = "Y" if side == "row" else "X"
            rows.append(("row", len(rows), tuple(mappings[group][kind, edge] for edge in ports)))
        vertices.append(rows)
    # Packet order is sorted (unordered symbol pair, per-pair edge occurrence).
    counts, packets = {}, []
    crossing = 0
    for edge in range(M):
        row, col = owners["row"][edge], owners["column"][edge]
        pair = min(row, col), max(row, col)
        packets.append((pair, counts.get(pair, 0), edge))
        counts[pair] = counts.get(pair, 0) + 1
        crossing += row != col
    column_ids = [0] * groups
    for _, _, edge in sorted(packets):
        row, col = owners["row"][edge], owners["column"][edge]
        for group in sorted({row, col}):
            ports = tuple(mappings[group][kind, edge]
                          for owner, kind in ((row, "Y"), (col, "X")) if owner == group)
            vertices[group].append(("column", column_ids[group], ports))
            column_ids[group] += 1
            budget.tick(len(ports) + 1)
    precision = node.precision + 64 * M  # a=u=1; independent of the group count.
    children = tuple(Topology(len(variables[g]), node.depth + 1, precision,
                              tuple(vertices[g])) for g in range(groups))
    if sum(c.edges for c in children) != 2 * M or any(
        groups * c.edges > 6 * M or c.edges >= M for c in children
    ):
        raise ValueError("projected child half-edge coverage or strict shrink failed")
    return children, crossing


def preflight_group_recursion(parent, *, groups=64, budget, general=False, root_call_charged=False):
    """Check every descendant topology, precision, tuple count and call budget.

    For the general complete grid, every nonzero residue point is a unit and
    W_xx(t+4*zeta) has valuation exactly two. Each crossing singleton therefore
    contributes its weight-one b=0 mode. Higher geometric modes have zero source
    forms. This count is independent of tensor entries; no structural-zero beta
    is omitted. The returned plan certifies feasibility, not arithmetic success.
    """
    if type(parent) is not ParentCall or parent.semantics is not Semantics.FINITE_SCALED_EXPERIMENT:
        raise ValueError("finite ParentCall required for group preflight")
    if type(groups) is not int or not 64 <= groups <= 1024:
        raise ValueError("finite group count must be an integer in 64..1024")
    if type(general) is not bool or type(root_call_charged) is not bool:
        raise TypeError("Boolean preflight options required")
    root = topology_of(parent)
    degree_limit = max(parent.maximum_degree, 4)
    memo, records = {}, []
    evidence_bytes = visited = 0
    maximal_depth, maximal_precision = root.depth, root.precision
    diagnostic = {"groups": groups, "root_digest": parent.content_digest,
                  "execution_family": "GENERAL_COMPLETE_GRID" if general else "CONSTANT_DEFORMATION",
                  "source_qualified": False, "tensor_values_checked": False}

    def visit(node):
        nonlocal evidence_bytes, visited, maximal_depth, maximal_precision
        budget.tick(len(node.vertices) + node.edges + 1)
        visited += 1
        if visited > budget.policy.max_calls:
            raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "prospective topology node cap")
        maximal_depth = max(maximal_depth, node.depth)
        maximal_precision = max(maximal_precision, node.precision)
        for key in ("crossing_packets", "nonzero_point_tuples", "zero_point_tuples",
                    "point_precision", "point_terms", "child_edges", "required_calls"):
            diagnostic.pop(key, None)
        diagnostic.update(failing_depth=node.depth, failing_edges=node.edges,
                          failing_precision=node.precision, failing_topology=node.content_digest)
        if node.depth > budget.policy.max_depth:
            raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "descendant depth exceeds policy")
        if node.edges > budget.policy.max_edges or node.precision > budget.policy.max_precision:
            raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "descendant edge or precision cap")
        if node.maximum_degree > degree_limit:
            raise ValueError("projected descendant degree invariant failed")
        if node.edges <= LEAF_EDGES:
            return 1
        signature = node.content_digest
        if signature in memo:
            return memo[signature]
        if node.precision + 64 * node.edges > budget.policy.max_precision:
            raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "descendant point precision exceeds policy")
        children, crossing = _project(node, groups, budget)
        point_precision = node.precision + 64 * node.edges
        tuples = comb(point_precision + crossing - 1, crossing) if general else 1
        point_terms = 2 * (1 + 3 * node.edges * tuples) if general else 2
        diagnostic.update(crossing_packets=crossing, nonzero_point_tuples=tuples,
                          zero_point_tuples=1, point_precision=point_precision,
                          point_terms=point_terms, child_edges=[c.edges for c in children])
        if tuples > budget.policy.max_tuples:
            raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "complete projected weighted tuple count exceeds policy")
        # Every retained tuple invokes every group, including empty children.
        if 1 + point_terms * groups > budget.policy.max_calls:
            raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "complete projected point calls exceed policy")
        descendants = sum(visit(child) for child in children)
        calls = 1 + point_terms * descendants
        if calls + budget.calls - int(root_call_charged) > budget.policy.max_calls:
            diagnostic.update(failing_depth=node.depth, failing_edges=node.edges,
                              failing_precision=node.precision, failing_topology=signature,
                              required_calls=calls, crossing_packets=crossing,
                              nonzero_point_tuples=tuples, point_terms=point_terms)
            raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "complete descendant calls exceed policy")
        record = TopologyExpectation(signature, node.depth, node.precision, node.edges,
                                     tuple(c.content_digest for c in children),
                                     tuple(c.edges for c in children), crossing, tuples,
                                     point_terms, calls)
        evidence_bytes += len(canonical(record.record()))
        if evidence_bytes > budget.policy.max_certificate_bytes:
            raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "group preflight evidence byte cap")
        records.append(record)
        memo[signature] = calls
        return calls

    try:
        required_calls = visit(root)
        result = GroupPreflight(parent.content_digest, root.content_digest, groups, general,
                                required_calls, maximal_precision, maximal_depth, visited,
                                tuple(records))
        if len(canonical(result.report())) > budget.policy.max_certificate_bytes:
            raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "complete group preflight report byte cap")
        return result
    except Refusal as exc:
        diagnostic.update(status=exc.status, reason=str(exc),
                          descendant_packing="INCOMPLETE_OR_REFUSED",
                          topology_nodes_visited=visited)
        # Diagnostics must obey the same serialization cap as successful plans.
        if len(canonical(diagnostic)) <= budget.policy.max_certificate_bytes:
            exc.report = diagnostic
        else:
            exc.report = {"status": exc.status, "reason": str(exc), "groups": groups}
        raise
