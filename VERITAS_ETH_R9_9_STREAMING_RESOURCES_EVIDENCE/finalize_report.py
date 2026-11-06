import json,hashlib,xml.etree.ElementTree as ET
from pathlib import Path
import sys
root=Path('/Users/dawsonblock/MATH SPEED/VERITAS_ETH_R9_9_STREAMING_RESOURCES')
e=root.parent/'VERITAS_ETH_R9_9_STREAMING_RESOURCES_EVIDENCE'
sys.path.insert(0,str(root/'src'))
from veritas.research.tapered_v4.provenance import source_binding
binding=source_binding()['digest']
read=lambda p:json.loads(p.read_text())
full=read(e/'full_v3/summary.json'); inherited=read(e/'inherited_v3/summary.json')
portable=read(e/'portable/portable_summary.json')
assert full['status']==inherited['status']==portable['status']=='PASS'
assert full['source']==inherited['source']==portable['implementation_source_sha256']==binding
run=read(e/'cli22_v2/report.json'); replay=read(e/'cli22_v2/verification.json')
assert run['implementation_source_sha256']==binding
assert run['status']=='PASS_FINITE_STREAMED_TAPERED_RECURSION'
assert replay['status']=='PASS_INDEPENDENT_STREAMED_RECURSION'
assert run['result']==replay['result'] and run['result'][0][0]==31**22
points=read(e/'all_points.json')
assert points['status']=='PASS_ALL_134_INDEPENDENT_CAUCHY_POINT_VALUES'
assert points['implementation_source_sha256']==binding and len(points['points'])==134
suite=ET.parse(e/'full_v3/pytest.xml').getroot()
suites=[suite] if suite.tag=='testsuite' else list(suite.iter('testsuite'))
counts={key:sum(int(s.get(key,0)) for s in suites) for key in ['tests','failures','errors','skipped']}
assert counts['failures']==counts['errors']==0
counts['passed']=counts['tests']-counts['skipped']
lean=read(e/'inherited_v3/lean.json')
assert lean['status']=='PASS' and len(lean['results'])==41
assert all(not r['axiom_audit']['unexpected_axioms'] for r in lean['results'])
summary={'status':'PASS_VALIDATED_FINITE_STREAMING_CORRECTIONS','implementation_source_sha256':binding,
 'pytest':counts,'inherited_commands':len(inherited['commands']),'lean_modules':41,
 'portable_commands':len(portable['commands']),'cli_result':run['result'],
 'cli_requests':run['requests'],'cli_actual_calls':run['ledger']['actual_calls'],
 'cli_cache':run['cache'],'cli_points':run['ledger']['point_evaluations'],
 'cli_evidence_bytes':run['evidence_bytes'],'cli_replay_status':replay['status'],'per_point_oracle_status':points['status'],
 'source_qualified':False,'theorem_mode_enabled':False,
 'general_two_active_level_full_tapered_acceptance':'NOT_RUN_RESOURCE_GAP',
 'bit_time_bound_status':'COMPLEXITY_NOT_ESTABLISHED','peak_space_bound_status':'COMPLEXITY_NOT_ESTABLISHED',
 'hard_host_memory_limit_enforced':False,'full_container_pytest':'NOT_RUN'}
