"""
Write a function to find the nth newman–shanks–williams prime number.
assert newman_prime(3) == 7
"""

def newman_prime(n): 
	if n == 0 or n == 1: 
		return 1
	a = 1
	b = 1
	c = 1
	for _ in range(2, n + 1):
		c = 2 * b + a
		a = b
		b = c
	return c
