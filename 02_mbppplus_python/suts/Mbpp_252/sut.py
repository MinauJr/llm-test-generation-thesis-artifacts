"""
Write a python function to convert complex numbers to polar coordinates.
assert convert(1) == (1.0, 0.0)
"""

import cmath  
def convert(numbers):    
  return cmath.polar(numbers)  
