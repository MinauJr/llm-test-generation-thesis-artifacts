"""
Write a python function to find the index of smallest triangular number with n digits. 
assert find_Index(2) == 4
"""

import math 
def find_Index(n): 
    x = math.sqrt(2 * math.pow(10,(n - 1)))
    return round(x)
