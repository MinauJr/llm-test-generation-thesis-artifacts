"""
Write a python function to find the minimum number of rotations (greater than 0) required to get the same string.
assert find_Rotations("aaaa") == 1
"""

def find_Rotations(s): 
    n = len(s)
    s += s
    for i in range(1, n + 1):
        if s[i: i + n] == s[0: n]:
            return i
    return n
