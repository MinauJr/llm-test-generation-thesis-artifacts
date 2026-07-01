"""
Write a function to find perfect squares between two given numbers.
assert perfect_squares(1,30)==[1, 4, 9, 16, 25]
"""

import math
def perfect_squares(a, b):
    if a > b:
        a, b = b, a
    if b < 0:
        return []
    if a < 0:
        a = 0
    return list(filter(lambda x: math.sqrt(x).is_integer(), range(a, b+1)))
