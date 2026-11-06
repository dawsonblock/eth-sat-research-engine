"""Rejection-only scalar oracle; never imported by the point executor."""
from fractions import Fraction
from math import prod
from pathlib import Path
import json
p=149;q=1<<p;T=20;L=8
cprime=prod(-i for i in range(-L,L) if i)
def W(x,y):
 z=Fraction(prod(T-i for i in range(-L,L) if i!=y-x),cprime)
 assert z.denominator%2
 return z.numerator*pow(z.denominator,-1,q)%q
w00,w02,w20,w22=W(0,0),W(0,2),W(2,0),W(2,2)
value=((4+10*(1+2*w02)*(1+2*w22)+10*(1+2*w00)*(1+2*w20)+25*(1+2*(w00+w02))*(1+2*(w20+w22)))*(7+10*w00))%q
pfile=Path('general_full_point.json')
verified=False
if pfile.exists():
 point=json.loads(pfile.read_text())
 if point['status'].startswith('PASS'):
  assert point['result']==[[value,0,0,0]]
  verified=True
Path('full_point_scalar_oracle.json').write_text(json.dumps({'oracle_value':value,'point_precision':p,'point_T':T,'production_comparison_passed':verified,'oracle_only':True,'source_qualified':False},indent=2)+'\n')
print('scalar oracle',value,'production comparison',verified)
