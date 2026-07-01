"""
Write a python function to find the last digit of a given number.
assert last_Digit(123) == 3
"""

def last_Digit(n) :
    if n < 0: 
        n = -n
    return n % 10
