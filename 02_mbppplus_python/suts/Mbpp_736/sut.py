"""
Write a function to locate the left insertion point for a specified value in sorted order. 
assert left_insertion([1,2,4,5],6)==4
"""

import bisect
def left_insertion(a, x):
    return bisect.bisect_left(a, x)
