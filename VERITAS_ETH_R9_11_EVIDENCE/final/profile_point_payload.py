from pathlib import Path
import json,hashlib,collections
base=Path(__file__).resolve().parent
records={}
for name in ['coupled_core','coupled_core_100mb']:
 largest=None;size=0
 with (base/name/'events.jsonl').open('rb') as f:
  for line in f:
   if len(line)>size:
    event=json.loads(line)
    if event['kind']=='point':largest=event;size=len(line)
 def encoded(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode()
 local=largest['original']['local']
 counts=collections.Counter(hashlib.sha256(encoded(item[2])).hexdigest() for item in local)
 records[name]={'largest_point_record_bytes':size,
  'original_local_bytes':len(encoded(local)),
  'folded_local_bytes':len(encoded(largest['folded']['local'])),
  'original_and_folded_locals_equal':local==largest['folded']['local'],
  'local_entries_with_distinct_port_identifiers':len(local),
  'distinct_coefficient_values_ignoring_port_identifiers':len(counts),
  'maximum_identical_coefficient_reuse':max(counts.values()),
  'interpretation':'SERIALIZATION_DUPLICATION_ONLY_NO_ARITHMETIC_OR_ASYMPTOTIC_SPEEDUP_ESTABLISHED'}
(base/'point_payload_profile.json').write_text(json.dumps(records,indent=2))
print(json.dumps(records))
