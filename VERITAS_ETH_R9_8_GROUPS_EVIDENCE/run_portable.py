import json, os, subprocess, sys, time
from pathlib import Path
from hashlib import sha256
from datetime import datetime, timezone
root=Path("/Users/dawsonblock/MATH SPEED/VERITAS_ETH_R9_8_GROUPS")
evidence=root.parent/"VERITAS_ETH_R9_8_GROUPS_EVIDENCE"
prior=root.parent/"VERITAS_ETH_R9_8_GENERAL_EVIDENCE"
sys.path.insert(0,str(root/"src"))
from veritas.research.tapered_v4.provenance import source_binding
binding=source_binding()["digest"]
old=json.loads((prior/"portable_commands.json").read_text())
commands=[]
for row in old:
    cmd=[part.replace("VERITAS_ETH_R9_8_GENERAL","VERITAS_ETH_R9_8_GROUPS").replace("veritas-eth:r98-general","veritas-eth:r98-groups") for part in row["command"]]
    commands.append((row["name"],cmd))
    if row["name"] in ("wheel_general_installed","docker_general_installed"):
        commands.append((row["name"].replace("general_installed","groups_installed"),[part.replace("general_installed.py","groups_installed.py") for part in cmd]))
records=[]
for name,cmd in commands:
    started=time.monotonic()
    with (evidence/(name+".log")).open("w") as log:
        try:
            result=subprocess.run(cmd,cwd=evidence,stdout=log,stderr=subprocess.STDOUT,timeout=1200)
            code=result.returncode
        except subprocess.TimeoutExpired:
            code=124
    records.append({"name":name,"command":cmd,"exit_code":code,"seconds":time.monotonic()-started})
    (evidence/"portable_commands.json").write_text(json.dumps(records,indent=2)+"\n")
    print(json.dumps(records[-1]),flush=True)
    if code:
        print((evidence/(name+".log")).read_text()[-6000:],flush=True)
        raise SystemExit(code)
    if source_binding()["digest"]!=binding:
        raise SystemExit("source changed during portable validation")
def record_from_log(name):
    for line in reversed((evidence/(name+".log")).read_text().splitlines()):
        try:
            value=json.loads(line)
        except ValueError:
            continue
        if isinstance(value,dict) and str(value.get("status", "")).startswith("PASS_"):
            if "source_binding" in value:
                assert value["source_binding"]==binding
            else:
                assert name.endswith("validate_r97_installed") and value["source_pin_status"]=="PIN_AND_LABELS_CHECKED"
            return value
    raise ValueError("missing bound installed report: "+name)
installed={name:record_from_log(name) for name,_ in commands if "installed" in name or name.endswith("packet_fix") or name.endswith("math_corrections")}
meta_cmd=["docker","image","inspect","--format","{{.Id}} {{.Architecture}} {{.Os}}","veritas-eth:r98-groups"]
meta=subprocess.run(meta_cmd,capture_output=True,text=True,check=True).stdout.strip().split()
wheel=next((evidence/"wheels").glob("*.whl"))
summary={"schema":"VERITAS_R98_GROUPS_PORTABLE_V1","status":"PASS","generated_utc":datetime.now(timezone.utc).isoformat(),"implementation_source_sha256":binding,"portable_command_count":len(records),"portable_commands":records,"installed":installed,"clean_wheel_python":installed["wheel_groups_installed"]["python"],"docker_python":installed["docker_groups_installed"]["python"],"wheel":{"path":str(wheel),"sha256":sha256(wheel.read_bytes()).hexdigest()},"docker":{"tag":"veritas-eth:r98-groups","image_id":meta[0],"architecture":meta[1],"operating_system":meta[2],"network":"none","cpus":2,"memory":"1g","pids_limit":256},"full_container_pytest":"NOT_RUN","hosted_ci":"NOT_RUN","source_qualified":False,"bit_time_bound_status":"COMPLEXITY_NOT_ESTABLISHED","peak_space_bound_status":"COMPLEXITY_NOT_ESTABLISHED"}
(evidence/"portable_summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
print(json.dumps({"status":"PASS","portable_commands":len(records),"source_binding":binding}),flush=True)
