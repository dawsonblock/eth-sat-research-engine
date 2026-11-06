import json,os,subprocess,sys,time
from pathlib import Path
root=Path('/Users/dawsonblock/MATH SPEED/VERITAS_ETH_R9_9_TWO_LEVEL_CONNECTION')
evidence=root.parent/'VERITAS_ETH_R9_9_TWO_LEVEL_CONNECTION_EVIDENCE/portable'
sys.path.insert(0,str(root/'src'))
from veritas.research.tapered_v4.provenance import source_binding
commands=json.loads((evidence/'commands.json').read_text())
(evidence/'wheels').mkdir(exist_ok=True)
expected = source_binding()['digest']
status = {'schema': 'VERITAS_R99_GENERAL_PACKET_PORTABLE_V1', 'status': 'INCOMPLETE',
          'implementation_source_sha256': expected, 'source_qualified': False,
          'full_container_pytest': 'NOT_RUN', 'hosted_ci': 'NOT_RUN',
          'bit_time_bound_status': 'COMPLEXITY_NOT_ESTABLISHED',
          'peak_space_bound_status': 'COMPLEXITY_NOT_ESTABLISHED', 'commands': []}

def execute(name, command):
    start = time.monotonic()
    before = source_binding()['digest']
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    try:
        result = subprocess.run(command, cwd=root, capture_output=True, text=True,
                                timeout=1200, env=env)
        code, output = result.returncode, result.stdout + result.stderr
    except subprocess.TimeoutExpired as exc:
        code, output = 124, str(exc)
    (evidence / ('portable_' + name + '.log')).write_text(output)
    after = source_binding()['digest']
    rec = {'name': name, 'command': command, 'exit_code': code,
           'seconds': time.monotonic() - start, 'source_before': before,
           'source_after': after}
    status['commands'].append(rec)
    (evidence / 'portable_commands.json').write_text(json.dumps(status['commands'], indent=2) + '\n')
    print(json.dumps({'name': name, 'exit_code': code, 'seconds': round(rec['seconds'], 2)}), flush=True)
    if code or before != expected or after != expected:
        raise ValueError(name + ' failed, timed out, or ran across a source change')

try:
    pass # source already sealed before validation
    for command in commands:
        execute(command['name'], command['command'])
    metadata = subprocess.run(['docker', 'image', 'inspect', '--format', '{{.Id}} {{.Architecture}} {{.Os}}',
                               'veritas-eth:r99-two-level-connection'], capture_output=True, text=True, timeout=60)
    if metadata.returncode:
        raise ValueError('docker image inspection failed')
    versions = {}
    for name, path in (('clean_wheel_python', str(evidence / 'clean_py310/bin/python')),
                       ('host_python', sys.executable)):
        versions[name] = subprocess.check_output([path, '--version'], text=True).strip()
    docker_version = subprocess.check_output(['docker', 'run', '--rm', '--network', 'none', '--cpus', '2',
        '--memory', '1g', '--pids-limit', '256', '--entrypoint', 'python',
        'veritas-eth:r99-two-level-connection', '--version'], text=True).strip()
    status.update(status='PASS', portable_command_count=len(commands),
                  clean_wheel_python=versions['clean_wheel_python'], host_python=versions['host_python'],
                  docker_python=docker_version, docker_image=metadata.stdout.strip(),
                  docker_limits={'network':'none','cpus':2,'memory':'1g','pids':256})
except (ValueError, OSError, subprocess.SubprocessError) as exc:
    status.update(status='FAILED_OR_INCONCLUSIVE', reason=str(exc))
(evidence / 'portable_summary.json').write_text(json.dumps(status, indent=2) + '\n')
print(json.dumps({'status': status['status'], 'commands': len(status['commands']),
                  'reason': status.get('reason')}), flush=True)
sys.exit(0 if status['status'] == 'PASS' else 1)
