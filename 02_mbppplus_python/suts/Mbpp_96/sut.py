"""
Write a python function to find the number of divisors of a given integer.
assert divisor(15) == 4
"""

def divisor(n):
  return sum(1 for i in range(1, n + 1) if n % i == 0)
