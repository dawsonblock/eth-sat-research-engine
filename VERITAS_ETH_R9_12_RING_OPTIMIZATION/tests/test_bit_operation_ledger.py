from veritas.research.bit_operation_ledger import BitOperationLedger


def test_nested_bit_totals():
    root = BitOperationLedger()
    root.charge('local', 10)
    child = root.child()
    child.charge('child', 5)
    report = root.report()
    assert report['total_bits'] == 15
    assert report['child_frames'] == 1
