"""
Write a python function to count number of digits in a given string.
assert number_ctr('program2bedone') == 1
"""

def number_ctr(s):
    return sum(c.isdigit() for c in s)
