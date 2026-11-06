"""Regression tests for v3.8 review findings; all certificates are finite."""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

import pytest

from veritas.core.cnf import CNF
from veritas.research.tensor import Factor, TensorNetwork, from_cnf
from veritas.research.eth_child_elimination_v38 import engine
from veritas.research.eth_d44_child_reference import construct_child_reference, verify_child_reference
from veritas.research.eth_modes_v31 import make_jet_tile_modes
from veritas.research.eth_packing_v26.constructor import construct_d3_packing
from veritas.research.eth_recursion_v30.implicit_children import (
    ImplicitBudgetExceeded, make_bipartite_edges,
)


def instance(net=None, *, r=2):
    if net is None:
        net = from_cnf(CNF.from_lists(2, [[1, 2]]))
    packing = construct_d3_packing(make_bipartite_edges(net), r=r, a=1)
    return net, make_jet_tile_modes(packing, node=1, precision=4,
                                    extension_degree=2, jet_length=2)


def test_shared_ledger_covers_oracle_and_v37_and_replays():
    net, modes = instance()
    cert = engine.construct_elimination_reference(net, modes, compare_v37=True)
    assert cert['work'] == sum(cert['work_by_phase'].values())
    assert all(cert['work_by_phase'][p] > 0 for p in
               ('validation', 'mode_enumeration_and_elimination', 'direct_oracle', 'v37_comparison'))
    assert cert['work_measure'] == 'cooperative_charged_events_not_bit_operations'
    assert engine.verify_elimination_reference(cert)['valid']
    corrupt = deepcopy(cert)
    corrupt['work_by_phase']['direct_oracle'] += 1
    assert not engine.verify_elimination_reference(corrupt)['valid']


def test_expired_validation_does_not_return_count(monkeypatch):
    net, modes = instance()
    original = engine.check_jet_tile_modes
    def slow(cert, **kwargs):
        time.sleep(.04)
        return original(cert, **kwargs)
    monkeypatch.setattr(engine, 'check_jet_tile_modes', slow)
    with pytest.raises(engine.ResourceLimit):
        engine.construct_elimination_reference(net, modes, timeout_s=.01)


