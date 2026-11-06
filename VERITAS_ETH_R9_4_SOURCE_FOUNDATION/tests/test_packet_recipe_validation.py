from dataclasses import replace

import pytest

from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.jets import JetRing
from veritas.research.eth_recursive_contraction_v39.described_network import (
    CreatedPacketTensor, DescribedVertex,
)
from veritas.research.eth_recursive_contraction_v39.lazy_children import PacketTensorEntry, _Budget


def valid_recipe():
    return PacketTensorEntry(0, (3, 4), (('Y', 10), ('X', 20)),
                             ((10, ((20, ((7,),)),)),),
                             ((0, 1, ((10, ((1,),)),)),),
                             ((1, 0, ((20, 1),)),))


@pytest.mark.parametrize('change', [
    {'packet_id': True},
    {'ports': (3, 3)},
    {'variables': (('Y', 10),)},
    {'variables': (('Y', 10), ('Z', 20))},
    {'variables': (('Y', 10), ('Y', 10))},
    {'rows': ()},
    {'rows': ((10, ((99, ((1,),)),)),)},
    {'rows': ((10, ((20, [[1]]),)),)},
    {'target_modes': ((0, -1, ()),)},
    {'target_modes': ((0, True, ()),)},
    {'target_modes': ((0, 1, ((99, ((1,),)),)),)},
    {'target_modes': ((0, 1, ((10, ((1,),)), (10, ((2,),)))),)},
    {'source_modes': ((1, -1, ()),)},
    {'source_modes': ((1, 1, ((99, 1),)),)},
    {'source_modes': ((1, 1, ((20, True),)),)},
])
def test_invalid_packet_recipes_are_rejected_at_creation(change):
    with pytest.raises(ValueError):
        replace(valid_recipe(), **change)


def test_packet_input_rejects_boolean_indices():
    ring = JetRing(ExtensionRing(3, 0b11), 1)
    with pytest.raises(ValueError, match='Boolean index'):
        valid_recipe().evaluate((True, 1), ring, _Budget(100, 5))


def test_inherited_packet_tensor_supports_positionally_reindexed_ports():
    recipe = valid_recipe()
    tensor = CreatedPacketTensor(recipe, 3, 0b11, 1)
    # New child edge IDs differ from recipe IDs; port order binds the bits.
    vertex = DescribedVertex('column', 'reindexed', (0, 1), tensor)
    ring = JetRing(ExtensionRing(3, 0b11), 1)
    assert vertex.tensor.evaluate((0, 1), ring, _Budget(100, 5)) == ring.elem([[7]])
