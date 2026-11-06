# Implicit D.3 packet reference

`veritas.research.eth_packing_v26.implicit.construct_implicit_packing` stores real directed label classes as edge-ID tuples. Empty classes and their padding are represented by absence and the common padding length H. `packet_slot(pairs, index, slot)` computes one slot; `packet` and `iter_packets` are explicitly budgeted views. Packet count is computed arithmetically, so a large number of empty classes does not itself require materializing them.

`check_implicit_packing` reconstructs the real classes from original edges and labels, checks their contents and H, and independently computes the location of each real edge before asking the slot reader to resolve that location. It reports finite potential, packet and port inequalities and numerical D.3 conditions separately. A valid representation may have false theorem conditions. Work figures count selected operations and are not bit-cost or peak-memory measurements; the work limit is cooperative, not an OS resource limit.

`materialize_finite_certificate` bridges the representation to the existing
v26 certificate and v38 finite child engine. It preserves the immutable
conditional-expectation trace, materializes packets under explicit limits,
and requires the existing independent checker to replay the complete trace.
Its `max_work` applies to the implicit precheck; the separate certificate
checker applies its own trace budget. This bridge is intentionally limited
to the explicit checker's domain, including D≤4096; it is not theorem-scale
implicit child evaluation.

For geometric mode generation, `implicit_mode_source` is a direct sparse
adapter. It stores only packets containing at least one edge (at most M),
along with each packet's original symbol pairs and index. The v31 mode checker
reconstructs the deterministic labeling and sparse packet view before
accepting modes. This path does not materialize the D directed classes or
their empty packets. On the current v31 finite reference, actual mode
generation still has small-input limits (at most six wires, L in {2,4}, and
r≤4). Differential tests compare its modes with the explicit constructor
after translating packet IDs. The v31 mode-indexed scalar-child evaluator
also accepts this source directly and checks its result against independent
half-edge enumeration. These children are scalar group contractions; the
path does not construct the manuscript's shrinking packet-tensor children.
The v36 finite Boolean-multilinear packet-coefficient generator also accepts
the sparse source and independently checks the global contraction. The v38
recursive elimination engine still requires its explicit certificate.

The label constructor remains `assign_full_d3_labels`, with its existing
dimension and work caps. Sparse-source verification now replays this
deterministic constructor and compares the full trace, labels, padding, and
active slots; it remains a finite check under those caps, not a proof of the
uniform existence theorem. It uses the *observed* maximum degree when
reporting numerical conditions. No full recursively shrinking child
representation, inter-depth precision orchestration, end-to-end work ledger,
or proof of a subexponential bound is supplied here.
