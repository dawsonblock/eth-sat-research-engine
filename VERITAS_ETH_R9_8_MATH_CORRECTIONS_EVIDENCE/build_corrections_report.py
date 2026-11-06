"""Aggregate completed evidence; refuse incomplete or failed final gates."""

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET


ROOT = Path('/Users/dawsonblock/MATH SPEED/VERITAS_ETH_R9_8_MATH_REVIEW')
OUT = Path(__file__).resolve().parent


def read(name):
    return json.loads((OUT / name).read_text())


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def suite(name):
    data = ET.parse(OUT / name).getroot().find('testsuite')
    record = {k: int(data.attrib[k]) for k in ('tests', 'failures', 'errors', 'skipped')}
    record['passed'] = record['tests'] - record['failures'] - record['errors'] - record['skipped']
    record['seconds'] = float(data.attrib['time'])
    record['skips'] = [
        {'test': t.attrib['name'], 'reason': t.find('skipped').attrib['message']}
        for t in data.findall('testcase') if t.find('skipped') is not None
    ]
    return record


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


tests = suite('pytest.xml')
focused = suite('corrections_focused.xml')
require(tests['failures'] == tests['errors'] == 0, 'full suite is not passing')
require(focused['failures'] == focused['errors'] == 0, 'focused suite is not passing')
checks, portable = read('checks_commands.json'), read('portable_commands.json')
require(len(checks) == 11 and all(c['exit_code'] == 0 for c in checks), 'incomplete validators')
require(len(portable) == 12 and all(c['exit_code'] == 0 for c in portable), 'incomplete portable checks')
require(git('status', '--porcelain') == '', 'commit the reviewed source before final report')

binding = json.loads((ROOT / 'src/veritas/binding/source.json').read_text())['sha256']
require(binding == (OUT / 'source_seal.log').read_text().strip(), 'source seal mismatch')
r98, lean, math = read('r98.json'), read('lean.json'), read('math_checks.json')
require(r98['source']['digest'] == binding, 'R98 source mismatch')
require(r98['status'] == 'PASS_FINITE_SCALED_PARENT_CHILD_IDENTITY', 'R98 failed')
require(r98['source_qualified'] is False and r98['theorem_mode_enabled'] is False, 'scope escalation')
require(r98['paper_formal_mode_domain_enumerated'] is False, 'formal mode-domain escalation')
require(lean['status'] == 'PASS' and len(lean['results']) == 41, 'Lean gate failed')
require(all(x['axiom_audit']['passed'] for x in lean['results']), 'incomplete axiom audit')
require(lean['universal_python_refinement_proven'] is False, 'unexpected refinement claim')

installed = {}
for platform in ('wheel', 'docker'):
    for check in ('packet_fix', 'math_corrections', 'validate_r98_installed', 'validate_r97_installed'):
        name = platform + '_' + check
        result = json.loads((OUT / (name + '.log')).read_text())
        if 'source_binding' in result:
            require(result['source_binding'] == binding, name + ' source mismatch')
        installed[name] = result

baseline_manifests = {}
for version, count in (('r97', 1051), ('r98', 1068)):
    log = (OUT / ('sealed_' + version + '_manifest.log')).read_text().strip()
    require(log.startswith('PASS: ' + str(count)), 'sealed baseline changed: ' + version)
    baseline_manifests[version] = {'status': 'PASS', 'files': count}

counterexamples = read('counterexamples.json')
require(counterexamples['corrected']['source_binding'] == binding, 'counterexamples use stale source')

