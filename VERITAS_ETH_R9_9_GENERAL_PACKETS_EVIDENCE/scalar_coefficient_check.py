"""Separate rational scalar check for the explicit two-row general fixture."""
from fractions import Fraction
from math import prod
from pathlib import Path
import json
p=149;modulus=1<<p;T=1+8*(1<<40)
Cprime=prod(-q for q in range(-4,4) if q)
def W(x,y):
    # Cancel T-(y-x) symbolically from the eight-factor Cauchy polynomial.
    value=Fraction(prod(T-q for q in range(-4,4) if q!=y-x),Cprime)
    assert value.denominator%2
    return value.numerator*pow(value.denominator,-1,modulus)%modulus
c0,c2=W(0,0),W(2,0)
expected=[49,140*(c0+c2)%modulus,480*c0*c2%modulus]
report=json.loads(Path('components.json').read_text())
actual=[r['value'][0][0] for r in report['fixed_coefficients']]
assert actual==expected
assert expected[2]!=0
Path('scalar_coefficient_check.json').write_text(json.dumps({'status':'PASS_INDEPENDENT_SCALAR_RATIONAL_COEFFICIENTS','precision':p,'point_T':T,'formulas':['49','140*(W00+W20)','480*W00*W20'],'values':expected,'complete_point_evaluated':False,'source_qualified':False},indent=2)+'\n')
print('PASS: beta 0, 1, 2 against direct rational formulas')
