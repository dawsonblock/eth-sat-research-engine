"""Mutation checks for the new model/executable evidence boundary."""
import copy
import importlib.util
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import validate_r94_foundation as validation
from veritas.research.eth_packing_v26.streaming import construct_streaming_d3_packing
from veritas.research.eth_packing_v26.streaming_check import verify_streaming_d3_certificate


@pytest.mark.parametrize("actual", [["a","a","c"], ["b","a","c"], ["a","b"], ["a","b","c","d"], ["x","b","c"]])
def test_full_sequence_detects_substitution_order_duplicate_and_truncation(actual):
    with pytest.raises(ValueError,match="sequence mismatch"):
        validation.assert_complete(actual,["a","b","c"])


def test_empty_sequence_matches_only_empty():
    validation.assert_complete([],[])


@pytest.mark.parametrize("mutation", ["order","tie","score","state","side","omit"])
def test_independent_replay_rejects_semantic_trace_mutations(mutation):
    cert=construct_streaming_d3_packing([(0,0),(1,1),(0,1)],r=2,a=1,
                                        max_work=100_000,score_backend="python").certificate
    assert verify_streaming_d3_certificate(cert)["valid"]
    altered=copy.deepcopy(cert)
    if mutation=="order": altered["steps"][0],altered["steps"][1]=altered["steps"][1],altered["steps"][0]
    if mutation=="tie": altered["steps"][0]["label"]=[1] # same candidate score, wrong first minimizer
    if mutation=="score": altered["steps"][0]["expected_square_scaled"]+=1
    if mutation=="state": altered["row_labels"]["0"]=[1]
    if mutation=="side": altered["steps"][0]["side"]="C"
    if mutation=="omit": altered["steps"].pop()
    assert verify_streaming_d3_certificate(altered)["valid"] is False


def test_regression_corpus_preserves_exact_three_edge_fixture():
    _,_,records,domains=validation.generate()
    fixture=records[2]
    assert [s["label"] for s in fixture["steps"]]==[[0],[1],[0],[1]]
    assert [s["expected_square_scaled"] for s in fixture["steps"]]==[22,16,16,12]
    assert fixture["initial_score"]==22 and fixture["final_score"]==12
    assert all(d["addresses"]==d["r"]**(2*d["a"])*d["H"] for d in domains)
