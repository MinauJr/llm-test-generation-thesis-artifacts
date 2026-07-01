"""
Write a python function to remove the characters which have odd index values of a given string.
assert odd_values_string('abcdef') == 'ace'
"""

def odd_values_string(str1):
    return ''.join(str1[i] for i in range(0, len(str1), 2))
