"""Run with Python -I outside the checkout to test the installed package only."""

from importlib.metadata import version
import json
import platform
import resource
from time import perf_counter

import veritas
from veritas.research.finite_reductions import (
    BoundaryPolicy, contract_boundary, replay_boundary,
)
from veritas.research.paper_verification.boundary_identity import verify_boundary_tree
from veritas.research.paper_verification.source_registry import source_registry
from veritas.research.tensor import Factor, TensorNetwork


def require(test, message):
    if not test:
        raise RuntimeError(message)


def main():
    require(version("veritas-eth") == veritas.__version__ == "3.8.2.post97", "version")
    start = perf_counter()
    small = TensorNetwork(1, (Factor((0,), (-2, 3), "a"), Factor((0,), (4, 5), "b")))
    result = contract_boundary(small, precision=5)
    require(result.get("result") == 7, str(result))
    require(replay_boundary(small, result["certificate"], precision=5)["valid"], "replay")
    data = (1,) * (1 << 16)
    net = TensorNetwork(16, (Factor(tuple(range(16)), data, "a"),
                            Factor(tuple(range(15, -1, -1)), data, "b")))
    policy = BoundaryPolicy(on_call_overflow="certified_elimination")
    strict = contract_boundary(net, precision=17)
    require(strict["status"] == "INCONCLUSIVE_RESOURCE_LIMIT" and "result" not in strict,
            "strict refusal")
    dense = contract_boundary(net, precision=17, policy=policy)
    require(dense.get("result") == 65536, str(dense))
    check = verify_boundary_tree(net, dense["certificate"], precision=17, policy=policy)
    require(check.get("result") == 65536, str(check))
    registry = source_registry()
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print(json.dumps({
        "status": "PASS_INSTALLED_FINITE_EXECUTION", "package_version": veritas.__version__,
        "python": platform.python_version(), "platform": platform.platform(),
        "one_wire_residue": 7, "dense_16_wire_residue": 65536,
        "source_pin_status": registry["status"], "wall_seconds": perf_counter() - start,
        "peak_process_rss_bytes": rss * (1 if platform.system() == "Darwin" else 1024),
        "theorem_mode_enabled": False,
    }))


if __name__ == "__main__":
    main()
