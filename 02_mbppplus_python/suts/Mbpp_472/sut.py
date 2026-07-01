"""
Write a python function to check whether the given list contains consecutive numbers or not.
assert check_Consecutive([1,2,3,4,5]) == True
"""

def check_Consecutive(l): 
    return sorted(l) == list(range(min(l),max(l)+1)) 
