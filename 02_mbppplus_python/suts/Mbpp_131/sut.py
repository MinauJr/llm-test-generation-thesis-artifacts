"""
Write a python function to reverse only the vowels of a given string (where y is not a vowel).
assert reverse_vowels("Python") == "Python"
"""

def reverse_vowels(str1):
	is_vowel = lambda x: x in 'aeiouAEIOU'
	pos = [i for i, c in enumerate(str1) if is_vowel(c)]
	return ''.join(c if not is_vowel(c) else str1[pos.pop()] for c in str1)
