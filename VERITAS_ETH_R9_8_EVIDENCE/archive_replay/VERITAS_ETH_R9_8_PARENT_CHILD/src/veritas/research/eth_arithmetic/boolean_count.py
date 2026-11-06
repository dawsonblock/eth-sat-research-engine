"""Recover an integer #SAT count from an already verified scalar residue."""
from __future__ import annotations


def recover_boolean_count(residue, *, precision, num_variables):
    """Recover a count from its canonical residue modulo 2**precision.

    The caller must establish that the residue is the completed contraction
    of a count-preserving Boolean formula on exactly num_variables declared
    variables. This function only checks the uniqueness and range conditions;
    it neither contracts a network nor verifies that premise.
    """
    if (type(residue) is not int or residue < 0 or
            type(precision) is not int or precision < 1 or
            type(num_variables) is not int or num_variables < 0):
        raise ValueError('nonnegative residue and variable count, and positive precision required')
    if precision <= num_variables:
        raise ValueError('precision must exceed the number of declared variables')
    if residue.bit_length() > precision:
        raise ValueError('residue is not canonical at the supplied precision')
    bits = residue.bit_length()
    if (bits > num_variables + 1 or
            (bits == num_variables + 1 and residue & (residue - 1))):
        raise ValueError('residue exceeds the maximum Boolean model count')
    return residue
