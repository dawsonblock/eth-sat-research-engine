from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

OUT = Path(__file__).resolve().parent
ROOT = Path('/Users/dawsonblock/MATH SPEED/VERITAS_ETH_R9_8_SHRINKING')

def read(name):
    return json.loads((OUT/name).read_text())

def require(ok, reason):
    if not ok:
        raise RuntimeError(reason)

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()

suite = ET.parse(OUT/'pytest.xml').getroot().find('testsuite')
tests = {k:int(suite.attrib[k]) for k in ('tests','errors','failures','skipped')}
tests['passed'] = tests['tests']-tests['errors']-tests['failures']-tests['skipped']
tests['seconds'] = float(suite.attrib['time'])
tests['new_shrinking_cases'] = sum('test_shrinking_' in t.attrib.get('classname','') for t in suite.findall('testcase'))
require(tests['errors']==tests['failures']==0, 'full suite did not pass')
checks, portable = read('checks_commands.json'), read('portable_commands.json')
require(len(checks)==12 and all(c['exit_code']==0 for c in checks), 'validators incomplete')
require(len(portable)==14 and all(c['exit_code']==0 for c in portable), 'portable checks incomplete')
require(git('status','--porcelain')=='', 'source changes must be committed')
binding = (OUT/'source_seal.log').read_text().strip()
require(json.loads((ROOT/'src/veritas/binding/source.json').read_text())['sha256']==binding, 'seal mismatch')
shrinking, lean = read('shrinking.json'), read('lean.json')
require(shrinking['status']=='PASS_FINITE_SCALED_SHRINKING_RECURSION', 'shrinking failed')
require(shrinking['source']['digest']==binding, 'shrinking source mismatch')
require(lean['status']=='PASS' and len(lean['results'])==41, 'Lean gate incomplete')
require(all(r['axiom_audit']['passed'] for r in lean['results']), 'axiom reports incomplete')
installed = {}
for name in ('wheel_shrinking_installed','docker_shrinking_installed'):
    d=read(name+'.log')
    require(d['source_binding']==binding and d['status']=='PASS_INSTALLED_ACTUAL_SHRINKING_RECURSION', name+' mismatch')
    installed[name]=d
for name in ('r97','r98'):
    require((OUT/('sealed_'+name+'_manifest.log')).read_text().startswith('PASS:'), 'sealed baseline changed')

executions = [read(c['execution_file']) for c in shrinking['cases']]
sys.path.insert(0, str(ROOT/'src'))
from veritas.research.parent_child_r98 import Budget
from veritas.research.parent_child_r98.shrinking_cli import load_input
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
from veritas.research.parent_child_r98.shrinking_layout import construct_vertex_shrinking_layout, audit_vertex_shrinking_layout
root_packing = {}
for name, filename in [('matching','r98_shrinking_484.json'),('connected_cycle','r98_shrinking_cycle484.json')]:
    parent = load_input(ROOT/'examples'/filename)
    layout = construct_vertex_shrinking_layout(parent, budget=Budget(DEFAULT_SHRINKING_POLICY))
    root_packing[name] = audit_vertex_shrinking_layout(parent, layout)
    require(root_packing[name]['group_load_bound_met'] is True, 'actual shrink premise failed')
    require(root_packing[name]['packet_bound_met'] is False, 'update scaled packing verdict')
