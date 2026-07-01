"""
Write a python function to find the next perfect square greater than a given number.
assert next_Perfect_Square(35) == 36
"""

import math  
def next_Perfect_Square(N): 
    if N < 0:
        return 0
    nextN = math.floor(math.sqrt(N)) + 1
    return nextN * nextN 
