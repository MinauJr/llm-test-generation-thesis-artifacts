"""
Write a python function that returns the number of integer elements in a given list.
assert count_integer([1,2,'abc',1.2]) == 2
"""

def count_integer(list1):
    return sum(isinstance(x, int) for x in list1)
