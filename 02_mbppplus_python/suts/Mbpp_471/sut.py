"""
Write a python function to find the product of the array multiplication modulo n.
assert find_remainder([ 100, 10, 5, 25, 35, 14 ],11) ==9
"""

def find_remainder(arr, n): 
    from functools import reduce
    return reduce(lambda x, y: x * y, arr) % n
