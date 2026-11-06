"""Quick reproducible v3.4 test driver (offline capable when dependencies installed)."""
import subprocess,sys
commands=[
    [sys.executable,'-m','pytest','-q','tests/test_v34_child_topology.py','tests/test_v34_bridge.py'],
    [sys.executable,'scripts/validate_v34.py'],
    [sys.executable,'scripts/verify_manifest.py'],
]
for command in commands:
    print('RUN',*command,flush=True)
    subprocess.run(command,check=True)
print('PASS: v3.4 focused checks and release digest checks')
