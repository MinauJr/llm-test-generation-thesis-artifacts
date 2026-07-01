"""
Write a python function to check if a given number is one less than twice its reverse.
assert check(70) == False
"""

def check(n):    
    return n == 2 * int(str(n)[::-1]) - 1
