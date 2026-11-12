"""CLI for offline local reasoning and smoke demos."""
import argparse
import json
from pathlib import Path
from veritas.core.cnf import CNF
from veritas.core.logic import entailment_query
from veritas.solvers.reference import solve
from veritas.solvers.certificates import make_unsat_certificate, check_unsat_certificate
from veritas.solvers.projected import projected_count
from veritas.solvers.count_certificates import make_count_certificate, check_count_certificate
from veritas.research.violation_polynomial import eliminate_violation_polynomial
from veritas.research.tensor import from_cnf, eliminate
from veritas.research.wire_deformation import deform_polynomial, independent_defect_histogram, check_deformation_invariants
from veritas.research.cauchy_deformation import exact_cauchy_deformation, verify_cauchy_small, shifted_cauchy_jet_mod
from veritas.research.cauchy_modes import cauchy_modes_at_node
from veritas.research.hermite_ring import hermite_plan, reconstruct_mod
from veritas.research.grouped_cauchy import grouped_cauchy_jet_mod
from veritas.research.recursive_separator import recursive_contract
from veritas.research.packet_schedule import plan_packets, relabel_network
from veritas.research.optimal_packets import optimize_packets_exact
from veritas.research.scalable_packets import optimize_packets_scalable
from veritas.research.matching_packets import optimize_packets_matching
from veritas.research.bounded_partition import optimize_packets_bounded
from veritas.research.bounded_partition_checker import verify_bounded_partition
from veritas.research.packet_bound_checker import check_packet_search_evidence
from veritas.research.cauchy_elimination import eliminate_cauchy_jet


