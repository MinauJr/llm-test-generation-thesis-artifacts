"""
Write a function to find the largest sum of a contiguous array in the modified array which is formed by repeating the given array k times.
assert max_sub_array_sum_repeated([10, 20, -30, -1], 4, 3) == 30
"""

def max_sub_array_sum_repeated(a, n, k): 
	modifed = a * k
	pre = 0	# dp[i-1]
	res = modifed[0]
	for n in modifed:
		pre = max(pre + n, n)
		res = max(pre, res)
	return res
