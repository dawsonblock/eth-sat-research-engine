from pathlib import Path
import hashlib,json,xml.etree.ElementTree as ET,sys
root=Path('/Users/dawsonblock/MATH SPEED/VERITAS_ETH_R9_9_SUPPORTED_RECURSION')
ev=root.parent/'VERITAS_ETH_R9_9_SUPPORTED_RECURSION_EVIDENCE'
sys.path.insert(0,str(root/'src'))
from veritas.research.parent_child_r98.model import decode,canonical
from veritas.research.bounded_integer_encoding import decode_integer_object
from veritas.research.tapered_v4.provenance import source_binding,manuscript_binding
from veritas.research.paper_verification.source_registry import source_registry
read=lambda p:json.loads(p.read_bytes(),object_hook=decode_integer_object)
recursive=read(ev/'final_v2/recursive_report.json');replay=read(ev/'final_v2/recursive_replay.json')
assert recursive['status']=='PASS_FINITE_SUPPORTED_SHRINKING_RECURSION',recursive
assert replay['status']=='PASS_INDEPENDENT_SUPPORTED_RECURSION',replay
assert recursive['result']==replay['result']==[[17*2**241,0]]
assert recursive['largest_edges_by_depth']=={'0':242,'1':22,'2':2}
assert recursive['ledger']['actual_calls']==56449 and recursive['ledger']['point_evaluations']==792 and recursive['ledger']['tuples']==882
closed=read(ev/'final_v2/closed_form.json');coefficients=read(ev/'final_v2/coefficients.json')
assert closed['point_count']==8 and len(coefficients['coefficients'])==6
assert recursive['nonconstant_active_calls_by_depth']['1']>0 and recursive['crossing_points_by_depth']['1']>0
cross=read(ev/'final_v2/crossing_report.json');cross_replay=read(ev/'final_v2/crossing_replay.json')
assert cross['status']=='PASS_FINITE_SUPPORTED_PACKET_RECOVERY' and cross_replay['status']=='PASS_INDEPENDENT_SUPPORTED_RECOVERY'
assert cross['result']==cross_replay['result']==[[1,0,0,0]]
full=json.loads((ev/'full_v2/summary.json').read_text());inherited=json.loads((ev/'inherited_v2/summary.json').read_text());portable=json.loads((ev/'portable_v2/portable_summary.json').read_text())
assert all(x['status']=='PASS' for x in (full,inherited,portable))
suite=ET.parse(ev/'full_v2/pytest.xml').getroot();suites=list(suite.iter('testsuite'));counts={k:sum(int(s.get(k,0)) for s in suites) for k in ('tests','failures','errors','skipped')}
assert counts['failures']==counts['errors']==0
binding=source_binding()['digest'];assert recursive['implementation_source_sha256']==cross['implementation_source_sha256']==binding
assert manuscript_binding()['pin_matches']
report={'schema':'VERITAS_R99_SUPPORTED_FINAL_AUDIT_V1','status':'PASS_BOUNDED_SUPPORTED_RECURSION_RELEASE','source':binding,'paper':manuscript_binding(),'paper_commit':'4eaee87548250b2682affda7d05d947c05554bae','paper_statement_registry':source_registry(),'source_eligible':False,'scaled_experiment':True,'source_schedule_verdict':'INCONCLUSIVE_SOURCE_SCHEDULE','mode_completeness':'INDEPENDENT_COMPLETE_ORIGINAL_BASIS_AND_EXACT_FOLDING','tuple_completeness':'EXACT_AGGREGATION_WITH_INDEPENDENT_AFFINE_SUPPORT_CHECK','original_weighted_stream_enumerated':False,'child_count_per_supported_tuple':64,'recursive_actual_shrink':'CHECKED_64_M_CHILD_LE_6_M','small_crossing_source_shrink':False,'creation_precision_inheritance':'INDEPENDENT_ENTRY_AND_RECURSIVE_REPLAY','lean_theorems':'41_EXISTING_MODULES_PASS_NO_NEW_GENERAL_REFINEMENT_THEOREM','pytest':counts,'inherited_commands':len(inherited['commands']),'portable_commands':len(portable['commands']),'recursive':{k:v for k,v in recursive.items() if k!='policy'},'recursive_replay':replay,'crossing_recovery':cross,'crossing_replay':cross_replay,'closed_form_root_check':closed,'folded_coefficients':coefficients,'source_qualified':False,'source_executor':'INCONCLUSIVE_SOURCE_REFINEMENT','formal_general_refinement':'NOT_PROVED','bit_time_bound_status':'COMPLEXITY_NOT_ESTABLISHED','peak_space_bound_status':'COMPLEXITY_NOT_ESTABLISHED','general_jet_valued_input':'UNIMPLEMENTED','arbitrary_density_sat_pipeline':'INCOMPLETE','preliminary_evidence':['probe_two_levels.log','probe_two_levels242.log','full/','portable/','final/recursive_replay.json','targeted_v3.log'],'preliminary_notes':'Initial long probes were interrupted. Initial CLI replay rejected timing metadata; fixed with a bounded report reader and an end-to-end CLI test. The first roundtrip test expected tuple/list identity; normalized it. Final validation uses only v2 directories.'}
from veritas.research.parent_child_r98.shrinking_cli import load_input
from veritas.research.parent_child_r98.model import Budget
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
from veritas.research.parent_child_r98.packing import audit_layout,preconditions
from veritas.research.parent_child_r99.cli import load_layout
parent=load_input(root/'examples/r99_nonconstant_matching242.json')
layout=load_layout(parent,root/'examples/r99_nonconstant_matching242_layout.json',Budget(DEFAULT_SHRINKING_POLICY))
report.update(packing_precondition_verdict=preconditions(parent),packet_load_proof=audit_layout(parent,layout),actual_child_degree_verdict='INDEPENDENTLY_RECONSTRUCTED_AND_BOUNDED_AT_EVERY_TRANSITION',per_point_independent_oracle_status={'small_crossing_grid':'90_DIRECT_HALF_EDGE_CHECKS','large_matching_root':'8_INDEPENDENT_CLOSED_FORM_CHECKS','recursive_points':'792_CHILD_REPLAY_CHECKS'},Hermite_coefficient_precision={'complete_small_crossing_grid':[101,149],'recursive_point_precisions':[16000,17408],'recursive_recovery':'DEGREE_CERTIFIED_TAYLOR_AND_INDEPENDENT_LAGRANGE','source_tapered_functional_used_in_recursive_fixture':False},lean_axiom_report={'file':'inherited_v2/lean.json','sha256':hashlib.sha256((ev/'inherited_v2/lean.json').read_bytes()).hexdigest(),'new_general_refinement_theorems':0},clean_wheel_and_docker={'status':portable['status'],'commands':len(portable['commands']),'wheel_python':portable['clean_wheel_python'],'docker_python':portable['docker_python'],'full_container_pytest':'NOT_RUN','hosted_ci':'NOT_RUN'})
(ev/'verification.json').write_bytes(canonical(report))
print('PASS',counts,'calls',recursive['ledger']['actual_calls'])
