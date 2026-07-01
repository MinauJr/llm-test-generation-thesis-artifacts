"""
Write a python function to count the number of positive numbers in a list.
assert pos_count([1,-2,3,-4]) == 2
"""

def pos_count(l):
  return len([x for x in l if x > 0])
