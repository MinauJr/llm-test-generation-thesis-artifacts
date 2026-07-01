"""
Write a python function to count the number of non-empty substrings of a given string.
assert number_of_substrings("abc") == 6
"""

def number_of_substrings(str1): 
	str_len = len(str1) 
	return str_len * (str_len + 1) // 2
