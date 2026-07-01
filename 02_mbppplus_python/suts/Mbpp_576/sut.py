"""
Write a python function to check whether a list is sublist of another or not.
assert is_Sub_Array([1,4,3,5],[1,2]) == False
"""

def is_Sub_Array(A,B): 
    a = 0
    b = 0
    while a < len(A) and b < len(B):
        if A[a] == B[b]:
            a += 1
            b += 1
        else:
            a += 1
    return b == len(B)
