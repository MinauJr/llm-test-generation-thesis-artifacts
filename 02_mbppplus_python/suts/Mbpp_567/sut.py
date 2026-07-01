"""
Write a function to check whether a specified list is sorted or not.
assert issort_list([1,2,4,6,8,10,12,14,16,17])==True
"""

def issort_list(list1):
    return all(a <= b for a, b in zip(list1, list1[1:]))
