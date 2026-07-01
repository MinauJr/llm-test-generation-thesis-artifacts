"""
Write a python function to set all even bits of a given number.
assert even_bit_set_number(10) == 10
"""

def even_bit_set_number(n): 
    mask = 2
    while mask < n:
        n |= mask
        mask <<= 2
    return n
