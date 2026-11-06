"""External point and full-grid transfer runs with independent replay."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from veritas.research.bounded_integer_encoding import decode_integer_object
from veritas.research.parent_child_r98.model import canonical
from veritas.research.tapered_v4.provenance import source_binding


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def scalar_cycle_oracle(edges, precision, w):
    """Plain integer 2x2 parent oracle, independent of packet/transfer code."""
    modulus = 1 << precision
    def mul(a, b):
        return tuple(tuple(sum(a[i][k] * b[k][j] for k in (0, 1)) % modulus
                           for j in (0, 1)) for i in (0, 1))
    k = ((1, 1-w), (0, w))
    kt = ((k[0][0], k[1][0]), (k[0][1], k[1][1]))
    factor = mul(mul(mul(kt, ((1, 2), (3, 4))), k), ((1, 2), (3, 5)))
    value = ((1, 0), (0, 1))
    for _ in range(edges // 2):
        value = mul(value, factor)
    return (value[0][0] + value[1][1]) % modulus


def run(output):
    if output.resolve().is_relative_to(ROOT):
        raise ValueError('transfer evidence must be outside the source checkout')
    output.parent.mkdir(parents=True, exist_ok=True)
    binding = source_binding()
    report = {'schema': 'VERITAS_R98_CYCLE_TRANSFER_VALIDATION_V1',
              'status': 'INCOMPLETE', 'source': binding, 'cases': [],
              'source_qualified': False, 'theorem_mode_enabled': False,
              'bit_time_bound_status': 'COMPLEXITY_NOT_ESTABLISHED',
              'peak_space_bound_status': 'COMPLEXITY_NOT_ESTABLISHED'}
    env = dict(os.environ, PYTHONPATH=str(ROOT / 'src'), PYTHONDONTWRITEBYTECODE='1')

    def execute(name, module, input_path, *, groups, layout=None, replay=False, certificate=None):
        output_file = output.parent / (name + '.json')
        certificate = certificate or output.parent / (name + '.certificate.json')
        command = [sys.executable, '-m', 'veritas.research.parent_child_r98.' + module,
                   str(input_path), '--groups', str(groups), '--output', str(output_file),
                   '--certificate', str(certificate), '--max-work', '1000000000',
                   '--max-seconds', '1200', '--max-certificate-bytes', '100000000']
        if layout is not None:
            command += ['--layout-file', str(layout)]
        if replay:
            command.append('--verify')
        done = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, timeout=1800)
        (output.parent / (name + '.log')).write_text(done.stdout + done.stderr)
        require(output_file.exists(), name + ' did not write a report: ' + done.stderr[-1000:])
        data = json.loads(output_file.read_bytes(), object_hook=decode_integer_object)
        report['cases'].append({'name': name, 'command': command, 'exit_code': done.returncode,
            'status': data['status'], 'report': output_file.name,
            'report_sha256': sha256(output_file.read_bytes()).hexdigest(),
            'certificate': certificate.name if certificate.exists() else None,
            'certificate_sha256': sha256(certificate.read_bytes()).hexdigest() if certificate.exists() else None})
        require(done.returncode == 0 and data['status'].startswith('PASS_'),
                name + ' failed: ' + str(data.get('reason')))
        require(not data.get('source_qualified', False) and not data.get('theorem_mode_enabled', False),
                'source qualification escalated')
        return data, certificate

    try:
        point44, cert44 = execute('cycle44-point', 'cycle_transfer_cli',
            ROOT / 'examples/r98_transfer_cycle44.json', groups=64)
        require(point44['retained_modes'] == 22 and point44['ledger']['actual_calls'] == 131,
                '44-edge actual mode/child count')
        require(point44['result'][0][0] == scalar_cycle_oracle(44, 2944, -84)
                and point44['result'][0][1] == 0, '44-edge scalar cycle oracle')
        replay44, _ = execute('cycle44-point-replay', 'cycle_transfer_cli',
            ROOT / 'examples/r98_transfer_cycle44.json', groups=64, replay=True, certificate=cert44)
        require(replay44['result'] == point44['result'], '44-edge fresh-process replay')

        full, full_cert = execute('mode-cycle22-recovery', 'cycle_recovery_cli',
            ROOT / 'examples/r98_transfer_mode_cycle22.json', groups=64,
            layout=ROOT / 'examples/r98_transfer_mode_cycle22_layout.json')
        require(full['result'] == [[17**22, 0, 0, 0, 0, 0, 0]], 'full recovered matching result')
        require(full['ledger']['point_evaluations'] == 134 and full['ledger']['actual_calls'] == 9899,
                'full point grid or actual local child calls missing')
        replay, _ = execute('mode-cycle22-recovery-replay', 'cycle_recovery_cli',
            ROOT / 'examples/r98_transfer_mode_cycle22.json', groups=64,
            layout=ROOT / 'examples/r98_transfer_mode_cycle22_layout.json', replay=True, certificate=full_cert)
        require(replay['result'] == full['result'] and replay['replayed_points'] == 134,
                'full independently replayed recovery')

        n = 242
        large = output.parent / 'cycle484-nonconstant-input.json'
        large.write_bytes(canonical({'root_s': 1024, 'precision': 512, 'extension_degree': 2,
            'edges': 484, 'vertices': [
                {'side':'row','ports':[2*i,2*i+1],'table':[1,3,2,4]} for i in range(n)] + [
                {'side':'column','ports':[2*i+1,2*((i+1)%n)],'table':[1,3,2,5]} for i in range(n)]}))
        point484, cert484 = execute('cycle484-nonconstant-point-final', 'cycle_transfer_cli', large, groups=512)
        require(point484['retained_modes'] == 242 and point484['ledger']['actual_calls'] == 1239,
                '484-edge mode/actual child-state count')
        require(point484['ledger']['point_evaluations'] == 1 and point484['ledger']['transitions'] == 1238,
                '484-edge point/representative transition ledger')
        require(point484['result'][0][0] == scalar_cycle_oracle(484, 31488, -84)
                and point484['result'][0][1] == 0, '484-edge independent scalar matrix oracle')
        replay484, _ = execute('cycle484-nonconstant-point-replay', 'cycle_transfer_cli', large,
                               groups=512, replay=True, certificate=cert484)
        require(replay484['result'] == point484['result'], '484-edge fresh-process replay')
        require(source_binding() == binding, 'implementation source changed during validation')
        report.update(status='PASS_FINITE_CYCLE_TRANSFER_VALIDATION', point44_modes=22,
            full_mode_cycle22_points=134, full_mode_cycle22_actual_calls=9899,
            full_mode_cycle22_result='17^22', connected484_modes=242,
            connected484_actual_calls=1239, connected484_scope='ONE_POINT_ONLY',
            full_connected_cycle_recovered=False, active_source_recursion=False)
    except (ValueError, KeyError, TypeError, OSError, subprocess.TimeoutExpired) as exc:
        report.update(status='FAILED_OR_INCONCLUSIVE', reason=str(exc))
    output.write_bytes(canonical(report))
    print(json.dumps({'status': report['status'], 'cases': len(report['cases']),
                      'reason': report.get('reason'), 'output': str(output)}))
    return int(not report['status'].startswith('PASS_'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    raise SystemExit(run(parser.parse_args().output))
