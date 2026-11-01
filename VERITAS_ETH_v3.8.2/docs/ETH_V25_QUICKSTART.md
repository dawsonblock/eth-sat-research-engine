# VERITAS-ETH v2.5 quickstart

Install from the extracted ZIP in a Python >=3.10 environment:

```powershell
py -m pip install -e ".[test]"
py -m pytest -q
veritas-eth25 parameters --s 1000
veritas-eth25 pack --edges-json "[[0,1],[0,1],[2,3],[2,3]]" --a 2 --r 4
veritas-eth25 ring --precision 8 --degree 4
veritas-eth25 cauchy --packet-size 4
.\start_windows.ps1
```

Linux/WSL:

```bash
python -m pip install -e '.[test]'
python -m pytest -q
python scripts/validate_v25.py
./start.sh
```

Research endpoints under `/v1/research/eth/`:

- POST `parameters` `{ "s": 1000, "mode": "MANUSCRIPT_EXACT", "depth": 0 }`
- POST `packing` `{ "edges": [[0,1],[0,1]], "a": 1, "r": 2 }`
- POST `packing/check` `{ "certificate": { ... } }`
- POST `ring` `{ "degree": 4, "precision": 8, "coefficients": [1,1] }`
- GET `status`

Packet edge endpoints are graph-vertex identifiers; the builder assigns
symbols to each endpoint. The `verification` section is recomputed by a
separate checker and distinguishes structural validity from numeric bounds.

Run `python scripts/build_release.py` to produce a reproducible source ZIP.
