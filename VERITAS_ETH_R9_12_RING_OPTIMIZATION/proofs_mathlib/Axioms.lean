import ModeCount

#print axioms ModeCount.mem_enum
#print axioms ModeCount.nodup_enum
#print axioms ModeCount.length_enum_le_product
#print axioms ModeCount.length_enum_le
#print axioms ModeCount.mode_multiplicity
#print axioms ModeCount.paper_tuple_count
#print axioms ModeCount.cost_le
#print axioms ModeCount.paper_enumeration_cost
#print axioms ModeCount.sum_labelings_load_sq
#print axioms ModeCount.exists_labeling
#print axioms ModeCount.packet_count
#print axioms ModeCount.path_precision
#print axioms ModeCount.precision_bound
#print axioms ModeCount.active_node_bounds
#print axioms ModeCount.geometric_mode_expansion
#print axioms ModeCount.WDiv.mul
#print axioms ModeCount.WDiv.affine_product
#print axioms ModeCount.eq_budget_add
#print axioms ModeCount.eval_eq_budget_sum
#print axioms ModeCount.budget_iff_enum
#print axioms ModeCount.crossing_not_dvd
#print axioms ModeCount.odd_choose_two_pow_sub_one
#print axioms ModeCount.factorization_prodAbs_eq
#print axioms ModeCount.first_fraction
#print axioms ModeCount.ratio_even
#print axioms ModeCount.crossing_entry_expansion
#print axioms ModeCount.oddUnits_zmod
#print axioms ModeCount.depth_bound
#print axioms ModeCount.schedule_bound
#print axioms ModeCount.size_conditions
#print axioms ModeCount.scheduled_precision_bound
#print axioms ModeCount.child_edges
#print axioms ModeCount.child_edges_le_eighth
#print axioms ModeCount.CallTree.size_le
#print axioms ModeCount.depth_exponent
#print axioms ModeCount.path_edges
#print axioms ModeCount.total_calls

example : ModeCount.enum [1, 2] 4 = [[0, 0], [0, 1], [1, 0], [1, 1], [2, 0], [3, 0]] := by decide
