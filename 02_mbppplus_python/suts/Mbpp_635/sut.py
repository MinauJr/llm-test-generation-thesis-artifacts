"""
Write a function to sort the given list.
assert heap_sort([1, 3, 5, 7, 9, 2, 4, 6, 8, 0])==[0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
"""

import heapq as hq
def heap_sort(iterable):
    hq.heapify(iterable)
    return [hq.heappop(iterable) for _ in range(len(iterable))]
