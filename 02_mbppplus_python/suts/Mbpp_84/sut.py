"""
Write a function to find the nth number in the newman conway sequence.
assert sequence(10) == 6
"""

def sequence(n): 
	if n == 1 or n == 2: 
		return 1
	seq = [0] * (n + 1)
	seq[1] = seq[2] = 1
	for i in range(3, n + 1):
		seq[i] = seq[seq[i - 1]] + seq[i - seq[i - 1]]
	return seq[n]
