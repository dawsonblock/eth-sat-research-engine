"""Collect completed portable checks without changing the tested source."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess

base = Path(__file__).resolve().parent
commands = json.loads((base / "portable_commands.json").read_text())
assert len(commands) == 16 and all(item["exit_code"] == 0 for item in commands)
binding = (base / "source_seal.log").read_text().strip()
assert len(binding) == 64 and all(char in "0123456789abcdef" for char in binding)
checks = {}
for prefix in ("wheel", "docker"):
    for name in ("packet_fix", "math_corrections", "shrinking_installed",
                 "general_installed", "validate_r98_installed", "validate_r97_installed"):
        key = prefix + "_" + name
        log = base / (key + ".log")
        raw = log.read_bytes()
        data = json.loads(raw)
        assert data["status"].startswith("PASS_")
        if "source_binding" in data:
            assert data["source_binding"] == binding
        checks[key] = {"result": data, "log": log.name,
                       "log_sha256": sha256(raw).hexdigest()}
wheel = base / "wheels/veritas_eth-3.8.2.post98-py3-none-any.whl"
image_command = ["docker", "image", "inspect", "--format",
                 "{{.Id}} {{.Architecture}} {{.Os}}", "veritas-eth:r98-general"]
image = subprocess.run(image_command, capture_output=True, text=True, check=True)
image_id, architecture, operating_system = image.stdout.strip().split()
report = {
    "schema": "VERITAS_R98_GENERAL_PORTABLE_V1",
    "status": "PASS_CLEAN_WHEEL_AND_CONSTRAINED_DOCKER",
    "generated_utc": datetime.now(timezone.utc).isoformat(),
    "implementation_source_sha256": binding,
    "portable_command_count": len(commands),
    "portable_commands": commands,
    "installed_checks": checks,
    "clean_wheel_python": checks["wheel_general_installed"]["result"]["python"],
    "docker_python": checks["docker_general_installed"]["result"]["python"],
    "wheel": {"file": str(wheel), "sha256": sha256(wheel.read_bytes()).hexdigest()},
    "docker": {"tag": "veritas-eth:r98-general", "image_id": image_id,
               "architecture": architecture, "operating_system": operating_system,
               "network": "none", "cpus": 2, "memory": "1g", "pids_limit": 256,
               "metadata_command": image_command, "metadata_exit_code": image.returncode},
    "full_container_pytest": "NOT_RUN",
    "hosted_ci": "NOT_RUN",
    "source_qualified": False,
    "universal_python_refinement": False,
    "bit_time_bound_status": "COMPLEXITY_NOT_ESTABLISHED",
    "peak_space_bound_status": "COMPLEXITY_NOT_ESTABLISHED",
}
(base / "portable_summary.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
print(json.dumps({"status": report["status"], "portable_commands": len(commands),
                  "source_binding": binding, "wheel_python": report["clean_wheel_python"],
                  "docker_python": report["docker_python"], "output": str(base / "portable_summary.json")}))
