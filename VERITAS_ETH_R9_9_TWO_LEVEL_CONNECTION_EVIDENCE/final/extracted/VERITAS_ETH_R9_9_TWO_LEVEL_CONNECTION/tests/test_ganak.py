import pytest
from veritas.core.cnf import CNF
from veritas.solvers.ganak import exact_count, CounterUnavailable


def test_mock_ganak_cli(tmp_path):
    program = tmp_path / 'ganak_fake'
    program.write_text('#!/bin/sh\nprintf "s mc 3\\n"\n')
    program.chmod(0o700)
    assert exact_count(CNF.from_lists(2, [[1, 2]]), executable=str(program)) == 3
    program.write_text('#!/bin/sh\nprintf "s SATISFIABLE\\nc s exact arb 3\\n"\n')
    assert exact_count(CNF.from_lists(2, [[1, 2]]), executable=str(program)) == 3
    program.write_text('#!/bin/sh\nprintf "s mc 3\\ns mc 4\\n"\n')
    with pytest.raises(CounterUnavailable):
        exact_count(CNF.from_lists(2, [[1, 2]]), executable=str(program))
    program.write_text('#!/bin/sh\nprintf "no answer\\n"\n')
    with pytest.raises(CounterUnavailable):
        exact_count(CNF.from_lists(2, [[1, 2]]), executable=str(program))
