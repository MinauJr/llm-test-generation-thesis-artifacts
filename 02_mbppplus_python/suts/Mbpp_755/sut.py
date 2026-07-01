"""
Write a function to find the second smallest number in a list.
assert second_smallest([1, 2, -8, -2, 0, -2])==-2
"""

def second_smallest(numbers):
  sorted_set = sorted(set(numbers))
  if len(sorted_set) < 2:
    return None
  return sorted_set[1]
