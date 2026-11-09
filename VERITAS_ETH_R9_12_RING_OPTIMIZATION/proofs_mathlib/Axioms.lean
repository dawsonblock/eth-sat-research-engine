import ModeCount

#print axioms ModeCount.mem_enum
#print axioms ModeCount.nodup_enum
#print axioms ModeCount.length_enum_le_product
#print axioms ModeCount.length_enum_le
#print axioms ModeCount.mode_multiplicity
#print axioms ModeCount.paper_tuple_count
#print axioms ModeCount.cost_le
#print axioms ModeCount.paper_enumeration_cost

example : ModeCount.enum [1, 2] 4 = [[0, 0], [0, 1], [1, 0], [1, 1], [2, 0], [3, 0]] := by decide
