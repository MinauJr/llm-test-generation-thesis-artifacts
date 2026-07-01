"""
Write a function to find the union of the elements of two given tuples and output them in sorted order.
assert union_elements((3, 4, 5, 6),(5, 7, 4, 10) ) == (3, 4, 5, 6, 7, 10)
"""

def union_elements(test_tup1, test_tup2):
  return tuple(sorted(set(test_tup1 + test_tup2)))
