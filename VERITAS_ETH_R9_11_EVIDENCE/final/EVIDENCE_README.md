# R9.11 portability evidence — partial generalization

Use the co-delivered R9.11 source archive. The new checker fully replays the
unchanged sealed R9.10 certificates in `sealed_r910/235` and `sealed_r910/242`.
The reports retain their old producer identity. No theorem mode is enabled.

From the extracted source checkout:

    PYTHONPATH=src python3 -m veritas.research.parent_child_r910.cli /path/to/evidence/sealed_r910/235/input.json --layout-file /path/to/evidence/sealed_r910/235/layout.json --replay-dir /path/to/evidence/sealed_r910/235 --output-dir /new/external/replay235 --max-seconds 600 --oracle-max-seconds 600 --oracle-max-work 5000000

Replace `235` with `242` to replay the other certificate. Output directories must
be new and external. The fresh R9.11 235-wire producer stream is in `numerical/run`.
Successful connected one-level streams and separate transfer references are in
`coupled_one_level` and `coupled_one_level_no_cache`.

`coupled_core`, `coupled_core_100mb`, `fully_nonconstant_cycle`, `sweep`, and
`sweep_shifted` contain bounded refusals. They do not contain successful parent
answers. The earlier driver snapshots preserve the original script bytes for
those attempts; each plan records its driver hash. The latest driver is in the
source archive. `experiment_summary.json` describes actual partial progress.

`validation_summary.json` records the completed release checks and open gates.
`portable/commands.json` and its logs include clean-wheel and Docker replays of
both sealed certificates. Rebuild the wheel/image from the supplied source to
repeat them; virtual environments and container images are not archived.
Historical absolute paths identify the originating environment.

`candidate_failure` contains the pre-fix source candidate's failed legacy
exception-contract test. Its source identity differs from the final release.
`wrong_interpreter_*` records an initial harness invocation that resolved the
virtual-environment executable to the base Python and could not import the package;
the corrected wheel/Docker invocations are in `additional_portable_summary.json`.
Neither is counted as successful validation.

Timing measurements are shared-host observations. Charged work is not exact bit
cost; interrupted oracle work can be pending outside the global ledger. Working
space, asymptotic bounds, the manuscript-active schedule, arbitrary jet length,
and executable refinement are not established. Hashes check byte consistency,
not author identity or mathematical validity.
