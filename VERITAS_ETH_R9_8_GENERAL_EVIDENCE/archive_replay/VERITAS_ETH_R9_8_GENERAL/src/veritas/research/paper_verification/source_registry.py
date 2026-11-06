"""Read and identify actual labeled text of the pinned October manuscript."""

from hashlib import sha256
from pathlib import Path

PIN = "4eaee87548250b2682affda7d05d947c05554bae"
FILES = {
    "main_full_version.tex": "b2e6159d4fb7ea6aa4f89ac15605152b0333a5f7cafe93323492bc20a5c066aa",
    "quantitative-contraction.tex": "671642d7b53154d92344e8c4be0240f18929632ebcfdf73b07c3e9939b873860",
    "quantitative-reduction.tex": "0b2b136c4f37ee0583dda40ee0c0d692f4751537d3d18539a389cd467ea8359a",
    "quantitative-circuits.tex": "0059668a666a35a6e0a67a7c5ed2e9b504862f4207d86e83ce5b7ab4b23fcc11",
}
# End markers delimit the statement, including the full explanatory subsection when requested.
BLOCKS = {
    "eq:tensor-parameters": r"\end{equation}",
    "eq:tensor-packing-conditions": r"\end{equation}",
    "lem:tensor-packets": r"\end{lemma}",
    "lem:tapered-hermite": r"\end{lemma}",
    "eq:tensor-mode-expansion": r"\end{equation}",
    "eq:tensor-mode-budget": r"\end{equation}",
    "eq:tensor-recursion-identity": r"\end{equation}",
    "subsec:tensor-children": r"\subsubsection",
    "subsec:tensor-cost": None,
    "eq:tensor-hermite-origin": r"\end{equation}",
}


def source_registry(directory=None):
    paper = (
        Path(directory)
        if directory is not None
        else Path(__file__).resolve().parents[2] / "paper"
    )
    for name, expected in FILES.items():
        p = paper / name
        if p.is_symlink() or sha256(p.read_bytes()).hexdigest() != expected:
            raise ValueError("source digest differs: " + name)
    if directory is None and paper.parent.parent.name == "src":
        checkout = paper.parent.parent.parent
        if (checkout / "scripts/verify_manifest.py").is_file():
            for name, expected in FILES.items():
                original = checkout / "paper" / name
                if (
                    original.is_symlink()
                    or sha256(original.read_bytes()).hexdigest() != expected
                ):
                    raise ValueError("vendored manuscript differs: " + name)
    text = (paper / "quantitative-contraction.tex").read_bytes()
    rows = {}
    for label, marker in BLOCKS.items():
        token = ("\\label{" + label + "}").encode()
        if text.count(token) != 1:
            raise ValueError("label missing or ambiguous: " + label)
        at = text.index(token)
        start = text.rfind(b"\n", 0, at) + 1
        if marker is None:
            end = len(text)
        else:
            end = text.index(marker.encode(), at)
            if marker != r"\subsubsection":
                end += len(marker)
        rows[label] = {
            "file": "quantitative-contraction.tex",
            "first_line": 1 + text.count(b"\n", 0, start),
            "last_line": 1 + text.count(b"\n", 0, end - 1),
            "statement_sha256": sha256(text[start:end]).hexdigest(),
        }
    return {
        "commit": PIN,
        "files": FILES.copy(),
        "labels": rows,
        "status": "PIN_AND_LABELS_CHECKED",
    }
