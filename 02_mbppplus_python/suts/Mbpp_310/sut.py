"""
Write a function to convert a given string to a tuple of characters.
assert string_to_tuple("python 3.0")==('p', 'y', 't', 'h', 'o', 'n', '3', '.', '0')
"""

def string_to_tuple(str1):
    result = tuple(x for x in str1 if not x.isspace()) 
    return result
