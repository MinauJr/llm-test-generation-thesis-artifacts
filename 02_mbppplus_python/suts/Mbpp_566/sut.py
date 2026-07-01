"""
Write a function to get the sum of the digits of a non-negative integer.
assert sum_digits(345)==12
"""

def sum_digits(n):
  return sum(map(int, str(n)))
