"""Exercise the actual installed wheel with cwd and import path outside the project."""
from pathlib import Path
import subprocess
import sys


def test_installed_source_leaf_and_manuscript_pin(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    target = tmp_path / "installed"
    subprocess.run([sys.executable, "-m", "pip", "wheel", "--no-deps", "--no-index",
                    "--no-build-isolation", "-w", str(tmp_path), str(repo)], cwd=tmp_path, check=True)
    wheel, = tmp_path.glob("*.whl")
    subprocess.run([sys.executable, "-m", "pip", "install", "--no-index", "--no-deps",
                    "--target", str(target), str(wheel)], cwd=tmp_path, check=True)
    check = """
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from importlib.resources import files
import veritas
from veritas.research.tapered_v4.source_state import SourceContext, SourceNode
from veritas.research.tapered_v4.source_leaf import contract_source_leaf
assert Path(veritas.__file__).resolve().is_relative_to(Path(sys.argv[1]))
node = SourceNode(SourceContext(2, 2, 1, 2, 2, 1, 19), 0, (), 0, 2)
result = contract_source_leaf(node)
assert result['result'] == ((1, 0, 0, 0),), result
paper = files('veritas').joinpath('paper').joinpath('quantitative-contraction.tex')
paper.write_bytes(b'corrupted')
bad = contract_source_leaf(node)
assert bad['status'] == 'INCONCLUSIVE_SOURCE_MISMATCH' and 'result' not in bad
"""
    subprocess.run([sys.executable, "-I", "-c", check, str(target)], cwd=tmp_path, check=True)
    for src in (repo / "paper").glob("*.tex"):
        assert src.read_bytes() == (repo / "src/veritas/paper" / src.name).read_bytes()
