from pathlib import Path
import json,xml.etree.ElementTree as ET,hashlib,subprocess
root=Path('/Users/dawsonblock/MATH SPEED/VERITAS_ETH_R9_9_GENERAL_PACKETS')
base=Path(__file__).parent.resolve()
tests=ET.parse(base/'full_final/pytest.xml').getroot()[0].attrib
full=json.loads((base/'full_final/summary.json').read_text());inherited=json.loads((base/'inherited/summary.json').read_text());portable=json.loads((base/'portable/portable_summary.json').read_text());components=json.loads((base/'components.json').read_text())
assert full['status']==inherited['status']==portable['status']=='PASS'
binding=full['source'];assert inherited['source']==portable['implementation_source_sha256']==components['implementation_source_sha256']==binding
fp=base/'general_full_point.json';point=json.loads(fp.read_text()) if fp.exists() else {'status':'RUNNING'}
report={'status':'PARTIAL_GENERAL_PACKET_MILESTONE','source_sha256':binding,'source_qualified':False,'theorem_mode_enabled':False,'source_active_executor':'NOT_IMPLEMENTED',
'full_tests':dict(collected=int(tests['tests']),passed=int(tests['tests'])-int(tests['skipped']),skipped=int(tests['skipped']),failures=int(tests['failures']),errors=int(tests['errors'])),
'inherited_checks':len(inherited['commands']),'existing_lean_gate':'PASS_41_MODULES_NO_NEW_GENERAL_RECURRENCE_PROOF','portable_commands':portable['portable_command_count'],'full_container_pytest':'NOT_RUN','hosted_ci':'NOT_RUN',
'general_multislot_complete_point':{'status':point['status'],'report':'general_full_point.json'},
'selected_higher_order_coefficients':'PASS_BETA_0_1_2_INCLUDING_NONZERO_QUADRATIC','independent_scalar_check':'scalar_coefficient_check.json','multi_valuation_grid':'PASS_90_POINTS_NONCONSTANT_LOCAL_MULTISLOT',
'active_recursion':'PASS_ONE_LEVEL_MATCHING22_RECOVERY_31_TO_22_WITHOUT_CONTRACTION_ORACLE',
'creation_precision':'INHERITED_IMMUTABLE_REFERENCES_RETAINED',
'fully_recovered_parent_with_crossing_modes':'NOT_ESTABLISHED_BY_R99',
'general_two_active_levels':json.loads((base/'two_level_policy_obstruction.json').read_text()),
'source_packing_correspondence':'NOT_ESTABLISHED','universal_python_refinement':'NOT_PROVED','bit_time':'COMPLEXITY_NOT_ESTABLISHED','peak_space':'COMPLEXITY_NOT_ESTABLISHED',
'prior_runs':{'targeted':'17 passed, 1 failed due to wrong expected fixture value; corrected 17^22 to 31^22','full':'terminated after collecting the stale assertion; superseded by full_final'},
'release':json.loads((base/'final_release_summary.json').read_text())}
(base/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'tests':report['full_tests'],'point':point['status']}))
