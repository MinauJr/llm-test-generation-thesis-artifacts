"""
Write a function to remove lowercase substrings from a given string.
assert remove_lowercase("PYTHon")==('PYTH')
"""

import re
def remove_lowercase(str1):
    return re.sub('[a-z]', '', str1)
