"""Optional external exact model counter. Never pretend absence means zero solutions."""
from __future__ import annotations
import os
import shutil
import subprocess
import tempfile
from veritas.core.cnf import CNF


class CounterUnavailable(RuntimeError):
    pass


def exact_count(cnf: CNF, *, seconds: float = 10.0, executable: str | None = None) -> int:
    binary = executable or os.environ.get("VERITAS_GANAK") or shutil.which("ganak")
    if not binary:
        raise CounterUnavailable("Ganak binary not found; install separately and configure VERITAS_GANAK")
    if not (0 < seconds <= 30):
        raise ValueError("seconds out of range")
    with tempfile.TemporaryDirectory(prefix="veritas_ganak_") as root:
        path = os.path.join(root, "query.cnf")
        with open(path, "w", encoding="ascii") as f:
            f.write(cnf.to_dimacs())
        try:
            proc = subprocess.run([binary, "--mode", "0", "--prob", "0", path],
                                  capture_output=True, text=True, timeout=seconds, cwd=root)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise CounterUnavailable(f"Ganak unavailable or timed out: {type(exc).__name__}") from exc
        if proc.returncode not in (0, 10, 20):
            raise CounterUnavailable(f"Ganak failed (exit {proc.returncode})")
        # Require exactly one unambiguous answer line. Reject incomplete output.
        answers = []
        for line in proc.stdout.splitlines():
            words = line.strip().split()
            if len(words) == 3 and words[0:2] == ["s", "mc"] and words[2].isdigit():
                answers.append(int(words[2]))
            # Versions that print a tagged integer-field count rather than
            # the model-counting-competition line are supported explicitly.
            elif len(words) == 5 and words[:4] in (["c", "s", "exact", "arb"], ["c", "s", "exact", "int"] ) and words[4].isdigit():
                answers.append(int(words[4]))
        if not answers or len(set(answers)) != 1 or not (0 <= answers[0] <= 1 << cnf.n):
            raise CounterUnavailable("Ganak output lacks an unambiguous valid exact integer count")
        return answers[0]
