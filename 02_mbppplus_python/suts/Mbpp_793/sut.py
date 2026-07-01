"""
Write a python function to find the last position of an element in a sorted array.
assert last([1,2,3],1) == 0
"""

def last(arr,x):
    return len(arr)-arr[::-1].index(x) - 1
