"""
Write a function to remove tuples from the given tuple.
assert remove_nested((1, 5, 7, (4, 6), 10)) == (1, 5, 7, 10)
"""

def remove_nested(test_tup):
  return tuple(e for e in test_tup if not isinstance(e, tuple))
