"""
Write a function that counts the number of pairs of integers in a list that xor to an even number.
assert find_even_pair([5, 4, 7, 2, 1]) == 4
"""

def find_even_pair(A): 
  if len(A) < 2: 
    return 0
  return sum((a ^ b) % 2 == 0 for i, a in enumerate(A) for b in A[i + 1:])