def main():
    parser = argparse.ArgumentParser(description="VERITAS-ETH local reasoning")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("cnf", help="Solve or count a DIMACS file")
    run.add_argument("path", type=Path)
    run.add_argument("--count", action="store_true")
    run.add_argument("--certify-unsat", action="store_true", help="Produce independently checked bounded UNSAT tree")
    run.add_argument("--project", nargs="*", type=int, help="Exact existential counting on listed variables")
    run.add_argument("--tensor", action="store_true")
    run.add_argument("--adaptive-contract", action="store_true", help="v1.7 exact contraction with optional globally optimal small-instance order")
    run.add_argument("--structure-hybrid-count", action="store_true",
                     help="Exact #SAT via disjoint component product with hybrid routing per component")
    run.add_argument("--structure-no-preprocess", action="store_true",
                     help="Disable count-preserving unit propagation before structure routing")
    run.add_argument("--xor-equations", type=Path, metavar="JSON",
                     help="Optional GF(2) XOR equations [{'variables':[...],'rhs':0|1}, ...]")
    run.add_argument("--max-xor-enum-bits", type=int, default=18,
                     help="Cap on GF(2) free bits when conditioning mixed CNF+XOR (default 18)")
    run.add_argument("--xor-strategy", choices=("auto", "substitute", "condition"), default="auto",
                     help="Mixed XOR routing: algebraic substitution vs null-space conditioning")
    run.add_argument("--compare-count-baselines", action="store_true",
                     help="With --structure-hybrid-count, cross-check against exhaustive / optional Ganak")
    run.add_argument("--optimal-order-report", action="store_true", help="v1.7 globally optimal small-instance elimination plan (no count)")
    run.add_argument("--optimal-objective", choices=('work','width'), default='work')
    run.add_argument("--adaptive-portfolio", choices=('auto','thorough','optimal_small'), default='auto')
    run.add_argument("--adaptive-execution", choices=('indexed','legacy','sparse'), default='indexed')
    run.add_argument("--adaptive-no-copy3", action="store_true")
    run.add_argument("--adaptive-no-separators", action="store_true")
    run.add_argument("--adaptive-table-cap", type=int, default=65536)
    run.add_argument("--adaptive-max-slices", type=int, default=3)
    run.add_argument("--bounded-degree", action="store_true", help="Count-preserving constant-degree COPY3 tensor gadget")
    run.add_argument("--gadget-contract", action="store_true", help="Contract bounded-degree gadget exactly using min-neighbor elimination")
    run.add_argument("--max-gadget-wires", type=int, default=5000, help="Hard cap on gadget network wires")
    run.add_argument("--max-work-assignments", type=int, default=2000000, help="Exact contraction evaluation budget")
    run.add_argument("--certify-count", action="store_true", help="Emit complete independently checkable exact-count tree")
    run.add_argument("--certify-count-dag", action="store_true", help="v2.2 independent component-DAG #SAT proof")
    run.add_argument("--certify-weighted-dag", type=Path, metavar="WEIGHTS.json", help="v2.3 proof-carrying exact rational weighted count; JSON variable-index weights")
    run.add_argument('--conditional-query', type=Path, metavar='QUERY.cnf', help='v2.3 probability of query CNF given input CNF; requires --weights')
    run.add_argument('--weights', type=Path, metavar='WEIGHTS.json', help='Normalized rational Bernoulli weights for conditional probability')
    run.add_argument('--marginals', action='store_true', help='v2.4 proof-checked all-variable exact posterior marginals; requires --weights')
    run.add_argument("--spectrum", action="store_true", help="Violation-count polynomial, exact or modulo 2^p")
    run.add_argument("--wire-deformation", action="store_true", help="Research split-wire deformation; not ETH Cauchy algorithm")
    run.add_argument("--cauchy-deformation", action="store_true", help="Exact manuscript D.4.3 kernel on tiny networks, exhaustive")
    run.add_argument("--cauchy-modes", action="store_true", help="Valuation-certified tiny local mode expansion")
    run.add_argument("--packet-schedule", action="store_true", help="Finite bounded packet collision optimization, not paper D.3")
    run.add_argument("--optimal-packets", action="store_true", help="v1.8 exact subset-DP minimum packet collision score for <=16 wires")
    run.add_argument("--bounded-packets", action="store_true", help="v2.1 finite packet branch-and-bound with admissible lower bound for packet sizes 1,2,4,8")
    run.add_argument("--max-packet-states", type=int, default=150000)
    run.add_argument("--max-packet-blocks", type=int, default=1000000)
    run.add_argument("--matching-packets", action="store_true", help="v2.0 global pair-packet optimum via minimum-weight matching (requires networkx)")
    run.add_argument("--scalable-packets", action="store_true", help="v1.9 scalable bounded packet search with checkable global lower bound")
    run.add_argument("--packet-search-evaluations", type=int, default=25000)
    run.add_argument("--packet-search-restarts", type=int, default=5)
    run.add_argument("--packet-search-seed", type=int, default=190026)
    run.add_argument("--optimize-packets", action="store_true", help="Permute wires before Cauchy elimination")
    run.add_argument("--packet-optimizer", choices=("legacy","exact_dp","scalable","matching"), default="legacy", help="Packet optimizer used with --optimize-packets")
    run.add_argument("--cauchy-eliminate", action="store_true", help="Exact modular Cauchy jet via polynomial factor elimination")
    run.add_argument("--weighted-children", action="store_true", help="v1.2 exact grouped mode pruning and recursive child-boundary tensor contraction")
    run.add_argument("--weighted-recovery", action="store_true", help="v1.3 end-to-end guarded Hermite reconstruction of #SAT using weighted child jets")
    run.add_argument("--max-boundary-vars", type=int, default=12, help="v1.2 exact child tensor boundary limit")
    run.add_argument("--separator-contract", action="store_true", help="Bounded exact recursive separator contraction, not paper ETH recursion")
    run.add_argument("--cauchy-grouped", action="store_true", help="Exact grouped rational rank decomposition of Cauchy jet")
    run.add_argument("--group-span", type=int, default=1, help="Number of row slots per Cauchy group")
    run.add_argument("--cauchy-hermite", action="store_true", help="Guard-bit certified Hermite reconstruction of tiny Cauchy CNF")
    run.add_argument("--packet-size", type=int, default=2, help="Cauchy packet size 1,2,4,8")
    run.add_argument("--node", type=int, default=0, help="Cauchy shifted 2-adic jet interpolation node")
    run.add_argument("--jet-order", type=int, default=4, help="Cauchy shifted 2-adic jet order")
    run.add_argument("--precision-bits", type=int, default=None, help="Optional coefficient modulus 2^p")
    run.add_argument("--timeout", type=float, default=5.0)
    check = sub.add_parser("check-proof", help="Independently check a DPLL UNSAT certificate against DIMACS")
    check.add_argument("cnf", type=Path)
    check.add_argument("certificate", type=Path)
    checkcount = sub.add_parser("check-count", help="Check a complete Shannon #SAT counting proof")
    checkdag = sub.add_parser("check-count-dag", help="Independently check a component-DAG #SAT certificate")
    checkdag.add_argument("cnf", type=Path)
    checkdag.add_argument("certificate", type=Path)
    checkmarginals = sub.add_parser('check-marginals', help='Replay exact posterior marginal certificate')
    checkmarginals.add_argument('cnf', type=Path)
    checkmarginals.add_argument('weights', type=Path)
    checkmarginals.add_argument('certificate', type=Path)
    checkweighted = sub.add_parser('check-weighted-dag', help='Independently verify weighted count against CNF and weights')
    checkweighted.add_argument('cnf', type=Path)
    checkweighted.add_argument('weights', type=Path)
    checkweighted.add_argument('certificate', type=Path)
    checkcount.add_argument("cnf", type=Path)
    checkcount.add_argument("certificate", type=Path)
    logic = sub.add_parser("entails", help="Check propositional entailment")
    logic.add_argument("--premise", action="append", default=[])
    logic.add_argument("--conclusion", required=True)
    logic.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()
    if args.command == "check-proof":
        cnf = CNF.from_dimacs(args.cnf.read_text(encoding="utf-8"))
        exported = json.loads(args.certificate.read_text(encoding="utf-8"))
        # Accept either a raw refutation object or the output of --certify-unsat.
        certificate = exported.get("certificate", exported) if isinstance(exported, dict) else exported
        valid, explanation, nodes = check_unsat_certificate(cnf, certificate)
        print(json.dumps({"status":"VALID" if valid else "REJECTED", "reason":explanation, "nodes":nodes}, indent=2))
        if not valid:
            raise SystemExit(2)
        return
    if args.command == 'check-marginals':
        from veritas.solvers.marginals import check_marginal_certificate
        cnf = CNF.from_dimacs(args.cnf.read_text(encoding='utf8'))
        weights = json.loads(args.weights.read_text(encoding='utf8'))
        output = json.loads(args.certificate.read_text(encoding='utf8'))
        certificate = output.get('certificate', output) if isinstance(output, dict) else output
        valid, why, status, marginals, nodes = check_marginal_certificate(cnf, weights, certificate)
        print(json.dumps({'status': 'VALID' if valid else 'REJECTED', 'reason': why,
                          'posterior_status': status, 'marginals': marginals, 'nodes': nodes}, indent=2))
        if not valid: raise SystemExit(2)
        return
    if args.command == 'check-weighted-dag':
        from veritas.solvers.weighted_dag import check_weighted_dag_certificate
        cnf = CNF.from_dimacs(args.cnf.read_text(encoding='utf8'))
        weights = json.loads(args.weights.read_text(encoding='utf8'))
        output = json.loads(args.certificate.read_text(encoding='utf8'))
        cert = output.get('certificate', output) if isinstance(output, dict) else output
        valid, reason, count, nodes = check_weighted_dag_certificate(cnf, weights, cert)
        print(json.dumps({'status':'VALID' if valid else 'REJECTED','reason':reason,'count':count,'nodes':nodes}, indent=2))
        if not valid: raise SystemExit(2)
        return
    if args.command == "check-count-dag":
        from veritas.solvers.count_dag import check_dag_count_certificate
        cnf = CNF.from_dimacs(args.cnf.read_text(encoding="utf-8"))
        exported = json.loads(args.certificate.read_text(encoding="utf-8"))
        cert = exported.get("certificate", exported) if isinstance(exported, dict) else exported
        valid, reason, count, nodes = check_dag_count_certificate(cnf, cert)
        print(json.dumps({"status": "VALID" if valid else "REJECTED", "count": str(count) if count is not None else None,
                          "reason": reason, "nodes": nodes}, indent=2))
        if not valid:
            raise SystemExit(2)
        return
    if args.command == "check-count":
        cnf = CNF.from_dimacs(args.cnf.read_text(encoding="utf-8"))
        exported = json.loads(args.certificate.read_text(encoding="utf-8"))
        certificate = exported.get("certificate", exported) if isinstance(exported, dict) else exported
        valid, explanation, count, nodes = check_count_certificate(cnf, certificate)
        print(json.dumps({"status":"VALID" if valid else "REJECTED", "count":str(count) if count is not None else None,
                          "reason":explanation, "nodes":nodes}, indent=2))
        if not valid:
            raise SystemExit(2)
        return
    if args.command == "cnf":
        cnf = CNF.from_dimacs(args.path.read_text(encoding="utf-8"))
        if args.optimal_order_report:
            from dataclasses import asdict
            from time import monotonic
            from veritas.research.contraction_planner import original_cnf_model, ContractLimit, elimination_order
            from veritas.research.optimal_order import optimize_small_model, replay_order
            try:
                model=original_cnf_model(cnf)
                plan, proof=optimize_small_model(model,objective=args.optimal_objective,
                    deadline=monotonic()+args.timeout)
                baseline=elimination_order(model,'min_degree')
                assert replay_order(model,plan.order)==(plan.estimated_assignments,plan.induced_width)
                print(json.dumps({'status':'FINITE_GRAPH_OPTIMAL_ORDER','objective':args.optimal_objective,
                      'plan':asdict(plan),'optimality':asdict(proof),
                      'baseline_min_degree':asdict(baseline),
                      'count':None,'replay_verified':True,
                      'warning':'Optimizes a dense cost proxy, not actual runtime or ETH asymptotics.'},indent=2))
            except (ContractLimit,ValueError) as exc:
                print(json.dumps({'status':'UNKNOWN','reason':str(exc),'count':None}))
                raise SystemExit(2)
            return
        if args.structure_hybrid_count:
            from veritas.research.contraction_planner import ContractLimit
            from veritas.research.cnf_structure import structure_aware_count
            from veritas.research.gf2_xor_count import parse_xor_equations
            xor_eqs = None
            if args.xor_equations is not None:
                xor_eqs = parse_xor_equations(json.loads(args.xor_equations.read_text()), n=cnf.n)
            try:
                output = structure_aware_count(
                    cnf,
                    preprocess=not args.structure_no_preprocess,
                    xor_equations=xor_eqs,
                    max_xor_enum_bits=args.max_xor_enum_bits,
                    xor_strategy=args.xor_strategy,
                    precision_bits=args.precision_bits,
                    include_copy3=not args.adaptive_no_copy3,
                    enable_separators=not args.adaptive_no_separators,
                    max_slices=args.adaptive_max_slices,
                    portfolio_mode=args.adaptive_portfolio,
                    execution_mode=args.adaptive_execution,
                    max_table_entries=args.adaptive_table_cap,
                    max_work_assignments=args.max_work_assignments,
                    timeout_s=args.timeout,
                )
                if args.compare_count_baselines:
                    from veritas.solvers.external_baselines import compare_count_baselines

                    output["baseline_compare"] = compare_count_baselines(
                        cnf,
                        structure_aware_count,
                        timeout_s=args.timeout,
                        preprocess=not args.structure_no_preprocess,
                        xor_equations=xor_eqs,
                        max_xor_enum_bits=args.max_xor_enum_bits,
                    )
                print(json.dumps(output, indent=2))
            except (ContractLimit, ValueError) as exc:
                print(json.dumps({'status': 'UNKNOWN', 'reason': str(exc)}, indent=2))
                raise SystemExit(2)
            return
        if args.adaptive_contract:
            from veritas.research.adaptive_contract import adaptive_count
            from veritas.research.contraction_planner import ContractLimit
            try:
                output=adaptive_count(cnf,
                    precision_bits=args.precision_bits,
                    include_copy3=not args.adaptive_no_copy3,
                    enable_separators=not args.adaptive_no_separators,
                    max_slices=args.adaptive_max_slices,
                portfolio_mode=args.adaptive_portfolio,execution_mode=args.adaptive_execution,
                    max_table_entries=args.adaptive_table_cap,
                    max_work_assignments=args.max_work_assignments,
                    timeout_s=args.timeout)
                print(json.dumps(output,indent=2))
            except (ContractLimit, ValueError) as exc:
                print(json.dumps({'status':'UNKNOWN','reason':str(exc),
                    'warning':'No partial answer is returned.'},indent=2))
                raise SystemExit(2)
            return
        if args.bounded_degree or args.gadget_contract:
            from dataclasses import asdict
            from veritas.research.bounded_degree import bounded_degree_from_cnf
            from veritas.research.minfill_contract import minfill_contract
            net,stat=bounded_degree_from_cnf(cnf,max_wires=args.max_gadget_wires)
            out={'status':'STRUCTURALLY_PARISMONIOUS_TENSOR',
                 'evidence_level':'MATHEMATICAL_CONSTRUCTION_NOT_KERNEL_PROOF',
                 'stats':asdict(stat),'formula_sha256':cnf.digest(),
                 'warning':'Exact COPY3 gadgets and min-neighbor contraction. Not subexponential ETH/D.4.4.'}
            if args.gadget_contract:
                if net.edges > 512 or len(net.factors)>1200:
                    raise ValueError('bounded contraction permits <=512 wires and <=1200 factors')
                result,cs=minfill_contract(net,timeout_s=args.timeout,
                     max_work_assignments=args.max_work_assignments,
                     modulus=(1<<args.precision_bits) if args.precision_bits else None)
                out.update(status='COUNT_RESIDUE' if args.precision_bits else 'EXACT_COUNT',
                           count=str(result), contract_stats=asdict(cs),
                           evidence_level='EXACT_ALGORITHM_NOT_PROOF_CERTIFICATE')
            print(json.dumps(out,indent=2))
            return
        if args.marginals:
            from veritas.solvers.marginals import exact_marginals
            if args.weights is None:
                raise ValueError('--marginals requires --weights')
            weights = json.loads(args.weights.read_text(encoding='utf8'))
            result = exact_marginals(cnf, weights, timeout_s=args.timeout)
            print(json.dumps({'status': result.status, 'evidence_weight': result.evidence_weight,
                              'marginals': result.marginals, 'certificate': result.certificate,
                              'nodes': result.nodes, 'reason': result.reason,
                              'evidence_level': 'WEIGHTED_DAG_AND_MARGINAL_REPLAY_CHECKED' if result.certificate else 'NONE'}, indent=2))
            return
        if args.conditional_query is not None:
            from veritas.solvers.conditional import exact_conditional
            if args.weights is None:
                raise ValueError('--conditional-query requires --weights')
            weights = json.loads(args.weights.read_text(encoding='utf8'))
            query = CNF.from_dimacs(args.conditional_query.read_text(encoding='utf8'))
            result = exact_conditional(cnf, query, weights, timeout_s=args.timeout)
            print(json.dumps({'status':result.status,
                'evidence_level': 'WEIGHTED_COUNT_PROOF_CHECKED' if result.status in ('PROBABILITY','UNDEFINED') else 'NONE',
                'probability':result.probability,'numerator':result.numerator,
                'denominator':result.denominator,'evidence_certificate':result.evidence_certificate,
                'joint_certificate':result.joint_certificate,'reason':result.reason},indent=2))
            return
        if args.certify_weighted_dag is not None:
            from veritas.solvers.weighted_dag import make_weighted_dag_certificate, check_weighted_dag_certificate
            weights = json.loads(args.certify_weighted_dag.read_text(encoding='utf8'))
            result = make_weighted_dag_certificate(cnf, weights, timeout_s=args.timeout)
            valid, reason, count, checked = (check_weighted_dag_certificate(cnf, weights, result.certificate)
                if result.certificate else (False, result.reason, None, 0))
            if result.status == 'WEIGHTED_COUNT' and (not valid or count != result.count):
                raise RuntimeError(f'independent verifier rejected weighted count: {reason}')
            print(json.dumps({'status':result.status,
                'evidence_level':'WEIGHTED_COUNT_PROOF_CHECKED' if valid else 'NONE',
                'count':result.count,'normalized_distribution':result.normalized,
                'nodes':result.nodes,'cache_hits':result.cache_hits,'checked_nodes':checked,
                'certificate':result.certificate,'reason':result.reason}, indent=2))
            return
        if args.certify_count_dag:
            from veritas.solvers.count_dag import make_dag_count_certificate, check_dag_count_certificate
            result = make_dag_count_certificate(cnf, timeout_s=args.timeout)
            valid, reason, counted, checked = (check_dag_count_certificate(cnf, result.certificate)
                                               if result.certificate else (False, 'no certificate', None, 0))
            print(json.dumps({"status": result.status, "count": str(result.count) if result.count is not None else None,
                              "evidence_level": "COUNT_PROOF_CHECKED" if valid and counted == result.count else "NONE",
                              "certificate": result.certificate, "generator_nodes": result.nodes,
                              "checker_nodes": checked, "cache_hits": result.cache_hits, "reason": result.reason,
                              "warning": "Component-DAG proof only; exponential worst case."}, indent=2))
            return
        if args.certify_count:
            result = make_count_certificate(cnf, timeout_s=args.timeout)
            valid, _, checked, _ = check_count_certificate(cnf, result.certificate) if result.certificate else (False, None, None, None)
            print(json.dumps({"status":result.status, "count":str(result.count) if result.count is not None else None,
                              "evidence_level":"COUNT_PROOF_CHECKED" if valid and checked == result.count else "NONE",
                              "certificate":result.certificate, "reason":result.reason}, indent=2))
            return
        if args.weighted_recovery:
            from veritas.research.weighted_recovery import recover_weighted_count, recovery_payload
            if cnf.n>24 or len(cnf.clauses)>18:
                raise ValueError('weighted recovery requires <=24 variables and 18 clauses')
            result=recover_weighted_count(cnf,packet_size=args.packet_size,
                group_span=args.group_span,precision_bits=args.precision_bits,
                max_boundary_vars=args.max_boundary_vars,timeout_s=args.timeout,cross_check=True)
            payload=recovery_payload(result)
            payload.update(status='EXACT_COUNT' if result.exact_count is not None else 'COUNT_RESIDUE',
                evidence_level='RESEARCH_CROSS_CHECKED',
                warning='Finite reference algorithm, exponential in worst case. NOT the paper ETH recurrence.')
            print(json.dumps(payload,indent=2))
            return
        if args.weighted_children:
            from dataclasses import asdict
            from veritas.research.weighted_children import recursive_weighted_jet
            net=from_cnf(cnf,max_degree=8)
            jet,modes,stats=recursive_weighted_jet(net,packet_size=args.packet_size,
                    node=args.node,group_span=args.group_span,precision_bits=args.precision_bits or 12,
                    jet_order=args.jet_order,max_boundary_vars=args.max_boundary_vars,
                    timeout_s=args.timeout)
            independent=None
            if net.edges<=6:
                independent,_=shifted_cauchy_jet_mod(net,packet_size=args.packet_size,
                    node=args.node,precision_bits=args.precision_bits or 12,
                    jet_order=args.jet_order,max_edges=6,timeout_s=args.timeout)
                if jet!=independent:raise AssertionError('child tensor oracle disagreement')
            print(json.dumps({'status':'JET_RESIDUES',
               'evidence_level':'RESEARCH_CROSS_CHECKED' if independent is not None else 'RESEARCH_ONLY',
               'jet_coefficients_mod_2_power':list(map(str,jet)),
               'independent_jet':list(map(str,independent)) if independent is not None else None,
               'stats':asdict(stats),
               'warning':'Bounded generic recursive child tensors, NOT paper D.4.4 subexponential algorithm'},indent=2))
            return
        if args.packet_schedule or args.optimal_packets or args.scalable_packets or args.matching_packets or args.bounded_packets:
            net=from_cnf(cnf,max_degree=12 if (args.scalable_packets or args.matching_packets or args.bounded_packets) else 16)
            bound=None
            bound_check=None
            matching_proof=None
            partition_proof=None
            partition_replay=None
            evidence=None
            if args.bounded_packets:
                plan,partition_proof=optimize_packets_bounded(net,packet_size=args.packet_size,
                    timeout_s=args.timeout,max_states=args.max_packet_states,max_blocks=args.max_packet_blocks)
                valid,partition_replay=verify_bounded_partition(net,plan,partition_proof)
                if not valid:raise AssertionError('bounded partition evidence: '+partition_replay)
            elif args.matching_packets:
                if args.packet_size!=2:raise ValueError('--matching-packets requires --packet-size 2')
                plan,matching_proof=optimize_packets_matching(net)
                evidence=None
            elif args.optimal_packets:
                plan,evidence=optimize_packets_exact(net,packet_size=args.packet_size,timeout_s=args.timeout)
            elif args.scalable_packets:
                plan,bound=optimize_packets_scalable(net,packet_size=args.packet_size,timeout_s=args.timeout,
                    max_evaluations=args.packet_search_evaluations,restarts=args.packet_search_restarts,
                    seed=args.packet_search_seed)
                verified,bound_check=check_packet_search_evidence(net,plan,bound)
                if not verified:raise RuntimeError("independent packet certificate verification failed")
                evidence=None
            else:
                plan=plan_packets(net,packet_size=args.packet_size,timeout_s=args.timeout)
                evidence=None
            print(json.dumps({'status':'FINITE_OPTIMAL_SCHEDULE' if evidence or matching_proof or (partition_proof and partition_proof.finished_search) or (bound and bound.exact_optimum_certified) else 'SCHEDULE',
               'evidence_level':('FINITE_PARTITION_INDEPENDENT_DP' if partition_proof.independent_oracle_checked else 'FINITE_PARTITION_BOUND_CHECKED') if partition_proof else ('FINITE_MATCHING_CROSSCHECKED' if matching_proof.oracle_checked else 'FINITE_MATCHING_ALGORITHM_ONLY') if matching_proof else
                   'FINITE_OPTIMUM_DP_REPLAYED' if evidence else
                   'FINITE_SURROGATE_OPTIMUM_LOWER_BOUND_CHECKED' if bound and bound.exact_optimum_certified else 'RESEARCH_ONLY',
               'method':'BOUNDED_PACKET_BRANCH_AND_BOUND' if partition_proof else 'EXACT_MINIMUM_WEIGHT_MATCHING' if matching_proof else
                   'FINITE_PACKET_SUBSET_DP' if evidence else
                   'SCALABLE_LOWER_BOUND_PACKET_SEARCH' if bound else 'BOUNDED_PACKET_INCIDENCE_OPTIMIZER',
               'stats':vars(plan),'optimality_evidence':vars(evidence) if evidence else None,
               'scalable_lower_bound_evidence':vars(bound) if bound else None,
               'matching_evidence':vars(matching_proof) if matching_proof else None,
               'bounded_partition_evidence':vars(partition_proof) if partition_proof else None,
               'bounded_partition_replay':partition_replay,
               'independent_lower_bound_check':bound_check,
               'warning':'Not the manuscript D.3 packing theorem or subexponential algorithm'},indent=2))
            return
        if args.cauchy_eliminate:
            from dataclasses import asdict
            net=from_cnf(cnf,max_degree=12)
            jet,stats=eliminate_cauchy_jet(net,packet_size=args.packet_size,node=args.node,
                precision_bits=args.precision_bits or 12,jet_order=args.jet_order,
                optimize_packets=args.optimize_packets,packet_optimizer=args.packet_optimizer,timeout_s=args.timeout)
            print(json.dumps({'status':'JET_RESIDUES','evidence_level':'RESEARCH_ONLY',
                  'jet_coefficients_mod_2_power':list(map(str,jet)),'stats':asdict(stats),
                  'warning':'Exact polynomial factor elimination, exponential in induced width; not ETH recursion'},indent=2))
            return
        if args.separator_contract:
            net=from_cnf(cnf,max_degree=14)
            count,stats=recursive_contract(net,modulus=(1<<args.precision_bits) if args.precision_bits else None,
                                         timeout_s=args.timeout)
            print(json.dumps({'status':'COUNT_RESIDUE' if args.precision_bits else 'EXACT_COUNT',
                   'evidence_level':'RESEARCH_ONLY','count':str(count),'stats':vars(stats),
                   'warning':'Exact bounded separator contraction, exponential worst case, NOT paper ETH recursion'},indent=2))
            return
        if args.cauchy_grouped:
            net=from_cnf(cnf,max_degree=6)
            jet,modes,summary=grouped_cauchy_jet_mod(net,packet_size=args.packet_size,node=args.node,
                       group_span=args.group_span,precision_bits=args.precision_bits or 8,
                       jet_order=args.jet_order,timeout_s=args.timeout)
            oracle,_=shifted_cauchy_jet_mod(net,packet_size=args.packet_size,node=args.node,
                        precision_bits=args.precision_bits or 8,jet_order=args.jet_order,timeout_s=args.timeout)
            if jet!=oracle:raise RuntimeError('grouped kernel mismatch')
            print(json.dumps({'status':'JET_RESIDUES','evidence_level':'RESEARCH_CROSS_CHECKED',
                 'coefficients_mod_2_power':list(map(str,jet)),'group_summary':vars(summary),
                 'modes':[{'row_group':m.row_group,'column_group':m.column_group,
                           'coefficient_degree':m.coefficient_degree,'u':list(map(str,m.u)),'v':list(map(str,m.v))}
                          for m in modes],
                 'warning':'Bounded grouped coefficient rank factoring, NOT the paper D.4.4 recursive mode bound'},indent=2))
            return
        if args.cauchy_modes:
            network=from_cnf(cnf,max_degree=6)
            result,modes,stats=cauchy_modes_at_node(network,packet_size=args.packet_size,node=args.node,
                    precision_bits=args.precision_bits or 8,jet_order=args.jet_order,timeout_s=args.timeout)
            check,_=shifted_cauchy_jet_mod(network,packet_size=args.packet_size,node=args.node,
                    precision_bits=args.precision_bits or 8,jet_order=args.jet_order,timeout_s=args.timeout)
            if result!=check: raise RuntimeError("mode decomposition mismatch")
            print(json.dumps({"status":"JET_RESIDUES","evidence_level":"RESEARCH_CROSS_CHECKED",
                  "coefficients_mod_2_power":list(map(str,result)),"modes":[vars(m) for m in modes],
                  "stats":vars(stats),"warning":"Small reference, NOT full paper D.4.4 recursion"},indent=2))
            return
        if args.cauchy_hermite:
            network=from_cnf(cnf,max_degree=6)
            if args.packet_size not in (1,2) or network.edges>4:
                raise ValueError('Hermite reference requires packet_size 1/2 and at most four wires')
            d=network.edges*(2*args.packet_size-1)
            nodes=[t for t in range(-args.packet_size,args.packet_size) if t!=0]
            multiplicity=(d+len(nodes))//len(nodes)
            plan=hermite_plan([(t,multiplicity) for t in nodes],alpha=2*args.packet_size,degree_bound=d)
            bits=(args.precision_bits or 8)+plan.guard_bits
            if bits>256: raise ValueError('guard bits exceed precision budget')
            jets=[shifted_cauchy_jet_mod(network,packet_size=args.packet_size,node=t,
                    precision_bits=bits,jet_order=multiplicity,timeout_s=args.timeout)[0] for t in nodes]
            recovered=reconstruct_mod(plan,jets,precision_bits=args.precision_bits or 8,data_precision_bits=bits)
            print(json.dumps({'status':'COUNT_RESIDUE','recovered':str(recovered),'guard_bits':plan.guard_bits,
                  'input_precision_bits':bits,'warning':'Bounded exact interpolation, NOT ETH recursion'},indent=2))
            return
        if args.cauchy_deformation:
            network = from_cnf(cnf,max_degree=6)
            coefficients,stats = exact_cauchy_deformation(network,packet_size=args.packet_size,timeout_s=args.timeout)
            nodes = verify_cauchy_small(network,coefficients,args.packet_size,timeout_s=args.timeout)
            jet, _ = shifted_cauchy_jet_mod(network,packet_size=args.packet_size,node=args.node,
                    precision_bits=args.precision_bits or 8,jet_order=args.jet_order,timeout_s=args.timeout)
            print(json.dumps({"status":"POLYNOMIAL", "method":"MANUSCRIPT_D4_3_CAUCHY_KERNEL_EXHAUSTIVE_REFERENCE",
                "rational_coefficients":list(map(str,coefficients)),"checked_nodes":nodes,
                "shifted_jet_mod_2_power":list(map(str,jet)),"enumerated_pairs":stats.evaluated_pairs,
                "warning":"Tiny exhaustive kernel reproduction; NO subexponential recursive contraction"},indent=2))
            return
        if args.wire_deformation:
            network = from_cnf(cnf,max_degree=14)
            coeffs, stats = deform_polynomial(network, precision_bits=args.precision_bits, timeout_s=args.timeout)
            rank_one = check_deformation_invariants(network, coeffs, precision_bits=args.precision_bits)
            checked = False
            if network.edges <= 7:
                oracle = independent_defect_histogram(network)
                if args.precision_bits is not None:
                    oracle = [v % (1 << args.precision_bits) for v in oracle]
                if oracle != coeffs:
                    raise RuntimeError('independent split-wire histogram mismatch')
                checked = True
            print(json.dumps({"status":"POLYNOMIAL", "method":"TOY_SPLIT_WIRE_DEFORMATION",
                              "coefficients":list(map(str, coeffs)),
                              "degree_bound":network.edges, "rank_one_nodes":rank_one,
                              "independent_histogram_checked":checked,
                              "precision_bits":args.precision_bits,
                              "max_intermediate_arity":stats.max_intermediate_arity,
                              "warning":"Not the claimed ETH subexponential algorithm"},indent=2))
            return
        if args.spectrum:
            coeffs, stats = eliminate_violation_polynomial(cnf,precision_bits=args.precision_bits,timeout_s=args.timeout)
            print(json.dumps({"status":"POLYNOMIAL", "coefficients":list(map(str,coeffs)),
                              "precision_bits":args.precision_bits, "v2_zero_pairs":stats.v2_zero_pairs_elided},indent=2))
            return
        if args.tensor:
            print(json.dumps({"method": "generic_tensor_bucket_elimination", "count": str(eliminate(from_cnf(cnf)))}))
            return
        if args.certify_unsat:
            result = make_unsat_certificate(cnf, timeout_s=args.timeout)
            check = check_unsat_certificate(cnf, result.certificate) if result.certificate else None
            print(json.dumps({"status": result.status,
                              "evidence_level": "PROOF_CHECKED" if check and check[0] else "WITNESS_CHECKED" if result.status == "SAT" else "NONE",
                              "model": result.model, "certificate": result.certificate,
                              "certificate_check": check, "reason": result.reason}, indent=2))
            return
        if args.project is not None:
            result = projected_count(cnf, args.project, timeout_s=args.timeout)
            print(json.dumps({"status":result.status,"projected":args.project,"count":str(result.count) if result.count is not None else None,"nodes":result.nodes,"reason":result.reason}, indent=2))
            return
        result = solve(cnf, count=args.count, timeout_s=args.timeout)
        print(json.dumps({"status": result.status, "count": str(result.count) if result.count is not None else None,
                          "model": result.model, "nodes": result.nodes, "reason": result.reason}, indent=2))
        return
    cnf, mapping, premises, conclusion = entailment_query(args.premise, args.conclusion)
    result = solve(cnf, timeout_s=args.timeout)
    counterexample = ({name: result.model[idx] for name, idx in mapping.items()} if result.model is not None else None)
    if counterexample is not None and (not all(p.eval(counterexample) for p in premises) or conclusion.eval(counterexample)):
        raise RuntimeError("invalid counterexample returned")
    print(json.dumps({"status": "ENTAILED" if result.status == "UNSAT" else "NOT_ENTAILED" if result.status == "SAT" else "UNKNOWN", "counterexample": counterexample}, indent=2))


if __name__ == "__main__":
    main()
