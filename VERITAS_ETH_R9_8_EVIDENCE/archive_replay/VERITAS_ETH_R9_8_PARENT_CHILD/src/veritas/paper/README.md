# Pinned source: the OpenAI ETH preprint

This directory vendors the LaTeX source of the paper that the finite
reference in `src/veritas/research/` is written against, so that every
parameter, lemma label, and equation number cited by this project can be
checked against the actual source rather than a remembered summary.

## Citation

> **The Exponential Time Hypothesis is False**, OpenAI, 25 October 2026.
> `README.upstream.md` is the upstream README, including the BibTeX entry.

The PDF is not redistributed here. Its upstream SHA-256 is recorded below so
an independent copy can be checked against the source vendored here.

## Files

| File | Upstream SHA-256 | Bytes |
|---|---|---|
| `main_full_version.tex` | `b2e6159d4fb7ea6aa4f89ac15605152b0333a5f7cafe93323492bc20a5c066aa` | 214857 |
| `quantitative-reduction.tex` | `0b2b136c4f37ee0583dda40ee0c0d692f4751537d3d18539a389cd467ea8359a` | 17832 |
| `quantitative-contraction.tex` | `671642d7b53154d92344e8c4be0240f18929632ebcfdf73b07c3e9939b873860` | 27544 |
| `quantitative-circuits.tex` | `0059668a666a35a6e0a67a7c5ed2e9b504862f4207d86e83ce5b7ab4b23fcc11` | 4152 |
| `README.upstream.md` | `a40b8829123b44bd9cfb589e5afa856b0018dc8cb36de36fa79e4315a03fe506` | 551 |
| `paper.pdf` (not vendored) | `5b1612dc2eebb2cad5b4cbe62d1fed2982f01ab1908c26f70010a651487e8123` | 887884 |

The vendored bytes are unmodified; `README.upstream.md` is the upstream
`README.md` renamed so it does not collide with this file. The hashes above
are also enforced by `tests/test_openai_paper_conformance.py` and by the
top-level release manifest.

## What lives where

- `main_full_version.tex` — the whole paper. The main theorem is
  `thm:main` (subexponential time, polynomial space, for every fixed `k`).
- `quantitative-reduction.tex` — Appendix `app:quantitative`,
  "A sharper bound for exact counting". States the contraction theorem
  `thm:tensor-contraction` and reduces #`k`-SAT to it.
- `quantitative-contraction.tex` — Appendix `app:tensor`, "Proof of the
  contraction theorem". This is the appendix the finite reference
  implements: collision packing (`lem:tensor-packets`), the Cauchy
  deformation, tapered Hermite recovery (`lem:tapered-hermite`), the mode
  expansion, and the recursive child construction.
- `quantitative-circuits.tex` — the `E^NP` circuit-lower-bound corollary.
  Not used by this project.

## Naming note

The paper has **no "Appendix D"**. This project historically labelled the
contraction appendix "Appendix D" and referred to "D.3", "D.4.4", and "D.6".
Those are aliases for, respectively:

- **D.3** → Lemma `lem:tensor-packets` ("Packing into packets") and the
  packing conditions `eq:tensor-packing-conditions`.
- **D.4.4** → the child construction in `subsec:tensor-children`
  ("The child networks and their descriptions").
- **D.6** → the same packing conditions, previously cited as a numbered
  display.

`docs/OPENAI_PAPER_CONFORMANCE.md` gives the full mapping and the exact
parameter formulas.
