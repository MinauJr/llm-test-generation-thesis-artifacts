"""
Write a python function to check whether a list of numbers contains only one distinct element or not.
assert unique_Element([1,1,1]) == True
"""

def unique_Element(arr):
    return arr.count(arr[0]) == len(arr)
