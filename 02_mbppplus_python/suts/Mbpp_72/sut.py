"""
Write a python function to check whether the given number can be represented as the difference of two squares or not.
assert dif_Square(5) == True
"""

def dif_Square(n): 
    # see https://www.quora.com/Which-numbers-can-be-expressed-as-the-difference-of-two-squares
    return n % 4 != 2
