"""Independent integer sum-product oracle for scalar dense matchings only."""
from veritas.research.parent_child_r98.model import decode


def matching_reference(parent):
    owners, scalar = {}, 1
    for vertex in parent.vertices:
        ref = vertex.tensor
        if ref.recipe_kind.split(':')[-1] != 'dense' or len(vertex.ports)>1:
            raise ValueError('oracle requires a dense scalar matching')
        data = decode(ref.description)['data']
        if any(len(x)!=1 or any(x[0][1:]) for x in data):
            raise ValueError('oracle requires scalar entries')
        values = [x[0][0] for x in data]
        if not vertex.ports:
            scalar *= values[0]
        else:
            key = vertex.side, vertex.ports[0]
            if key in owners:
                raise ValueError('duplicate matching endpoint')
            owners[key] = values
    factors = []
    for edge in range(parent.edge_count):
        row, column = owners['row',edge], owners['column',edge]
        factors.append(row[0]*column[0]+row[1]*column[1])
    if len(owners)!=2*parent.edge_count:
        raise ValueError('matching endpoint inventory')
    for factor in factors:
        scalar *= factor
    return {'method':'EXHAUSTIVE_TWO_ASSIGNMENTS_PER_INDEPENDENT_EDGE',
            'edge_factors':factors, 'unreduced_integer':scalar,
            'result':((scalar % (1 << parent.precision),)
                      +(0,)*(parent.defining_polynomial.bit_length()-2),),
            'source_qualified':False}