def test_oracle_exhaustion_is_inconclusive(monkeypatch):
    net, modes = instance()
    cert = engine.construct_elimination_reference(net, modes)
    def exhausted(*args, **kwargs):
        raise ImplicitBudgetExceeded('injected oracle exhaustion')
    monkeypatch.setattr(engine, '_direct_oracle', exhausted)
    verdict = engine.verify_elimination_reference(cert)
    assert not verdict['valid'] and verdict['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT'
    assert 'count' not in verdict and 'result' not in verdict


def test_api_check_reports_oracle_exhaustion(monkeypatch):
    from fastapi.testclient import TestClient
    from veritas.api.main import app
    net, modes = instance()
    cert = engine.construct_elimination_reference(net, modes)
    def exhausted(*args, **kwargs):
        raise ImplicitBudgetExceeded('oracle timeout')
    monkeypatch.setattr(engine, '_direct_oracle', exhausted)
    response = TestClient(app).post('/v1/research/eth/finite-child-elimination/check',
                                    json={'certificate': cert})
    assert response.status_code == 200
    assert response.json()['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT'


def test_api_setup_is_within_shared_deadline(monkeypatch):
    from fastapi.testclient import TestClient
    import veritas.api.main as api
    original = api._eth29_d3
    def slow(*args, **kwargs):
        time.sleep(.04)
        return original(*args, **kwargs)
    monkeypatch.setattr(api, '_eth29_d3', slow)
    monkeypatch.setattr(api, '_Eth38SharedMeter', lambda work, seconds: engine.SharedMeter(work, .01))
    response = TestClient(api.app).post('/v1/research/eth/finite-child-elimination', json={})
    assert response.status_code == 422
    assert 'certificate' not in response.json()


def test_api_success_exposes_full_charged_event_ledger():
    from fastapi.testclient import TestClient
    from veritas.api.main import app
    response = TestClient(app).post('/v1/research/eth/finite-child-elimination', json={})
    assert response.status_code == 200
    body = response.json()
    assert body['checker']['valid']
    assert body['budget']['work'] == sum(body['budget']['work_by_phase'].values())
    assert body['budget']['work'] > body['certificate']['work']


def test_natural_work_exhaustion_is_inconclusive():
    net, modes = instance(from_cnf(CNF.from_lists(3, [[1,-2,3], [2,-3,1]])), r=4)
    cert = engine.construct_elimination_reference(net, modes, max_work=200_000)
    verdict = engine.verify_elimination_reference(cert, max_work=500)
    assert not verdict['valid'] and verdict['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT'


@pytest.mark.parametrize('kwargs', [{'max_work':2_000_001}, {'timeout_s':31},
                                    {'max_work':99}, {'timeout_s':0}])
def test_inconsistent_budget_range_rejected_before_validation(kwargs, monkeypatch):
    def should_not_run(*args, **kw):
        raise AssertionError('validation ran before parameter validation')
    monkeypatch.setattr(engine, 'check_jet_tile_modes', should_not_run)
    with pytest.raises(ValueError):
        engine.construct_elimination_reference(None, None, **kwargs)


def test_repeated_factor_labels_have_distinct_cache_entries():
    network = TensorNetwork(2, (
        Factor((0,), (1, 2), 'row:0'), Factor((1,), (3, 4), 'row:0'),
        Factor((0,), (1, 1), 'col:0'), Factor((1,), (1, 1), 'col:1'),
    ))
    net, modes = instance(network)
    cached = engine.construct_elimination_reference(net, modes, max_cache_entries=8192)
    uncached = engine.construct_elimination_reference(net, modes, max_cache_entries=0)
    legacy = construct_child_reference(net, modes)
    assert cached['result'] == uncached['result'] == legacy['result']
    assert engine.verify_elimination_reference(cached)['valid']


def test_v37_certificate_created_by_original_archive_still_replays():
    fixture = Path(__file__).parent / 'fixtures' / 'v37-archive-replay.json'
    cert = json.loads(fixture.read_text())
    assert verify_child_reference(cert)['valid']


@pytest.mark.parametrize('optimized', [False, True])
@pytest.mark.parametrize('mutation', ['modified', 'missing', 'added', 'duplicate', 'escape'])
def test_manifest_rejects_tampering_even_under_optimization(tmp_path, mutation, optimized):
    root = tmp_path / 'release'
    scripts = root / 'scripts'
    scripts.mkdir(parents=True)
    source = Path(__file__).resolve().parents[1] / 'scripts' / 'verify_manifest.py'
    shutil.copyfile(source, scripts / 'verify_manifest.py')
    payload = root / 'payload.txt'
    payload.write_text('correct\n')
    def line(path):
        rel = path.relative_to(root).as_posix()
        return hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + rel + '\n'
    manifest = root / 'SHA256SUMS.txt'
    manifest.write_text(line(payload) + line(scripts / 'verify_manifest.py'))
    cmd = [sys.executable] + (['-O'] if optimized else []) + [str(scripts / 'verify_manifest.py')]
    env = {**os.environ, 'PYTHONOPTIMIZE': '1' if optimized else '0'}
    assert subprocess.run(cmd, env=env, capture_output=True).returncode == 0
    if mutation == 'modified': payload.write_text('tampered\n')
    elif mutation == 'missing': payload.unlink()
    elif mutation == 'added': (root / 'extra.txt').write_text('extra')
    elif mutation == 'duplicate': manifest.write_text(manifest.read_text() + line(payload))
    else: manifest.write_text(manifest.read_text() + '0'*64 + '  ../escape\n')
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True)
    assert proc.returncode != 0 and 'FAIL:' in proc.stderr


def test_optimized_builder_refreshes_both_manifests_and_zip(tmp_path):
    from zipfile import ZipFile
    root = tmp_path / 'release'
    scripts = root / 'scripts'
    scripts.mkdir(parents=True)
    source = Path(__file__).resolve().parents[1] / 'scripts'
    for name in ('verify_manifest.py', 'build_release.py'):
        shutil.copyfile(source / name, scripts / name)
    (root / 'payload').write_text('payload')
    (root / 'SHA256_MANIFEST.json').write_text('stale')
    proc = subprocess.run([sys.executable, '-O', str(scripts / 'build_release.py')],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    recorded = json.loads((root / 'SHA256_MANIFEST.json').read_text())['files']
    assert recorded['payload'] == hashlib.sha256(b'payload').hexdigest()
    archive = tmp_path / 'VERITAS_ETH_R9_1_CPP_LEAN_REFINEMENT_FULL_UPGRADED.zip'
    assert archive.is_file()
    sidecar = json.loads(
        (tmp_path / (archive.name + '.manifest.json')).read_text())
    assert sidecar['schema'] == 'VERITAS_ETH_RELEASE_ZIP_MANIFEST_V1'
    assert sidecar['archive_sha256'] == hashlib.sha256(archive.read_bytes()).hexdigest()
    assert sidecar['member_count'] == len(sidecar['members'])
    with ZipFile(archive) as z:
        z.extractall(tmp_path / 'extracted')
    verifier = tmp_path / 'extracted' / 'release' / 'scripts' / 'verify_manifest.py'
    assert subprocess.run([sys.executable, '-O', str(verifier)], capture_output=True).returncode == 0


def test_cli_rejects_invalid_work_before_parsing_formula():
    proc = subprocess.run([sys.executable, '-m', 'veritas.research.eth_child_elimination_v38.cli',
                           'construct', '--clauses-json', 'invalid-json', '--max-work', '2000001'],
                          capture_output=True, text=True)
    assert proc.returncode != 0
    assert 'must be in 100..2000000' in proc.stderr
    assert 'JSONDecodeError' not in proc.stderr
