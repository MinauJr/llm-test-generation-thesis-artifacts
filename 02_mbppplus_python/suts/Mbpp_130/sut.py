"""
Write a function to find the item with maximum frequency in a given list.
assert max_occurrences([2,3,8,4,7,9,8,2,6,5,1,6,1,2,3,2,4,6,9,1,2])==2
"""

from collections import defaultdict
def max_occurrences(nums):
    d = defaultdict(int)
    for n in nums:
        d[n] += 1
    return max(d, key=d.get)
