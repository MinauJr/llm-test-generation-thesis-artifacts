"""
Write a function to find the third side of a right angled triangle.
assert otherside_rightangle(7,8)==10.63014581273465
"""

import math
def otherside_rightangle(w,h):
  return math.sqrt(w * w + h * h)
