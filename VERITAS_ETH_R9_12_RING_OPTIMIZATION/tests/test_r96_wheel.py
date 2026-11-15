"""Exercise the actual installed wheel with cwd and import path outside the project."""
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys


def test_recorded_source_pin_matches_packaged_bytes():
    """The wheel pin is the digest of the bytes setuptools actually installs.

    Checkout transcripts hash the same virtual paths. A seal that is not rerun
    after a package edit leaves installed wheels raising SourceBindingError.
    """
    repo = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo / "src"))
    from veritas.research.tapered_v4.provenance import _digest

    package = repo / "src" / "veritas"
    paths = {}
    for path in package.rglob("*"):
        assert not path.is_symlink()
        if path.is_file() and path.suffix == ".py":
            paths["src/veritas/" + path.relative_to(package).as_posix()] = path
    for path in (package / "paper").rglob("*"):
        assert not path.is_symlink()
        if path.is_file():
            paths[path.relative_to(package).as_posix()] = path
    paths["pyproject.toml"] = package / "binding/pyproject.toml"
    paths["docs/OPENAI_PAPER_CONFORMANCE.md"] = package / "binding/OPENAI_PAPER_CONFORMANCE.md"
    entries = [{"path": name, "sha256": sha256(path.read_bytes()).hexdigest()}
               for name, path in sorted(paths.items())]
    pin = json.loads((package / "binding/source.json").read_text(encoding="utf-8"))
    assert pin == {"schema": "VERITAS_INSTALLED_SOURCE_V1", "sha256": _digest(entries)}


def test_installed_source_leaf_and_manuscript_pin(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    target = tmp_path / "installed"
    subprocess.run([sys.executable, "-m", "pip", "wheel", "--no-deps", "--no-index",
                    "--no-build-isolation", "-w", str(tmp_path), str(repo)], cwd=tmp_path, check=True)
    wheel, = tmp_path.glob("*.whl")
    subprocess.run([sys.executable, "-m", "pip", "install", "--no-index", "--no-deps",
                    "--target", str(target), str(wheel)], cwd=tmp_path, check=True)
    import json
    from veritas.research.tensor import Factor, TensorNetwork
    from veritas.research.finite_reductions import contract_boundary
    net=TensorNetwork(1,(Factor((0,),(-2,3),"a"),Factor((0,),(4,5),"b")))
    exported=contract_boundary(net,precision=5)["certificate"]
    (tmp_path/"checkout.json").write_text(json.dumps(exported))
    check = """
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from importlib.resources import files
import veritas
from veritas.research.tapered_v4.source_state import SourceContext, SourceNode
from veritas.research.tapered_v4.source_leaf import contract_source_leaf
from importlib.metadata import version
from veritas.research.tensor import Factor, TensorNetwork
from veritas.research.finite_reductions import contract_boundary, replay_boundary
import json
assert version("veritas-eth")==veritas.__version__=="3.8.2.post912"
net=TensorNetwork(1,(Factor((0,),(-2,3),"a"),Factor((0,),(4,5),"b")))
r=contract_boundary(net,precision=5)
assert r.get("result")==7,r
assert replay_boundary(net,json.loads(Path("checkout.json").read_text()),precision=5)["valid"]
extra=Path(veritas.__file__).parent/"unexpected_source.py"
extra.write_text("# extra source")
assert contract_boundary(net,precision=5)["status"]=="INCONCLUSIVE_SOURCE_MISMATCH"
extra.unlink()
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
