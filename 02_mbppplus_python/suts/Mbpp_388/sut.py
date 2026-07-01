"""
Write a python function to find the highest power of 2 that is less than or equal to n.
assert highest_Power_of_2(10) == 8
"""

def highest_Power_of_2(n): 
    i = 0
    while ((1 << i) <= n): 
        i += 1
    return (1 << (i - 1))
