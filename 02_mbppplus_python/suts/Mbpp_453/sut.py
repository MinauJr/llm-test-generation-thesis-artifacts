"""
Write a python function to find the sum of even factors of a number.
assert sumofFactors(18) == 26
"""

import math 
def sumofFactors(n) : 
    if (n % 2 != 0) : 
        return 0
    return sum([i for i in range(2, n + 1) if n % i == 0 and i % 2 == 0])
