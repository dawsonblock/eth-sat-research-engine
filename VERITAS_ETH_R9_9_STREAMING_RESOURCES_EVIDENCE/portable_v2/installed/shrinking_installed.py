"""Exercise installed, strictly shrinking children without a checkout import."""
import json
import platform
from pathlib import Path

from veritas.research.parent_child_r98.shrinking_cli import load_input
from veritas.research.parent_child_r98 import contract_shrinking
from veritas.research.tapered_v4.provenance import source_binding

parent = load_input(Path(__file__).with_name('shrinking_484.json'))
result = contract_shrinking(parent)
assert result['status'] == 'PASS_FINITE_SCALED_SHRINKING_RECURSION', result
assert result['result'] == ((1 << 484, 0),)
assert result['edge_layers'] == {'0':[484], '1':[0,44], '2':[0,4]}
assert result['ledger']['actual_calls'] == 5761
assert result['ledger']['nonshrinking_children'] == 0
assert len(result['transitions']) == 90
for point in result['transitions']:
    assert point['child_count'] == len(point['child_edges']) == 64
    assert sum(point['child_edges']) == 2*point['parent_edges']
    assert all(64*n <= 6*point['parent_edges'] and n < point['parent_edges']
               for n in point['child_edges'])
assert result['source_qualified'] is False
print(json.dumps({'status':'PASS_INSTALLED_ACTUAL_SHRINKING_RECURSION',
                  'source_binding':source_binding()['digest'],
                  'python':platform.python_version(),
                  'edge_layers':result['edge_layers'],
                  'result':result['result'], 'ledger':result['ledger'],
                  'source_qualified':False}))
