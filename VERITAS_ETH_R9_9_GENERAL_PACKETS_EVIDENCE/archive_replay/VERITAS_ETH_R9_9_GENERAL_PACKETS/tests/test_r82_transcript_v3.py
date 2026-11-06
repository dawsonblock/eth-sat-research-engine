from copy import deepcopy
from hashlib import sha256
import json

from veritas.core.cnf import CNF
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_recursive_contraction_v39 import describe_integer_network
from veritas.research.tapered_v4 import RecursionPolicy, TaperedState, contract_recursive, replay_certificate
from veritas.research.tapered_v4.certificates import canonical
from veritas.research.tapered_v4.provenance import source_binding
from veritas.research.tapered_v4.recursor import _evidence_digest
from veritas.research.tensor import from_cnf


def _state(clauses=((1, 2),)):
    f = first_irreducible(3)
    net = describe_integer_network(from_cnf(CNF.from_lists(2, [list(c) for c in clauses])),
                                  creation_precision=3, defining_polynomial=f)
    return TaperedState(net, 0, 3, f, 1, net.edges)


def _v3():
    state = _state()
    policy = RecursionPolicy(allow_nonshrinking_leaf=True)
    result = contract_recursive(state, policy)
    assert result["status"] == "EXACT_MODULAR_CONTRACTION_FINITE"
    assert result["certificate"]["schema_version"] == 3
    return state, policy, result["certificate"]


def test_v3_replay_binds_source_policy_paper_input_and_unsigned_status():
    state, policy, cert = _v3()
    assert cert["trust_class"] == "HASH_MATCH_UNSIGNED"
    assert cert["manuscript_binding"]["pin_matches"]
    assert cert["source_binding"]["digest"] == source_binding()["digest"]
    assert cert["input_network_digest"]
    assert cert["execution_policy"] == policy.__dict__
    assert replay_certificate(state, policy, cert)["valid"]
    changed_policy = RecursionPolicy(allow_nonshrinking_leaf=True,
                                     auto_point_oracle_edges=3)
    assert replay_certificate(state, changed_policy, cert)["status"] == "POLICY_MISMATCH"


def test_v3_canonical_replay_accepts_reordered_json_keys():
    state, policy, cert = _v3()
    reordered = json.loads(json.dumps(cert, sort_keys=False))
    reordered = dict(reversed(list(reordered.items())))
    reordered["input_state"] = dict(reversed(list(reordered["input_state"].items())))
    assert replay_certificate(state, policy, reordered)["valid"]


def test_v3_transcript_embeds_and_hashes_finite_packing_mode_and_child_certificates():
    _, _, cert = _v3()
    packing = [item["payload"] for item in cert["events"]
               if item.get("payload", {}).get("kind") == "packing"]
    points = [item["payload"] for item in cert["events"]
              if item.get("payload", {}).get("kind") == "point"]
    recipes = [item["payload"] for item in cert["events"]
               if item.get("payload", {}).get("kind") == "child_recipe_check"]
    assert packing and all("source_certificate" in item for item in packing)
    assert points and all("mode_certificate" in item for item in points)
    assert recipes and all("certificate" in item for item in recipes)
    for item in packing:
        assert sha256(canonical(item["source_certificate"])).hexdigest() == item["source_sha256"]
    for item in points:
        assert sha256(canonical(item["mode_certificate"])).hexdigest() == item["mode_certificate_sha256"]
    for item in recipes:
        assert sha256(canonical(item["certificate"])).hexdigest() == item["certificate_sha256"]


def test_v3_rejects_omitted_policy_field_and_modified_default():
    state, policy, cert = _v3()
    omitted = deepcopy(cert)
    omitted["execution_policy"].pop("auto_point_oracle_edges")
    assert replay_certificate(state, policy, omitted)["status"] == "POLICY_MISMATCH"
    changed = deepcopy(cert)
    changed["execution_policy"]["auto_point_oracle_edges"] = 3
    changed["evidence_sha256"] = _evidence_digest(changed)
    assert replay_certificate(state, policy, changed)["status"] == "POLICY_MISMATCH"


