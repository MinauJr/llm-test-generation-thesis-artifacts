"""
Write a function to check whether the given string is starting with a vowel or not using regex.
assert check_str("annie")
"""

import re 
def check_str(string): 
	regex = '^[aeiouAEIOU][A-Za-z0-9_]*'
	return re.search(regex, string)
