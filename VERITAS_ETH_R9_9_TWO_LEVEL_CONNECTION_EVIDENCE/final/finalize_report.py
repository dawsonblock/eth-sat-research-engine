import json, hashlib, xml.etree.ElementTree as ET
from pathlib import Path
r=Path(__file__).resolve().parent
source=r.parents[1]/'VERITAS_ETH_R9_9_TWO_LEVEL_CONNECTION'
# Evidence is external; only the release report is written in the checkout.
source=Path('/Users/dawsonblock/MATH SPEED/VERITAS_ETH_R9_9_TWO_LEVEL_CONNECTION')
def read(p): return json.loads((r/p).read_text())
checks={k:read(f'{k}/summary.json') for k in ['full','inherited','portable']}
assert all(v['status']=='PASS' for v in checks.values()),checks
binding=(r/'seal.log').read_text().strip()
assert all(v['source']==binding for v in checks.values())
suites=list(ET.parse(r/'full/pytest.xml').getroot().iter('testsuite'))
counts={k:sum(int(s.get(k,0)) for s in suites) for k in ['tests','failures','errors','skipped']}
assert not counts['failures'] and not counts['errors']
counts['passed']=counts['tests']-counts['skipped']
lean=read('inherited/lean.json');assert lean['status']=='PASS' and len(lean['results'])==41
run=read('executed22/report.json');replay=read('executed22/verification.json')
assert run['status']=='PASS_FINITE_STREAMED_TAPERED_RECURSION'
assert replay['status']=='PASS_INDEPENDENT_STREAMED_RECURSION'
assert run['result']==replay['result'] and run['result'][0][0]==31**22
assert run['implementation_source_sha256']==binding
preview=read('topology/report.json');assert preview['status']=='PASS_FINITE_TOPOLOGY_ONLY'
assert preview['preflight']['streaming_topology_admitted'] and 'result' not in preview
probe=read('bounded_run/report.json');assert probe['status']=='INCONCLUSIVE_RESOURCE_LIMIT' and 'result' not in probe
summary={'schema':'VERITAS_R99_TWO_LEVEL_CONNECTION_VALIDATION_V1','status':'PASS_FINITE_CONNECTION',
'implementation_source_sha256':binding,'pytest':counts,'inherited_commands':len(checks['inherited']['commands']),
'portable_commands':len(checks['portable']['commands']),'lean_modules':len(lean['results']),
'projected_edges':[242,22,2],'topology_status':preview['status'],'numerical_22_status':run['status'],
'independent_replay_status':replay['status'],'actual_calls':run['ledger']['actual_calls'],
'grid_points':run['ledger']['point_evaluations'],'cache_hits':run['cache']['hits'],
'full_two_active_level_numerical_validation':'NOT_RUN_RESOURCE_GAP','resource_probe_status':probe['status'],
'source_qualified':False,'theorem_mode_enabled':False,'bit_time_bound_status':'COMPLEXITY_NOT_ESTABLISHED',
'peak_space_bound_status':'COMPLEXITY_NOT_ESTABLISHED','full_container_pytest':'NOT_RUN','hosted_ci':'NOT_RUN',
'excluded_preliminary_evidence':'Parent evidence directory predates final digest correction; final/portable/initial_install_failure.json records rejected install attempt.'}
(r/'validation_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
text=f'''# R9.9 two-level streaming layout connection

Implementation source SHA-256: `{binding}`.
The sealed streaming-resources baseline is preserved in its separate checkout.

## Delivered behavior

The external streaming CLI accepts `--layout-file`, authenticates its original
parent digest, enlarges the scalar root field when necessary, and independently
re-audits the layout bound to the prepared parent. It checks descendant topology
using the same singleton first-fit strategy supplied to recursive execution.
Original preflight provenance is retained and the adapted report is rehashed.
`--preflight-only` returns no contraction result and starts no tensor arithmetic.
Preflight work is charged to the subsequent execution budget.

Legacy estimates for recomputing every child and retaining every grid are
preserved as advisories for the cached streaming executor. Other structural
and precision blockers remain admission failures. Runtime feasibility is not
inferred from topology admission; execution still enforces its resource caps.

## Fresh results

- Projected two-level matching topology: **242 -> 22 -> 2**, with both active
  levels packable. Degree ten supplies 1,024 residues for the 727-point root grid.
- Actual one-active-level 22-edge matching through the layout-file CLI:
  all 134 grid points, 135 actual computations, 8,442 cache hits, and
  8,576 child transitions. Result `31^22`; independent streamed replay passed.
- The connected 242-edge executor probe returned `INCONCLUSIVE_RESOURCE_LIMIT`
  at Hermite-plan budget admission, with one call and zero evaluated points.
  Its conservative work charge was 33,865,497 against a 1,000,000 cap.
  This is a policy refusal, not measured hardware exhaustion.
- Full pytest: **{counts['passed']} passed, {counts['skipped']} skipped**; no failures or errors.
  C++ Release build and self-test passed.
- **{len(checks['inherited']['commands'])} inherited commands** passed, including the 41-module Lean/axiom gate.
- **{len(checks['portable']['commands'])} clean-wheel/Docker commands** passed, including installed connection
  tests and explicit installed source identity checks. An initial installation
  was rejected by the identity check and rerun with an explicit wheel reinstall.
  Full container pytest and hosted CI were not run.

## Remaining scope

The 242-edge input is a matching. The successful topology projection is not an
executed two-active-level numerical validation and is not the combined general
connected, multi-slot, nonconstant, exponent-two acceptance case. That full
numerical case remains unestablished. Mode counts, interpolation work and total
recursive work can still exceed budgets. Source packing, source-active execution,
universal executable refinement, and bit-time/peak-space proofs remain open.
The inherited Lean gate does not prove the new Python connection. Theorem mode
and source qualification remain disabled.

See [the external CLI](docs/R99_TWO_LEVEL_CONNECTION.md).
Final evidence is external in
`../VERITAS_ETH_R9_9_TWO_LEVEL_CONNECTION_EVIDENCE/final/`.
Earlier preliminary evidence is excluded from these release results.
'''
(source/'RELEASE_REPORT_R99_TWO_LEVEL_CONNECTION.md').write_text(text)
files=['validation_summary.json','full/summary.json','full/pytest.xml','inherited/summary.json','inherited/lean.json','portable/summary.json','topology/report.json','bounded_run/report.json','executed22/report.json','executed22/verification.json','executed22/events.jsonl']
(r/'REVIEW_SHA256.json').write_text(json.dumps({p:hashlib.sha256((r/p).read_bytes()).hexdigest() for p in files},indent=2)+'\n')
print(json.dumps(summary,indent=2))
