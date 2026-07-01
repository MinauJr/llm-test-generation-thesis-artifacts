"""
Write a function to find the n largest integers from a given list of numbers, returned in descending order.
assert heap_queue_largest( [25, 35, 22, 85, 14, 65, 75, 22, 58],3)==[85, 75, 65]
"""

import heapq as hq
def heap_queue_largest(nums: list,n: int) -> list:
  largest_nums = hq.nlargest(n, nums)
  return largest_nums
