"""R9.6 regression tests: the pinned manuscript is a content-addressed resource.

Red test (R9.5): ``source_state.inspect_source_node`` derived the manuscript
path as ``Path(__file__).parents[4] / "paper/quantitative-contraction.tex"``.
That resolves inside a source checkout only.  An isolated virtual environment
containing just the wheel had no ``paper/`` directory, so every source-leaf
call returned

    {"status": "INCONCLUSIVE_SOURCE_MISMATCH",
     "reason": "pinned manuscript is absent or changed"}

Green test (R9.6): the bytes ship inside the distribution, are read through
``importlib.resources``, and are hash-checked on every access.  A missing or
substituted asset refuses with the same structured status and never yields a
value.
"""
import os
import shutil
from hashlib import sha256
from pathlib import Path

import pytest

from veritas.research.tapered_v4.manuscript import (
    ENVIRONMENT_VARIABLE, PINNED_MANUSCRIPT_SHA256, PinnedManuscript,
    read_pinned_manuscript, verify_manuscript_bytes)
from veritas.research.tapered_v4.source_leaf import (
    SourceLeafPolicy, contract_source_leaf)
from veritas.research.tapered_v4.source_state import (
    SourceAdmissionError, SourceContext, SourceNode, inspect_source_node)

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper" / "quantitative-contraction.tex"


def test_bundled_resource_carries_the_pinned_digest():
    pinned = read_pinned_manuscript()
    assert pinned.sha256 == PINNED_MANUSCRIPT_SHA256
    assert pinned.origin.startswith("package:")
    assert len(pinned.data) == PAPER.stat().st_size


def test_bundled_bytes_equal_the_vendored_paper_source():
    """The distribution copy must be byte-identical to paper/."""
    assert read_pinned_manuscript().data == PAPER.read_bytes()


def test_explicit_authentic_asset_is_accepted(tmp_path):
    copy = tmp_path / "authentic.tex"
    shutil.copyfile(PAPER, copy)
    pinned = read_pinned_manuscript(copy)
    assert pinned.sha256 == PINNED_MANUSCRIPT_SHA256
    assert pinned.origin == f"explicit:{copy}"
    assert pinned.text.startswith("\\")


