"""
Write a python function to count the number of equal numbers from three given integers.
assert test_three_equal(1,1,1) == 3
"""

def test_three_equal(x,y,z):
  result = set([x,y,z])
  if len(result) == 3:
    return 0
  elif len(result) == 2:
    return 2
  else:
    return 3
