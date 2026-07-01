"""
Write a function to check whether a list contains the given sublist or not.
assert is_sublist([2,4,3,5,7],[3,7])==False
"""

def is_sublist(l, s):
	if len(l) < len(s):
		return False
	return any(l[i:i+len(s)] == s for i in range(len(l)-len(s)+1))
