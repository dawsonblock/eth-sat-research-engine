"""Apply the tapered functional in every coefficient of O[V]/(V**ell).

Interpolation is in the deformation coordinate, independently of V. No
evaluation or division in V is used; cancellation and precision loss are
checked separately in each extension coordinate of each V coefficient.
"""
from veritas.research.parent_child_r910.recovery import Recovery


class JetRecovery:
    def __init__(self, parent, layout, certificate, *, budget, max_points=256, independent=False):
        self.coordinates = tuple(Recovery(parent, layout, certificate, budget=budget,
            max_points=max_points, independent=independent) for _ in range(parent.jet_length))
        self.description = dict(self.coordinates[0].description)
        if parent.jet_length != 1:
            self.description['jet_length'] = parent.jet_length

    def points(self):
        yield from self.coordinates[0].points()

    def add(self, t, point, precision, value):
        if type(value) not in (tuple, list) or len(value) != len(self.coordinates):
            raise ValueError('complete V coefficient vector required')
        for recovery, coefficient in zip(self.coordinates, value):
            recovery.add(t, point, precision, coefficient)

    def finish(self):
        return tuple(recovery.finish()[0] for recovery in self.coordinates)
