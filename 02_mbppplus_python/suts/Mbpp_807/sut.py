"""
Write a python function to find the first odd number in a given list of numbers.
assert first_odd([1,3,5]) == 1
"""

def first_odd(nums):
  first_odd = next((el for el in nums if el%2!=0), None)
  return first_odd
