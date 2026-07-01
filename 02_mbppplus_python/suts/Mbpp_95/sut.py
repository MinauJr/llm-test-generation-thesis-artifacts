"""
Write a python function to find the length of the smallest list in a list of lists.
assert Find_Min_Length([[1],[1,2]]) == 1
"""

def Find_Min_Length(lst):  
    minLength = min(len(x) for x in lst )
    return minLength 
