"""Run outside the checkout with python -I against an installed R9.8 wheel."""

from importlib.metadata import version
import json
import platform

import veritas
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_recursive_contraction_v39.described_network import (
    describe_integer_network,
)
from veritas.research.parent_child_r98 import contract_scaled, from_described
from veritas.research.parent_child_r98.model import Policy
from veritas.research.tensor import Factor, TensorNetwork
from veritas.research.tapered_v4.provenance import source_binding


def main():
    if (
        version("veritas-eth") != veritas.__version__
        or veritas.__version__ != "3.8.2.post98"
    ):
        raise ValueError("installed version mismatch")
    net = TensorNetwork(
        1, (Factor((0,), (-2, 3), "row:0"), Factor((0,), (4, 5), "col:0"))
    )
    parent = from_described(
        describe_integer_network(
            net, creation_precision=5, defining_polynomial=first_irreducible(4)
        ),
        root_s=16,
        precision=5,
    )
    result = contract_scaled(
        parent,
        levels=2,
        strategy="scaled_singletons",
        policy=Policy(max_seconds=600, max_work=300_000_000),
    )
    if (
        result.get("result") != ((7, 0, 0, 0),)
        or result["ledger"]["maximum_depth"] != 2
    ):
        raise ValueError(result)
    print(
        json.dumps(
            {
                "status": "PASS_INSTALLED_R98_TWO_LEVEL",
                "python": platform.python_version(),
                "platform": platform.platform(),
                "result": result["result"],
                "ledger": result["ledger"],
                "source_binding": source_binding()["digest"],
                "theorem_mode_enabled": False,
            }
        )
    )


if __name__ == "__main__":
    main()
