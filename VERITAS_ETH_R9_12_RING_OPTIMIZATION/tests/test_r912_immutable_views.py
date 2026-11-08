from hashlib import sha256
from dataclasses import replace
import pytest
from veritas.research.parent_child_r98.model import ModeSet,PacketLayout,Policy,canonical


def test_cached_decoding_returns_fresh_mutable_views():
    payload={'local':[[0,0,[[2**4096-1,0]]]],'modes':[]}
    modes=ModeSet('a'*64,canonical(payload));before=modes.content_digest
    view=modes.certificate;view['local'][0][2][0][0]=7
    view['modes'].append({'forged':True})
    assert modes.certificate==payload
    assert modes.content_digest==before==sha256(canonical(['a'*64,payload])).hexdigest()
    layout=PacketLayout('b'*64,1,1,canonical({'labels':[[1,2]]}))
    before=layout.content_digest;layout.source['labels'][0][0]=9
    assert layout.source=={'labels':[[1,2]]} and layout.content_digest==before
    altered=replace(modes,certificate_bytes=canonical({'local':[]}))
    assert altered.content_digest!=modes.content_digest


def test_total_stream_cap_is_separate_from_record_and_working_memory():
    assert Policy(max_certificate_bytes=1_000_000_000).max_certificate_bytes==1_000_000_000
    with pytest.raises(ValueError):Policy(max_certificate_bytes=1_000_000_001)


def test_measured_two_level_work_allowance_remains_bounded():
    assert Policy(max_work=2_000_000_000).max_work==2_000_000_000
    with pytest.raises(ValueError):Policy(max_work=2_000_000_001)
