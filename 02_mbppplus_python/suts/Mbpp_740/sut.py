"""
Write a function to convert the given tuple to a key-value dictionary using adjacent elements. 
assert tuple_to_dict((1, 5, 7, 10, 13, 5)) == {1: 5, 7: 10, 13: 5}
"""

def tuple_to_dict(test_tup):
  return dict(test_tup[idx : idx + 2] for idx in range(0, len(test_tup), 2))
