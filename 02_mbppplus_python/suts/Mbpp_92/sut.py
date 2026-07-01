"""
Write a function to check whether the given number is undulating or not.
assert is_undulating(1212121) == True
"""

def is_undulating(n): 
	digits = [int(digit) for digit in str(n)]
	if len(set(digits)) != 2:
		return False
	return all(a != b for a, b in zip(digits, digits[1:]))
