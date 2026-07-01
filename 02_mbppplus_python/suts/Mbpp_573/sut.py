"""
Write a python function to calculate the product of the unique numbers in a given list.
assert unique_product([10, 20, 30, 40, 20, 50, 60, 40]) ==  720000000
"""

def unique_product(list_data):
    from functools import reduce
    return reduce(lambda x, y: x*y, set(list_data))
