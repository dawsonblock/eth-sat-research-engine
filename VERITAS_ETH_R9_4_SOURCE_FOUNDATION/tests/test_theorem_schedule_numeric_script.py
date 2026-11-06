import json
import subprocess
import sys
from pathlib import Path

from veritas.research.appendix_d_schedule import _degree_limit


def test_degree_limit_satisfies_exact_inequality():
    for s in list(range(2, 250)) + [1 << exponent for exponent in range(1, 101)]:
        limit = _degree_limit(s)
        assert (limit - 1) ** 10 < s ** 9 <= limit ** 10


def test_theorem_scale_numeric_path_script():
    script = Path(__file__).resolve().parents[1] / 'scripts' / 'audit_theorem_schedule_numeric.py'
    run = subprocess.run([sys.executable, str(script)], check=True, capture_output=True,
                         text=True, timeout=10)
    result = json.loads(run.stdout)
    assert result['scope'] == 'HYPOTHETICAL_NUMERIC_SIZE_PATH_ONLY'
    assert result['path_status'] == 'FINITE_SCHEDULE_PATH_NUMERICS_CHECKED'
    assert [(c['depth'], c.get('u'), c.get('a')) for c in result['calls']] == [
        (0, 4, 8), (1, 2, 12), (2, 1, 14), (3, None, None)]
    assert all(all(c['numeric_preconditions'].values()) for c in result['calls'][:3])
    assert result['calls'][3]['status'] == 'DIRECT_LEAF_ALLOWED'
    assert result['ends_at_leaf']
    for flag in ('network_descriptions_verified', 'child_identities_verified',
                 'all_branches_verified', 'uniform_theorem_proven'):
        assert result[flag] is False