def test_explicit_tampered_asset_is_refused(tmp_path):
    copy = tmp_path / "tampered.tex"
    data = bytearray(PAPER.read_bytes())
    data[len(data) // 2] ^= 0x01
    copy.write_bytes(bytes(data))
    with pytest.raises(SourceAdmissionError) as caught:
        read_pinned_manuscript(copy)
    assert caught.value.status == "INCONCLUSIVE_SOURCE_MISMATCH"
    assert "substituted or modified" in str(caught.value)


def test_truncated_asset_is_refused(tmp_path):
    copy = tmp_path / "truncated.tex"
    copy.write_bytes(PAPER.read_bytes()[:-1])
    with pytest.raises(SourceAdmissionError) as caught:
        read_pinned_manuscript(copy)
    assert caught.value.status == "INCONCLUSIVE_SOURCE_MISMATCH"


def test_missing_asset_is_refused(tmp_path):
    with pytest.raises(SourceAdmissionError) as caught:
        read_pinned_manuscript(tmp_path / "absent.tex")
    assert caught.value.status == "INCONCLUSIVE_SOURCE_MISMATCH"
    assert "absent" in str(caught.value)


def test_windows_style_path_is_not_silently_resolved():
    """A Windows separator must never be reinterpreted as a local search."""
    with pytest.raises(SourceAdmissionError) as caught:
        read_pinned_manuscript(r"C:\paper\quantitative-contraction.tex")
    assert caught.value.status == "INCONCLUSIVE_SOURCE_MISMATCH"


def test_directory_instead_of_file_is_refused(tmp_path):
    with pytest.raises(SourceAdmissionError) as caught:
        read_pinned_manuscript(tmp_path)
    assert caught.value.status == "INCONCLUSIVE_SOURCE_MISMATCH"


def test_oversized_asset_is_refused_before_reading(tmp_path):
    from veritas.research.tapered_v4 import manuscript as module
    big = tmp_path / "big.tex"
    big.write_bytes(b"x" * (module.MAXIMUM_MANUSCRIPT_BYTES + 1))
    with pytest.raises(SourceAdmissionError) as caught:
        read_pinned_manuscript(big)
    assert caught.value.status == "INCONCLUSIVE_RESOURCE_LIMIT"


def test_read_only_asset_directory_is_supported(tmp_path):
    directory = tmp_path / "readonly"
    directory.mkdir()
    copy = directory / "quantitative-contraction.tex"
    shutil.copyfile(PAPER, copy)
    os.chmod(copy, 0o444)
    os.chmod(directory, 0o555)
    try:
        assert read_pinned_manuscript(copy).sha256 == PINNED_MANUSCRIPT_SHA256
    finally:
        os.chmod(directory, 0o755)


def test_environment_variable_selects_the_asset(tmp_path, monkeypatch):
    copy = tmp_path / "env.tex"
    shutil.copyfile(PAPER, copy)
    monkeypatch.setenv(ENVIRONMENT_VARIABLE, str(copy))
    assert read_pinned_manuscript().origin == f"explicit:{copy}"
    tampered = tmp_path / "env_bad.tex"
    tampered.write_bytes(b"not the manuscript")
    monkeypatch.setenv(ENVIRONMENT_VARIABLE, str(tampered))
    with pytest.raises(SourceAdmissionError):
        read_pinned_manuscript()


def test_verify_manuscript_bytes_rejects_wrong_types():
    with pytest.raises(TypeError):
        verify_manuscript_bytes("text")  # type: ignore[arg-type]
    assert verify_manuscript_bytes(PAPER.read_bytes()) == PINNED_MANUSCRIPT_SHA256


def test_pinned_record_with_foreign_digest_is_refused():
    with pytest.raises(SourceAdmissionError):
        read_pinned_manuscript(PinnedManuscript(b"x", "forged", "0" * 64))


def test_source_admission_refuses_a_substituted_asset(tmp_path, monkeypatch):
    context = SourceContext(2, 1, 1, 1, 1, 1, 19)
    node = SourceNode(context, 0, (), 0, 1)
    tampered = tmp_path / "bad.tex"
    tampered.write_bytes(b"substituted")
    monkeypatch.setenv(ENVIRONMENT_VARIABLE, str(tampered))
    with pytest.raises(SourceAdmissionError) as caught:
        inspect_source_node(node)
    assert caught.value.status == "INCONCLUSIVE_SOURCE_MISMATCH"


def test_source_leaf_refuses_a_substituted_asset_without_a_value(tmp_path, monkeypatch):
    context = SourceContext(2, 1, 1, 1, 1, 1, 19)
    node = SourceNode(context, 0, (), 0, 1)
    tampered = tmp_path / "bad.tex"
    tampered.write_bytes(b"substituted")
    monkeypatch.setenv(ENVIRONMENT_VARIABLE, str(tampered))
    out = contract_source_leaf(node, SourceLeafPolicy())
    assert out["status"] == "INCONCLUSIVE_SOURCE_MISMATCH"
    assert "result" not in out
    assert out["theorem_mode_enabled"] is False


def test_source_leaf_accepts_an_explicit_authentic_asset(tmp_path):
    context = SourceContext(2, 1, 1, 1, 1, 1, 19)
    node = SourceNode(context, 0, (), 0, 1)
    copy = tmp_path / "authentic.tex"
    shutil.copyfile(PAPER, copy)
    out = contract_source_leaf(node, SourceLeafPolicy(), manuscript=copy)
    assert out["status"] == "EXACT_SOURCE_LEAF_MODULAR_CONTRACTION"
    assert out["result"] == ((1, 0, 0, 0),)


def test_no_parent_directory_search_remains_in_source_state():
    text = (ROOT / "src/veritas/research/tapered_v4/source_state.py").read_text(
        encoding="utf-8")
    assert "parents[4]" not in text
    assert "quantitative-contraction.tex" not in text
