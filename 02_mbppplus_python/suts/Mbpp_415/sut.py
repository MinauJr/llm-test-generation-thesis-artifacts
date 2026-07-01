"""
Write a python function to find a pair with highest product from a given array of integers.
assert max_Product([1,2,3,4,7,0,8,4]) == (7,8)
"""

def max_Product(arr): 
    pairs = [(a, b) for a in arr for b in arr if a != b]
    return max(pairs, key=lambda x: x[0] * x[1])
