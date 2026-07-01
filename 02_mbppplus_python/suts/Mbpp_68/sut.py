"""
Write a python function to check whether the given array is monotonic or not.
assert is_Monotonic([6, 5, 4, 4]) == True
"""

def is_Monotonic(A): 
    return all(a <= b for a, b in zip(A, A[1:])) or all(a >= b for a, b in zip(A, A[1:]))
