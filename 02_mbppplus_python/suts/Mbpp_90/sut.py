"""
Write a python function to find the length of the longest word.
assert len_log(["python","PHP","bigdata"]) == 7
"""

def len_log(list1):
    return max(len(x) for x in list1)
