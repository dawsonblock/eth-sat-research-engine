"""Construct one actual singleton-packet child for a local mode state.

This builder is used only by the separate finite cycle-transfer experiment.
It retains the original tensor references and creation precisions. The
standalone transfer certificate checker reconstructs its semantics without
calling this module or the ordinary production child constructor.
"""

from veritas.research.tapered_v4.source_recipes import EntryLimits, make_reference
from veritas.research.tapered_v4.source_state import SourceVertex

from .model import ChildGraph, ExponentTuple, canonical, layout_group_count, schedule_record


class TransferChildren:
    def __init__(self, parent, layout, modes, *, budget):
        self.parent, self.layout, self.modes, self.budget = parent, layout, modes, budget
        self.record, self.source = modes.certificate, layout.source
        self.groups = layout_group_count(parent, layout)
        budget.tick(len(parent.vertices) + len(self.source['packets'])
                    + len(self.record['modes']) + self.groups)
        if (layout.parent_digest != parent.content_digest
                or modes.layout_digest != layout.content_digest
                or canonical(self.record['d3_certificate']) != layout.source_bytes):
            raise ValueError('transfer child ancestry mismatch')
        self.modes_digest = modes.content_digest
        self.schedule = canonical(schedule_record(parent, layout))
        self.inherited = [[] for _ in range(self.groups)]
        self.owners = {'row': {}, 'column': {}}
        labels = {'row': self.source['row_labels'], 'column': self.source['column_labels']}
        for vertex in parent.vertices:
            group = labels[vertex.side].get(str(vertex.vertex_id), [0])[0]
            self.inherited[group].append(vertex)
            for position, edge in enumerate(vertex.ports):
                budget.tick()
                self.owners[vertex.side][edge] = (group, vertex.vertex_id, position)
        self.variables = [[] for _ in range(self.groups)]
        for side, kind in (('row', 'Y'), ('column', 'X')):
            for edge in range(parent.edge_count):
                group = self.owners[side][edge][0]
                self.variables[group].append((kind, edge))
                budget.tick()
        self.packet_of_edge, self.packet_ids = {}, [[] for _ in range(self.groups)]
        for pid, packet in enumerate(self.source['packets']):
            if len(packet['occupied_slots']) != 1:
                raise ValueError('transfer children require singleton packets')
            slot, edge = packet['occupied_slots'][0]
            self.packet_of_edge[edge] = (pid, slot)
            for group in sorted({self.owners['row'][edge][0], self.owners['column'][edge][0]}):
                self.packet_ids[group].append(pid)
        self.local = {(y, x): coefficient for y, x, coefficient in self.record['local']}
        self.packet_modes = [[] for _ in self.source['packets']]
        for index, mode in enumerate(self.record['modes']):
            self.packet_modes[mode['packet']].append((index, mode))
        # Before any child is evaluated, inspect the full actual endpoint map.
        if sum(map(len, self.variables)) != 2 * parent.edge_count:
            raise ValueError('transfer half-edge coverage mismatch')
        for variables in self.variables:
            budget.tick(len(variables) + 1)
            if (self.groups * len(variables) > 6 * parent.edge_count
                    or len(variables) >= parent.edge_count):
                raise ValueError('transfer child violates strict group shrink')
            if len(variables) > 4:
                from .model import Refusal
                raise Refusal('INCONCLUSIVE_TRANSFER_NONLEAF',
                              'cycle transfer currently requires every actual child to be a four-edge leaf')

    def child(self, group, beta_values):
        if (type(group) is not int or not 0 <= group < self.groups
                or type(beta_values) is not tuple
                or len(beta_values) != len(self.record['modes'])
                or any(type(x) is not int or x not in (0, 1) for x in beta_values)
                or sum(beta_values) >= self.record['precision']):
            raise ValueError('invalid local transfer state')
        self.budget.tick(len(beta_values) + len(self.variables[group])
                         + len(self.inherited[group]) + len(self.packet_ids[group]) + 1)
        beta = ExponentTuple(self.modes_digest, beta_values)
        variables = self.variables[group]
        edges = {key: index for index, key in enumerate(variables)}
        edge_map = []
        for kind, edge in variables:
            side = 'row' if kind == 'Y' else 'column'
            _, identity, position = self.owners[side][edge]
            edge_map.append((kind, edge, *self.packet_of_edge[edge], identity, position))
        inherited = tuple((v.side, v.vertex_id) for v in self.inherited[group])
        vertices = []
        for vertex in self.inherited[group]:
            kind = 'Y' if vertex.side == 'row' else 'X'
            vertices.append(SourceVertex('row', len(vertices),
                                         tuple(edges[kind, e] for e in vertex.ports), vertex.tensor))
        zero = [[0] * self.record['extension_degree']]
        for number, pid in enumerate(self.packet_ids[group]):
            _, edge = self.source['packets'][pid]['occupied_slots'][0]
            ys = [edge] if ('Y', edge) in edges else []
            xs = [edge] if ('X', edge) in edges else []
            ports = tuple(edges[kind, e] for kind, values in (('Y', ys), ('X', xs)) for e in values)
            local = [[self.local.get((y, x), zero) for x in xs] for y in ys]
            targets, sources = [], []
            for index, mode in self.packet_modes[pid]:
                if mode['target_group'] == group:
                    byrow = dict(mode['rows'])
                    targets.append([beta_values[index], [byrow.get(y, zero) for y in ys]])
                if mode['source_group'] == group:
                    bycol = dict(mode['column_terms'])
                    sources.append([beta_values[index],
                                    [bycol.get(x, 0) % (1 << self.record['precision']) for x in xs]])
            tensor = make_reference(kind='packet', arity=len(ports),
                creation_precision=self.record['precision'], defining_polynomial=self.parent.defining_polynomial,
                jet_length=1, data=[list(range(len(ys))), list(range(len(ys), len(ports))),
                                    local, targets, sources],
                limits=EntryLimits(max_seconds=60, max_precision_bits=self.budget.policy.max_precision))
            vertices.append(SourceVertex('column', number, ports, tensor))
        child = ChildGraph(self.parent.content_digest, self.layout.content_digest, self.modes_digest,
            self.schedule, self.parent.depth + 1, self.record['node'], tuple(self.record['zeta']),
            beta, group, tuple(edge_map), inherited, tuple(self.packet_ids[group]), tuple(vertices),
            self.record['precision'], self.parent.defining_polynomial)
        if (child.edge_count != len(variables) or child.edge_count > 4
                or self.groups * child.edge_count > 6 * self.parent.edge_count):
            raise ValueError('constructed transfer child fails its actual wire bound')
        return child
