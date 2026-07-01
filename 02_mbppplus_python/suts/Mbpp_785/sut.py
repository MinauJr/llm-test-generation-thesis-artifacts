"""
Write a function to convert tuple string to integer tuple.
assert tuple_str_int("(7, 8, 9)") == (7, 8, 9)
"""

def tuple_str_int(test_str):
  return tuple(int(num) for num in test_str.replace('(', '').replace(')', '').replace('...', '').split(', '))
