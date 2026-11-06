"""Manuscript Appendix D.3 finite exact implementation, isolated from v2.5."""
from .constructor import construct_d3_packing, d3_preconditions
from .checker import verify_d3_packing
__all__=['construct_d3_packing','verify_d3_packing','d3_preconditions']
