"""
Write a function to find the n'th star number.
assert find_star_num(3) == 37
"""

def find_star_num(n): 
	return 6 * n * (n - 1) + 1 
