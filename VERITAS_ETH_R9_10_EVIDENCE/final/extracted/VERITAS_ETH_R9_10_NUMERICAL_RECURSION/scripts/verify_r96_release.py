"""Verify a trusted local release ZIP and reproduce the isolated CI evidence step."""

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys
from tempfile import TemporaryDirectory
from zipfile import ZipFile


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def run(tree, command):
    proc = subprocess.run(
        [sys.executable, *command],
        cwd=tree,
        capture_output=True,
        text=True,
        timeout=120,
        env={**os.environ, "PYTHONPATH": str(tree / "src")},
    )
    require(proc.returncode == 0, proc.stderr or proc.stdout)
    return proc.stdout.strip()


def verify(archive, expected):
    digest = sha256(archive.read_bytes()).hexdigest()
    require(digest == expected, "unexpected archive digest")
    with TemporaryDirectory() as tmp, ZipFile(archive) as z:
        stage = Path(tmp)
        members = z.infolist()
        require(
            len(members) <= 2048 and sum(i.file_size for i in members) <= 256 * 1024**2,
            "inventory exceeds caps",
        )
        names = [i.filename for i in members]
        require(len(names) == len(set(names)) and z.testzip() is None, "zip integrity")
        prefixes = set()
        for i in members:
            path = PurePosixPath(i.filename)
            require(
                not path.is_absolute()
                and len(path.parts) >= 2
                and ".." not in path.parts
                and path.as_posix() == i.filename
                and "\\" not in i.filename
                and all(":" not in part for part in path.parts),
                "unsafe path",
            )
            require(stat.S_ISREG(i.external_attr >> 16), "non-regular archive member")
            prefixes.add(path.parts[0])
        require(len(prefixes) == 1, "ambiguous release root")
        z.extractall(stage)
        sealed = stage / prefixes.pop()
        json_hashes = json.loads((sealed / "SHA256_MANIFEST.json").read_text())["files"]
        payload = {
            p.relative_to(sealed).as_posix(): sha256(p.read_bytes()).hexdigest()
            for p in sealed.rglob("*")
            if p.is_file() and p.name not in ("SHA256SUMS.txt", "SHA256_MANIFEST.json")
        }
        require(json_hashes == payload, "JSON payload manifest mismatch")
        initial = run(sealed, ["scripts/verify_manifest.py"])
        optimized = run(sealed, ["-O", "scripts/verify_manifest.py"])
        work = stage / "ci-work"
        shutil.copytree(sealed, work)
        run(work, ["scripts/validate_v08.py"])
        artifacts = stage / "fresh"
        run(
            sealed,
            [
                "scripts/collect_ci_evidence.py",
                str(sealed / "validation"),
                str(work / "validation"),
                str(artifacts),
            ],
        )
        require(
            (artifacts / "validation_v08.json").is_file(),
            "missing newly generated CI artifact",
        )
        after = run(sealed, ["scripts/verify_manifest.py"])
        cnf = stage / "example.cnf"
        cnf.write_text("p cnf 3 2\n1 2 0\n-1 2 0\n")
        args = [
            "-m",
            "veritas.research.finite_reductions",
            str(cnf),
            "--leaf-edges",
            "1",
        ]
        cert = stage / "cli.json"
        result = json.loads(run(sealed, args + ["--write", str(cert)]))
        require(
            result.get("model_count") == 4
            and json.loads(run(sealed, args + ["--replay", str(cert)]))["valid"],
            "extracted CLI or replay failed",
        )
        require(after == initial == optimized, "sealed payload drift")
        return {
            "status": "PASS_FRESH_EXTRACTION",
            "archive_sha256": digest,
            "archive_members": len(members),
            "json_payload_hashes": len(payload),
            "sealed_manifest": after,
            "optimized_manifest": optimized,
            "separate_ci_artifact": "validation_v08.json",
            "cli_model_count": 4,
            "cli_replayed": True,
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    verdict = verify(args.archive, args.sha256)
    args.output.write_text(json.dumps(verdict, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(verdict))
