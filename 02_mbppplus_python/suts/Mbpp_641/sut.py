"""
Write a function to find the nth nonagonal number.
assert is_nonagonal(10) == 325
"""

def is_nonagonal(n): 
	return int(n * (7 * n - 5) / 2) 