report = {
    'schema': 'VERITAS_R98_MATH_CORRECTIONS_REVIEW_V1',
    'status': 'PASS_FINITE_MATHEMATICAL_CORRECTIONS',
    'generated_utc': datetime.now(timezone.utc).isoformat(),
    'development_snapshot_not_new_release': True,
    'branch': git('branch', '--show-current'),
    'commit': git('rev-parse', 'HEAD'),
    'sealed_r98_baseline_commit': git('rev-parse', 'b40e45c'),
    'previous_packet_fix_commit': git('rev-parse', '278ec33'),
    'implementation_source_sha256': binding,
    'paper': r98['paper'],
    'parent_digest': r98['parent_digest'],
    'source_eligible': False,
    'scaled_experiment': True,
    'source_qualified': False,
    'theorem_mode_enabled': False,
    'source_refinement_proven': False,
    'bit_time_bound_status': 'COMPLEXITY_NOT_ESTABLISHED',
    'peak_space_bound_status': 'COMPLEXITY_NOT_ESTABLISHED',
    'packing_precondition_verdict': r98['source_preflight'],
    'packet_load_evidence': r98['actual_packing'],
    'mode_completeness': r98['mode_completeness'],
    'mode_basis_scope': r98['mode_basis_scope'],
    'tuple_completeness': r98['tuple_completeness'],
    'tuple_domain': r98['tuple_domain'],
    'paper_formal_mode_domain_enumerated': False,
    'child_count_per_tuple': r98['child_count_per_tuple'],
    'actual_child_shrink': r98['actual_child_shrink'],
    'actual_child_degree': r98['actual_child_degree'],
    'creation_precision_inheritance': r98['creation_precision_inheritance'],
    'per_point_independent_oracle_status': r98['per_point_independent_oracle_status'],
    'hermite_coefficient_precision': r98['hermite_coefficient_precision'],
    'recursive_depth': r98['recursive_depth'],
    'actual_calls': r98['actual_calls'],
    'exact_result': r98['exact_result'],
    'leaf_only_status': 'PASS_FINITE_SCALED_LEAF',
    'leaf_only_transition_claim': False,
    'pytest': tests,
    'focused_tests': focused,
    'validators': checks,
    'portable_commands': portable,
    'clean_wheel': {'status': 'PASS_TARGETED_INSTALLED_CHECKS', 'python': '3.10.19'},
    'docker': {'status': 'PASS_TARGETED_INSTALLED_CHECKS', 'python': '3.12.14', 'network': 'none', 'memory_limit': '1GiB'},
    'installed_results': installed,
    'full_container_pytest': 'NOT_RUN',
    'hosted_ci': 'NOT_RUN',
    'lean_theorem_axiom_report': {
        'status': lean['status'],
        'modules': len(lean['results']),
        'all_required_axiom_reports_passed': True,
        'allowed_axioms': lean['allowed_lean_axioms'],
        'version': lean['lean_version_output'],
        'scope': 'Existing conditional finite models; no universal Python recursion refinement',
        'complete_report': 'lean.json',
    },
    'bounded_math_checks': math,
    'counterexamples': counterexamples,
    'sealed_baseline_manifests': baseline_manifests,
    'first_attempt': read('attempt_1/ATTEMPT_STATUS.json'),
    'selected_multimode_test': {
        'defining_polynomial': 25,
        'modes': 2,
        'legal_tuple_count': 66795,
        'selected_tuples_checked': 7,
        'full_point_coverage_claimed': False,
    },
    'source_archive': 'NOT_CREATED_DEVELOPMENT_CORRECTIONS_ONLY',
}
(OUT / 'verification.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')

