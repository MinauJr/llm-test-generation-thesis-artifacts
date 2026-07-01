"""
Write a function to find the ratio of zeroes to non-zeroes in an array of integers.
assert math.isclose(zero_count([0, 1, 2, -1, -5, 6, 0, -3, -2, 3, 4, 6, 8]), 0.181818, rel_tol=0.001)
"""

def zero_count(nums):
    if all(x == 0 for x in nums):
        return float('inf')
    return sum(x == 0 for x in nums) / sum(x != 0 for x in nums)