(e/'validation_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
paths=[]
for directory in ['full_v3','inherited_v3','cli22_v2']:
    paths.extend(p for p in (e/directory).rglob('*') if p.is_file())
paths.extend(p for p in (e/'portable').glob('*.json'))
paths.extend(p for p in (e/'portable_final').glob('*.json'))
paths.extend([e/'docker_final_identity.log',e/'all_points.json',e/'all_points.log'])
paths.extend([e/'reassessment242_v2.json',e/'validation_summary.json'])
hashes={str(p.relative_to(e)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(paths))}
(e/'REVIEW_SHA256.json').write_text(json.dumps(hashes,indent=2)+'\n')
report=f'''# R9.9 finite streaming corrections

Implemented in a separate development worktree; the sealed preflight baseline is preserved.
Implementation source SHA-256: `{binding}`.

## Delivered behavior

Lazy geometric mode production can apply independently checked constant-row cancellation
before expansion. Surviving higher orders and higher beta exponents are preserved.
The bounded reduced inventory and support are still materialized, with explicit refusal on overflow.

A bounded exact cache binds full graph and tensor semantics, original creation precision,
evaluation precision, field, depth and remaining schedule. Ancestry provenance alone is
excluded from its key and is still checked on every replay event.

Scalar root recipes can be transported to a sufficiently large verified extension ring.
727 points require degree ten (1,024 residue classes). Non-scalar entries and generated
packet recipes require a separate embedding and are refused by this adapter.

Full tapered recovery consumes one ordered node grid at a time. Independent recursive
replay reconstructs all children, checks shrinking, recomputes leaves, verifies cache
reuse, and uses separate ring arithmetic and divided differences. No production oracle
substitutes an answer. All successful leaves have at most four edges.

## Fresh validation

- Full pytest: {counts['passed']} passed, {counts['skipped']} optional skips, no failures/errors.
- C++ Release build and self-test passed.
- {len(inherited['commands'])} inherited/component validation commands passed, including the
  41-module Lean and axiom gate and the finite 12/14/16-edge matrix.
- {len(portable['commands'])} clean-wheel/Docker commands passed, including new streaming
  checks. Installed wheel and Docker source identities were checked explicitly.
  Stale same-version wheel results were excluded and rerun in a fresh environment.
  Full container pytest and hosted CI were not run.
- External 22-edge nonconstant matching: all 134 complete-grid points evaluated;
  8,577 requests, 135 actual computations, 8,442 cache hits, no evictions.
  Peak cache payload 142,501 bytes; evidence payload 8,293,909 bytes.
  Exact result `31^22 = {31**22}`; independent streamed replay passed.
  All 134 production point values also matched a separate Cauchy closed-form calculation.
  The validation observer asserted equality and never supplied production answers.
- The 242-edge probe obtained the required degree-ten field but refused before expensive
  plan arithmetic under its explicit work cap. The full run was not launched.

The cache payload excludes Python object overhead. Host resource checks are cooperative;
no hard host memory limit was enforced; these measurements are not peak-space or bit-time proofs. Docker
portable checks used no network, two CPUs and a 1 GiB limit.

## Remaining obligations

The combined connected, multi-slot, nonconstant, nonzero exponent-two,
two-active-level full-tapered acceptance case remains unestablished. General large
mode inventories, support counts and interpolation work can still exhaust budgets.
Source-compliant padded packing, source-active nonleaf execution, arbitrary recursive
jet refinement, universal Python correspondence, arbitrary-density SAT reduction,
and bit-time/peak-space bounds remain unfinished. The inherited Lean gate does not
prove these new Python routines. Source qualification and theorem mode remain off.

See [usage and mathematical scope](docs/R99_STREAMING_RESOURCES.md).
Raw evidence is outside this checkout in `../VERITAS_ETH_R9_9_STREAMING_RESOURCES_EVIDENCE`.
`validation_summary.json` and `REVIEW_SHA256.json` bind the final checks; interrupted
preliminary directories are not release evidence.
'''
(root/'RELEASE_REPORT_R99_STREAMING.md').write_text(report)
readme=root/'README.md'
old=readme.read_text()
assert old.startswith('# R9.9 manuscript preflight development')
readme.write_text('''# R9.9 finite streaming resources

This checkout adds lazy mode production with certified early row cancellation,
bounded exact computation reuse, scalar-root extension-field preparation, full-grid
streamed tapered recovery, and independent single-pass recursive replay.

The validated 22-edge nonconstant matching computes all 134 grid points with 135
actual computations and 8,442 cache hits. The general two-level full-tapered acceptance
case and source-qualified algorithm remain unfinished; theorem mode stays disabled.

See the [current release report](RELEASE_REPORT_R99_STREAMING.md) and
[external CLI and remaining scope](docs/R99_STREAMING_RESOURCES.md).

''' + old.replace('# R9.9 manuscript preflight development','## Preserved preflight development',1))
assert source_binding()['digest']==binding
print(json.dumps(summary,indent=2))
