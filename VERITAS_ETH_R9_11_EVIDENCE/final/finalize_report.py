from pathlib import Path
import json,re,xml.etree.ElementTree as ET
base=Path(__file__).resolve().parent
root=Path('/Users/dawsonblock/MATH SPEED/VERITAS_ETH_R9_11_COUPLED_RECURSION')
read=lambda path:json.loads(path.read_text())
assert read(base/'full/summary.json')['status']=='PASS'
assert read(base/'portable/summary.json')['status']=='PASS'
assert read(base/'additional_portable_summary.json')['status']=='PASS'
assert read(base/'experiments.json')['status']=='PASS_EXPECTED_OUTCOMES'
assert read(base/'numerical_series.json')['status']=='PASS_EXPECTED_OUTCOMES'
counts={k:sum(int(s.attrib.get(k,0)) for s in ET.parse(base/'full/pytest.xml').getroot()) for k in ['tests','failures','errors','skipped']}
assert counts['failures']==counts['errors']==0
passed=counts['tests']-counts['skipped']
p=root/'RELEASE_REPORT_R911.md';text=p.read_text().replace('> DRAFT: final frozen-source validation is in progress. Measurements are finalized only after all required checks finish.\n\n','')
a=read(base/'replay235/verification.json');b=read(base/'replay242/verification.json')
text=text.replace('| 60.37 |',f"| {a['ledger']['elapsed_seconds']:.2f} |").replace('| 49.56 |',f"| {b['ledger']['elapsed_seconds']:.2f} |")
core=read(base/'coupled_core_100mb/report.json');elapsed=core['ledger']['elapsed_seconds'];points=core['ledger']['point_evaluations']
text=text.replace('it reached 34 point evaluations',f'it reached {points} point evaluations').replace('183.06 seconds',f'{elapsed:.2f} seconds')
rows=[]
for ports in [1,2,4,8,16,32,242]:
 r=read(base/'sweep_shifted'/('b'+str(ports))/'report.json');rows.append((ports,2*(3*ports+1),r['ledger']['point_evaluations'],r['ledger']['work_units'],r.get('reason')))
text=re.sub(r'They completed respectively 111, 85, 35, 51, 54, 44\nand 22 point evaluations across the recursion; these are not completed root grids\.',
 'The partial evaluations below span the recursion; none is a completed root grid.\n\n| Nonconstant row ports | Root sample bound | Completed points, all levels | Charged work units |\n|---|---:|---:|---:|\n'+ '\n'.join(f'| {n} | {samples} | {done} | {work:,} |' for n,samples,done,work,_ in rows),text)
text=text.replace('all 35 clean-wheel/Docker commands passed.',f'all 35 inherited clean-wheel/Docker commands passed. Two additional portable\nreplays of the new connected one-level certificate also passed. The full suite\npassed {passed:,} tests, with {counts["skipped"]} optional pybind tests skipped.')
text=text.replace('The full-suite result is recorded in the accompanying\nevidence summary.','The exact commands and results are recorded in the accompanying\nevidence summary.')
text=text.replace('## Validation and remaining gates','''The largest recorded coupled-core point duplicated its complete local-coefficient
array in the original and folded data. Its 44 port-identified entries also shared
one identical coefficient value. `point_payload_profile.json` records the exact
sizes. Removing this duplication is a concrete next serialization target; it is
not an implemented optimization or a complexity result.

## Validation and remaining gates''')
text=text.replace('Lean model compilation does not establish refinement of the\nPython executable.', '''Lean model compilation does not establish refinement of the
Python executable. The first candidate failed an unchanged legacy budget-exception
test. The correction preserves the enclosing budget's exception type and adds
work/time regression tests; the final source was revalidated from scratch. The
failed-candidate logs remain separately identified in the evidence archive.''')
p.write_text(text)
print('Final report:',passed,'passed,',counts['skipped'],'skipped')
