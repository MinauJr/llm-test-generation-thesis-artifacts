"""
Write a function to locate the right insertion point for a specified value in sorted order.
assert right_insertion([1,2,4,5],6)==4
"""

import bisect
def right_insertion(a, x):
    return bisect.bisect_right(a, x)
