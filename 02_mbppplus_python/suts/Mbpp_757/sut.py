"""
Write a function to count the pairs of reverse strings in the given string list. 
assert count_reverse_pairs(["julia", "best", "tseb", "for", "ailuj"])== 2
"""

def count_reverse_pairs(test_list):
  return sum(test_list[i+1:].count(s[::-1]) for i, s in enumerate(test_list))
