import base64
from copy import deepcopy
from hashlib import sha256
import random
import zlib
import pytest
from veritas.research.parent_child_r98.model import canonical,Refusal
from veritas.research.parent_child_r912.record_writer import pack_record
from veritas.research.parent_child_r912.record_reader import unpack_record


def event():
    return {'kind':'term','children':[{'value':[[2**30000-7,2**29000+9]]}]*64}


def test_exact_compressed_transport():
    original=event();packed=pack_record(original)
    assert packed['kind']=='compressed_record'
    assert canonical(unpack_record(packed,max_expanded_bytes=2000000))==canonical(original)
    assert len(canonical(packed))*20<len(canonical(original))


@pytest.mark.parametrize('attack',['hash','size','tail','payload','base64','nested'])
def test_compressed_tampering(attack):
    packed=pack_record(event())
    if attack=='hash':packed['content_sha256']='0'*64
    elif attack=='size':packed['decoded_size']-=1
    elif attack=='tail':packed['data']=base64.b64encode(base64.b64decode(packed['data'])+b'x').decode()
    elif attack=='payload':packed['data']=base64.b64encode(b'invalid').decode()
    elif attack=='base64':packed['data']+='\n'
    else:
        raw=canonical(packed);packed={'kind':'compressed_record','schema':'VERITAS_ZLIB_RECORD_V1',
            'decoded_size':len(raw),'content_sha256':sha256(raw).hexdigest(),
            'data':base64.b64encode(zlib.compress(raw)).decode()}
    with pytest.raises(ValueError):unpack_record(packed,max_expanded_bytes=2000000)


def test_expansion_bomb_is_bounded():
    packed=pack_record(event())
    with pytest.raises(Refusal):unpack_record(packed,max_expanded_bytes=1000)
    packed['decoded_size']=100
    with pytest.raises(ValueError):unpack_record(packed,max_expanded_bytes=1000)


@pytest.mark.parametrize('precision',[1,17,2048,16384])
def test_high_precision_inverse_against_separate_polynomial_arithmetic(precision):
    from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
    from veritas.research.independent_r95.recipe_oracle import ReferenceArithmetic
    from veritas.research.independent_r82.point_mode_oracle import _IndependentExtension,_Meter
    r=ExtensionRing(precision,19,max_precision_bits=65536)
    reference=ReferenceArithmetic(precision,19,1,100000,max_precision_bits=65536)
    independent=_IndependentExtension(precision,19,_Meter(100000,60),max_precision_bits=65536)
    rng=random.Random(2127+precision)
    for _ in range(3):
        a=tuple(rng.getrandbits(precision) for _ in range(4));a=(a[0]|1,)+a[1:]
        b=tuple(rng.getrandbits(precision) for _ in range(4))
        assert r.mul(a,b)==reference.mul((a,),(b,))[0]==independent.mul(a,b)
        inverse=r.inverse(a)
        assert reference.mul((a,),(inverse,))==reference.one
        assert inverse==independent.inverse(a)
