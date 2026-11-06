"""Run during release assembly, before building the wheel and archive manifests."""

import json
from pathlib import Path
from shutil import copyfile
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from veritas.research.tapered_v4.provenance import source_binding


def seal():
    base = ROOT / "src/veritas"
    (base / "binding").mkdir(exist_ok=True)
    for src in (ROOT / "paper").iterdir():
        if src.is_file():
            copyfile(src, base / "paper" / src.name)
    for name in ("pyproject.toml", "docs/OPENAI_PAPER_CONFORMANCE.md"):
        copyfile(ROOT / name, base / "binding" / Path(name).name)
    record = {
        "schema": "VERITAS_INSTALLED_SOURCE_V1",
        "sha256": source_binding(ROOT)["digest"],
    }
    (base / "binding/source.json").write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8"
    )
    print(record["sha256"])


if __name__ == "__main__":
    seal()
