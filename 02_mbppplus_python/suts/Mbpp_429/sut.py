"""
Write a function to extract the elementwise and tuples from the given two tuples.
assert and_tuples((10, 4, 6, 9), (5, 2, 3, 3)) == (0, 0, 2, 1)
"""

def and_tuples(test_tup1, test_tup2):
  return tuple(x & y for x, y in zip(test_tup1, test_tup2))
