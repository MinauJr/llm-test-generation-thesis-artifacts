"""
Write a function to find whether a given array of integers contains any duplicate element.
assert test_duplicate(([1,2,3,4,5]))==False
"""

def test_duplicate(arraynums):
    return len(arraynums) != len(set(arraynums))
