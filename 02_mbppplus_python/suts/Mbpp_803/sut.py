"""
Write a function to check whether the given number is a perfect square or not. 
assert not is_perfect_square(10)
"""

def is_perfect_square(n) :
    if n < 0:
        return False
    return n**(1/2) == int(n**(1/2))
