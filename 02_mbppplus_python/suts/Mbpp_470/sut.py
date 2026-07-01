"""
Write a function to find the pairwise addition of the neighboring elements of the given tuple.
assert add_pairwise((1, 5, 7, 8, 10)) == (6, 12, 15, 18)
"""

def add_pairwise(test_tup):
  return tuple(a + b for a, b in zip(test_tup, test_tup[1:]))
