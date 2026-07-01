"""
Write a function to check whether the product of numbers in a list is even or not.
assert is_product_even([1,2,3])
"""

def is_product_even(arr): 
    return any(x % 2 == 0 for x in arr)