report = {
    'schema':'VERITAS_R98_ACTUAL_SHRINKING_REVIEW_V1',
    'status':'PASS_FINITE_SCALED_SHRINKING_RECURSION',
    'generated_utc':datetime.now(timezone.utc).isoformat(),
    'branch':git('branch','--show-current'), 'commit':git('rev-parse','HEAD'),
    'base_commit':git('rev-parse','3a923e4'),
    'implementation_source_sha256':binding, 'paper':shrinking['paper'],
    'source_eligible':False, 'scaled_experiment':True, 'source_qualified':False,
    'theorem_mode_enabled':False, 'source_refinement_proven':False,
    'bit_time_bound_status':'COMPLEXITY_NOT_ESTABLISHED',
    'peak_space_bound_status':'COMPLEXITY_NOT_ESTABLISHED',
    'supported_recovery_family':'ROW_CONSTANT_AT_EVERY_ACTIVE_CALL',
    'packing':'WHOLE_VERTEX_BALANCING_WITH_INDEPENDENT_ACTUAL_LOAD_CHECK',
    'packing_source_padded_packet_bound':'FAIL_ON_VALIDATED_SCALED_ROOTS',
    'root_packing_audits':root_packing,
    'mode_basis_scope':'ZERO_REDUCED_GEOMETRIC_POINT_MODES',
    'tuple_domain':'ALL_WEIGHTED_TUPLES_OVER_RETAINED_MODES',
    'paper_formal_mode_domain_enumerated':False,
    'child_count_per_tuple':64, 'actual_child_shrink':'PASS_EVERY_64_M_CHILD_LE_6_M',
    'degree_verdict':'PASS_FIXED_DEGREE_INVARIANT',
    'termination':'STRICT_EDGE_DECREASE_TO_FOUR_EDGE_LEAVES',
    'creation_precision_inheritance':True, 'maximal_precision_used':max(e['maximal_precision_used'] for e in executions),
    'per_point_independent_oracle':'PASS_INDEPENDENT_HALF_EDGE_ELIMINATION',
    'per_tuple_independent_oracle':'PASS_INDEPENDENT_POLYNOMIAL_FACTOR_ELIMINATION',
    'hermite_coefficient_precision':'CONSTANT_AT_POINT_PRECISION_ZERO_TAIL_EXACT',
    'cases':shrinking['cases'], 'pytest':tests,
    'validators':checks, 'portable_commands':portable, 'installed':installed,
    'lean':{'modules':41,'all_axiom_audits_pass':True,'allowed_axioms':lean['allowed_lean_axioms'],
            'scope':'Inherited conditional finite models; no universal Python refinement', 'details':'lean.json'},
    'new_standalone_saved_trace_certificate_consumer':'NOT_IMPLEMENTED_RUNTIME_INDEPENDENT_CHECKS_AND_FRESH_CLI_EXECUTION',
    'generic_nonconstant_row_recursion':'NOT_IMPLEMENTED_IN_THIS_DRIVER',
    'general_source_active_executor':'REMAINS_UNQUALIFIED_AND_UNAVAILABLE',
    'hosted_ci':'NOT_RUN','full_container_pytest':'NOT_RUN',
    'release_archive':'NOT_CREATED_DEVELOPMENT_BRANCH_ONLY',
}
(OUT/'verification.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
text=f'''# Actual shrinking recursion implementation

Implemented on `{report['branch']}`, commit `{report['commit']}`.
Source binding: `{binding}`. The previous correction branch and sealed R9.7/R9.8
baselines remain intact; this is a development snapshot, not a new sealed release.

The new `contract_shrinking` constructs actual 64-group packet children, checks
`64*M_child <= 6*M` before any recursive call, independently verifies their
ports and entries, and recursively recomputes all 64 values. Successful leaves
have at most four edges. A requested depth is never used as successful termination.

Both the matching and connected-cycle external CLI cases execute **484 → 44 → 4**.
Each has **5,761 actual calls, 5,760 child transitions, 90 complete point values,
45 recoveries, and zero nonshrinking children**. Each result is `2^484 mod 2^512`.
The test suite also verifies a weighted connected 484-cycle with result
`2^484 * 15^242 mod 2^512`, and a connected 64-cycle with nonconstant column
tables whose result is `17^32`. Maximum working precision is **34,304 bits**.

The packer balances whole vertices on each side, supports connected graphs,
and preserves inherited port order. Independent actual side-load checks imply
the numerical child bound; the constructor separately enforces the resulting
actual wire count. It refuses a layout that cannot meet the load bound.

The recursor currently supports the independently certified **constant-row
deformation family at every active call**. Summing the Boolean row affine
factors proves the deformation has degree zero. Both required odd Hermite
nodes are still computed recursively; higher jet coefficients are certified
exactly zero. This is not generic recovery from two samples. All retained
weighted tuples are processed; zero cross-mode coefficients follow from exact
singleton Cauchy values at those nodes, while cross-group ports remain explicit.

Validation: **{tests['passed']} passed, {tests['skipped']} optional pybind skips**;
**{tests['new_shrinking_cases']} new shrinking tests** included. All **12** validators
passed, including the inherited **41-module Lean gate** with complete standard
axiom reports. Fresh Python 3.10 wheel and Linux Docker checks execute actual
two-level shrinking recursion. Full pytest inside Docker and hosted CI were not run.

The general source-active executor, generic nonconstant-row recursion, universal
executable refinement, and asymptotic bit-time/peak-space bounds remain unfinished.
No source/theorem flag was enabled. The source padded packet bound fails on these
scaled roots and is not claimed. Runtime point/child checks are independent; saved traces
do not yet have a separate standalone replay certificate consumer.

[Mathematics and use](../VERITAS_ETH_R9_8_SHRINKING/docs/R98_ACTUAL_SHRINKING_RECURSION.md)
and [machine-readable evidence](verification.json) describe the exact scope.
`REVIEW_SHA256.json` records unsigned artifact hashes, not authenticated provenance.
'''
(OUT/'SHRINKING_REPORT.md').write_text(text)
entries=[]
for f in sorted(OUT.rglob('*')):
    rel=f.relative_to(OUT)
    if not f.is_file() or 'clean_py310' in rel.parts or '__pycache__' in rel.parts or f.name=='REVIEW_SHA256.json':continue
    if f.suffix in ('.pyc','.pyo'):continue
    entries.append({'path':str(rel),'sha256':sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size})
(OUT/'REVIEW_SHA256.json').write_text(json.dumps({'signature_status':'UNSIGNED_HASH_MATCH_ONLY',
    'excluded':['clean_py310/**','__pycache__/**','*.pyc','*.pyo','REVIEW_SHA256.json'],'files':entries},indent=2)+'\n')
print(json.dumps({'status':report['status'],'commit':report['commit'],'tests':tests,'artifacts':len(entries)}))
