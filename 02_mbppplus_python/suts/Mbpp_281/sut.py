"""
Write a python function to check if the elements of a given list are unique or not.
assert all_unique([1,2,3]) == True
"""

def all_unique(test_list):
    return len(test_list) == len(set(test_list))