def test_v3_rejects_source_pin_input_forgery_and_truncation():
    state, policy, cert = _v3()
    source_changed = deepcopy(cert)
    source_changed["source_binding"]["files"][0]["sha256"] = "0" * 64
    source_changed["evidence_sha256"] = _evidence_digest(source_changed)
    assert replay_certificate(state, policy, source_changed)["status"] == "SOURCE_HASH_MISMATCH"
    paper_changed = deepcopy(cert)
    paper_changed["manuscript_binding"]["tree_digest"] = "0" * 64
    paper_changed["evidence_sha256"] = _evidence_digest(paper_changed)
    assert replay_certificate(state, policy, paper_changed)["status"] == "MANUSCRIPT_PIN_MISMATCH"
    input_changed = deepcopy(cert)
    input_changed["input_network_digest"] = "0" * 64
    input_changed["evidence_sha256"] = _evidence_digest(input_changed)
    assert not replay_certificate(state, policy, input_changed)["valid"]
    truncated = deepcopy(cert)
    truncated["events"].pop()
    assert replay_certificate(state, policy, truncated)["status"] == "EVIDENCE_HASH_MISMATCH"


def test_v3_rejects_forged_mode_dependency_even_after_outer_rehash():
    state, policy, cert = _v3()
    forged = deepcopy(cert)
    point_events = [event for event in forged["events"]
                    if event.get("payload", {}).get("kind") == "point"]
    if point_events:
        point_events[0]["payload"]["mode_certificate_sha256"] = "0" * 64
    else:
        forged["certificate_dependencies"]["mode_certificate_sha256"] = ["0" * 64]
    forged["evidence_sha256"] = _evidence_digest(forged)
    result = replay_certificate(state, policy, forged)
    assert not result["valid"]
    assert result["status"] == "INVALID_CERTIFICATE"


def test_v3_live_source_digest_mismatch_is_rejected(monkeypatch):
    from veritas.research.tapered_v4 import recursor
    state, policy, cert = _v3()
    original = recursor.source_binding
    def changed():
        value = deepcopy(original())
        value["files"].append({"path": "src/veritas/added.py", "sha256": "0" * 64})
        value["digest"] = "0" * 64
        return value
    monkeypatch.setattr(recursor, "source_binding", changed)
    assert replay_certificate(state, policy, cert)["status"] == "SOURCE_HASH_MISMATCH"


def test_source_digest_changes_for_modified_added_deleted_files_and_rejects_symlink(tmp_path):
    root = tmp_path
    (root / "src" / "veritas").mkdir(parents=True)
    (root / "src" / "veritas" / "base.py").write_text("x = 1\n")
    (root / "paper").mkdir()
    (root / "paper" / "quantitative-contraction.tex").write_text("source\n")
    first = source_binding(root)
    (root / "src" / "veritas" / "base.py").write_text("x = 2\n")
    modified = source_binding(root)
    assert first["digest"] != modified["digest"]
    (root / "src" / "veritas" / "added.py").write_text("y = 1\n")
    added = source_binding(root)
    assert modified["digest"] != added["digest"]
    (root / "src" / "veritas" / "added.py").unlink()
    deleted = source_binding(root)
    assert added["digest"] != deleted["digest"]
    try:
        (root / "src" / "veritas" / "link.py").symlink_to(root / "src" / "veritas" / "base.py")
    except (OSError, NotImplementedError):
        return
    try:
        source_binding(root)
    except RuntimeError as exc:
        assert "symlink" in str(exc)
    else:
        raise AssertionError("symlink was accepted into the source manifest")


def test_v3_validation_wrapper_hashes_content_and_normalizes_json_key_order():
    from scripts.validate_tapered_v4 import SCHEMA, _evidence_digest
    record = {"schema": SCHEMA, "input_network_digest": "abc",
              "policy": {"max_work": 10, "verify_small_nodes": False},
              "point_coverage": {"points_total": 1, "points_checked": 1}}
    digest = _evidence_digest(record)
    reordered = dict(reversed(list(record.items())))
    reordered["policy"] = dict(reversed(list(reordered["policy"].items())))
    assert _evidence_digest(reordered) == digest
    forged = deepcopy(record)
    forged["input_network_digest"] = "changed"
    assert _evidence_digest(forged) != digest