summary = f'''# R9.8 mathematical corrections: reviewed implementation

The corrections are committed on `{report['branch']}` at `{report['commit']}`.
The source binding is `{binding}`. The sealed R9.7 and R9.8 baselines and all
four pinned manuscript files remain unchanged. This is a development snapshot,
not a newly sealed source release.

## Corrected behavior

- Retain the corrected packet range `0 <= j < H_pad / 2^k`, where k counts
  equal coordinates. Broadened regressions cover a=1,2,3 and the actual six-edge
  layout that the original R9.8 checker rejected.
- Preserve the parent's exact defining polynomial through point modes,
  replay, child tensors and recovery. Valid alternative irreducible
  polynomials no longer fail solely because the generator chose its default.
- Bind child-to-parent adaptation to the recorded parent digest, depth,
  defining polynomial and increased precision. Reject Boolean integer metadata,
  duplicated half-edge identities and noncanonical ordering.
- State tuple coverage over the zero-reduced geometric basis. Exact zero-mode
  elimination is separate from the high-weight divisibility cutoff; neither
  permits truncating the complete retained weighted stream to meet a budget.
- Report current-node numeric preconditions separately from actual packing and
  descendant admission. Per-side load bounds are sufficient for shrinkage,
  not necessary conditions for every individually small child.
- Return `PASS_FINITE_SCALED_LEAF` when no parent-to-child transition ran.
  Edge-free networks still evaluate their inherited scalar tensors.
- Preserve the existing source resource-limit refusal in mode replay, while
  rejecting missing or null defining-polynomial metadata.

The source precision formula is unchanged. The proof notes explain canonical
creation-coordinate lifting, coefficientwise Hermite precision and the
conditional group factorization. They do not claim a universal executable proof.
See [the derivations](../VERITAS_ETH_R9_8_MATH_REVIEW/docs/R98_MATHEMATICAL_CORRECTIONS.md).

## Verification

- Full suite: **{tests['passed']} passed, {tests['skipped']} optional pybind skips**,
  zero failures/errors. Focused corrections and resource regression: **{focused['passed']} passed**.
- All **11** standalone validators passed, including the 41-module Lean gate,
  R98 parent-child checks and inherited R94–R97 evidence generation/replay.
  Every required Lean axiom record passed; allowed axioms are Classical.choice,
  Quot.sound and propext. These remain conditional finite-model theorems.
- Fresh installed-wheel checks passed on Python 3.10.19; corresponding Docker
  checks passed on Python 3.12.14, with network disabled and a 1 GiB limit.
  These are targeted installed checks, not the entire suite inside Docker.
- The real two-level scaled singleton fixture recovered `7 mod 32`, with
  {r98['actual_calls']:,} actual calls. Nonshrinking children are recorded as
  `{r98['actual_child_shrink']}`. The cross-group point validator covers the
  complete retained weighted stream and all 64 children per tuple.
- Alternative-ring tests cover nonscalar point values, cross modes and full
  one-level Hermite recovery. The separate two-mode test checks seven selected
  coefficient contributions; it does not claim all 66,795 tuples were summed.
- The exact rational audit checked 1,300 shifted Cauchy polynomials, 6,000
  geometric remainders and six independent confluent-Vandermonde recoveries.
  These bounded calculations corroborate the formulas; they are not proofs
  over every admissible parameter.

The first final-suite attempt exposed a resource-error precedence regression
introduced by this correction. Its failed test and original evidence remain in
`attempt_1/`; the fix passed fresh focused, full and portable checks. Final
reports use only the current source digest.

Source qualification and theorem mode remain **false**. Bit-time and peak-space
bounds remain **COMPLEXITY_NOT_ESTABLISHED**. Practical 12–16-edge finite boundary
and elimination results retain their separate qualification. Hosted CI was not run.

Machine-readable evidence: [verification.json](verification.json).
Detailed before/after cases: [counterexamples.json](counterexamples.json).
Artifact integrity uses unsigned SHA-256 hashes in `REVIEW_SHA256.json`; those
hashes do not authenticate provenance or establish mathematical correctness.
'''
(OUT / 'CORRECTIONS_REPORT.md').write_text(summary)

files = []
for path in sorted(OUT.rglob('*')):
    rel = path.relative_to(OUT)
    if not path.is_file() or 'clean_py310' in rel.parts or '__pycache__' in rel.parts:
        continue
    if path.name == 'REVIEW_SHA256.json' or path.suffix in ('.pyc', '.pyo'):
        continue
    files.append({'path': rel.as_posix(), 'sha256': sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size})
(OUT / 'REVIEW_SHA256.json').write_text(json.dumps({
    'schema': 'VERITAS_EXTERNAL_REVIEW_HASHES_V1',
    'signature_status': 'UNSIGNED_HASH_MATCH_ONLY',
    'excluded': ['clean_py310/**', 'attempt_1/clean_py310/**', '__pycache__/**', '*.pyc', '*.pyo', 'REVIEW_SHA256.json'],
    'files': files,
}, indent=2) + '\n')
print(json.dumps({'status': report['status'], 'commit': report['commit'], 'binding': binding,
                  'pytest_passed': tests['passed'], 'pytest_skipped': tests['skipped'],
                  'artifact_files': len(files), 'source_qualified': False}))
