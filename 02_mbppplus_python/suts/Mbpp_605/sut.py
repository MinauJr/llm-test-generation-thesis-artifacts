"""
Write a function to check if the given integer is a prime number.
assert prime_num(13)==True
"""

import math
def prime_num(num):
  if num <= 1:
    return False
  for i in range(2, int(math.sqrt(num)) + 1):
    if num % i == 0:
      return False
  return True
