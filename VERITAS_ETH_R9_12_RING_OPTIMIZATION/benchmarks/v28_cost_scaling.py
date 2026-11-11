"""Record dense Cauchy operation growth vs wire count (finite measurement only)."""
from __future__ import annotations

import json
from pathlib import Path
from random import Random

from veritas.research.dense_cauchy_testbed import experiment


def main() -> None:
    rows = []
    for wires in (8, 10, 12):
        rng = Random(9120 + wires)
        a = [rng.randrange(2) for _ in range(1 << wires)]
        b = [rng.randrange(2) for _ in range(1 << wires)]
        result = experiment(a, b, wires, precision=2)
        ops = result['counted_scalar_additions'] + result['counted_scalar_multiplications']
        rows.append({'wires': wires, 'dense_cauchy_ops': ops, 'modes_retained': result['retained_structural_modes']})
    for i in range(1, len(rows)):
        prev, cur = rows[i - 1], rows[i]
        ratio = cur['dense_cauchy_ops'] / max(prev['dense_cauchy_ops'], 1)
        cur['ops_ratio_vs_previous'] = round(ratio, 4)
        cur['log2_growth_per_wire'] = round(
            (cur['dense_cauchy_ops'].bit_length() - prev['dense_cauchy_ops'].bit_length())
            / (cur['wires'] - prev['wires']),
            4,
        )
    report = {
        'schema': 'VERITAS_COST_SCALING_V1',
        'warning': 'Two-point ratios do not prove asymptotic complexity.',
        'measurements': rows,
    }
    path = Path(__file__).resolve().parents[1] / 'validation' / 'cost_scaling_v28.json'
    path.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
