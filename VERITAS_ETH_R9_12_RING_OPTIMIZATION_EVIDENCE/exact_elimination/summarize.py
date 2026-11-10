"""Collect the 96-wire interaction sweep into summary.json."""
import json
from pathlib import Path

here = Path(__file__).resolve().parent
rows = []
for run in sorted(here.glob('offset_*')):
    if not run.is_dir():
        continue
    e = json.loads((run/'elimination.json').read_text())
    r = json.loads((run/'reference.json').read_text())
    rec = json.loads((run/'report.json').read_text()) if (run/'report.json').exists() else None
    rows.append({'offset': int(run.name.split('_')[1]), 'wires': 96, 'status': e['status'],
                 'result_classification': e['result_classification'],
                 'elimination_width': e['elimination_width'],
                 'peak_live_entries': e['route_selection']['ordering']['peak_live_entries'],
                 'predicted_work': e['route_selection']['ordering']['predicted_work'],
                 'elimination_seconds': round(e['ledger']['elapsed_seconds'], 3),
                 'reference_frontier': r['max_frontier_bits'], 'reference_order': r.get('order_source', 'min_degree'),
                 'reference_seconds': round(r['elapsed_seconds'], 3),
                 'matches_independent_integer_reference': e['matches_independent_integer_reference'],
                 'flags_false': all(e[k] is False for k in ('source_qualified', 'theorem_mode_enabled', 'theorem_aligned',
                                                             'source_recursive_bound_evidence', 'subexponential_bound_evidence')),
                 'recursive_route': None if rec is None else {'status': rec['status'], 'reason': rec.get('reason'),
                                                               'work_units': rec['ledger']['work_units']}})
summary = {'runs': rows, 'all_match': all(r['matches_independent_integer_reference'] for r in rows),
           'max_width': max(r['elimination_width'] for r in rows),
           'scope': 'Finite exact elimination results; not evidence for the source recursion or any subexponential bound.'}
(here/'summary.json').write_text(json.dumps(summary, indent=1) + '\n')
print(json.dumps({k: v for k, v in summary.items() if k != 'runs'}))
for r in rows:
    print(r['offset'], r['elimination_width'], r['reference_frontier'], r['reference_order'], r['elimination_seconds'],
          r['matches_independent_integer_reference'], r['recursive_route'])
