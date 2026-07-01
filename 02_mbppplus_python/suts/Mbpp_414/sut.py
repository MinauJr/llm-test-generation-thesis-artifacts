"""
Write a python function to check whether any value in a sequence exists in a sequence or not.
assert overlapping([1,2,3,4,5],[6,7,8,9]) == False
"""

def overlapping(list1,list2):  
    return any(v in list2 for v in list1)
