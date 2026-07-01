"""
Write a function to convert polar coordinates to rectangular coordinates.
assert polar_rect(3,4)==((5.0, 0.9272952180016122), (-2+2.4492935982947064e-16j))
"""

import cmath
def polar_rect(x,y):
    cn = cmath.polar(complex(x, y))
    cn1 = cmath.rect(2, cmath.pi)
    return (cn, cn1)
