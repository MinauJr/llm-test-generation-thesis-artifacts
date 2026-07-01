"""
Write a function to remove characters from the first string which are present in the second string.
assert remove_dirty_chars("probasscurve", "pros") == 'bacuve'
"""

def remove_dirty_chars(string, second_string): 
	for char in second_string:
		string = string.replace(char, '')
	return string
