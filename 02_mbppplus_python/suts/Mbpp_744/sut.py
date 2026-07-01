"""
Write a function to check if the given tuple has any none value or not.
assert check_none((10, 4, 5, 6, None)) == True
"""

def check_none(test_tup):
  return any(ele is None for ele in test_tup)
