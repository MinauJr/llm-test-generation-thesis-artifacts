"""
Write a python function to count the occurence of all elements of list in a tuple.
assert count_Occurrence(('a', 'a', 'c', 'b', 'd'),['a', 'b'] ) == 3
"""

from collections import Counter 
def count_Occurrence(tup, lst): 
    return sum(tup.count(ele) for ele in lst)
