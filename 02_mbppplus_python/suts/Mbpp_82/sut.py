"""
Write a function to find the volume of a sphere.
assert math.isclose(volume_sphere(10), 4188.790204786391, rel_tol=0.001)
"""

import math
def volume_sphere(r):
  return (4./3.) * math.pi * (r**3)
