"""
Write a function to count the number of characters in a string that occur at the same position in the string as in the English alphabet (case insensitive).
assert count_char_position("xbcefg") == 2
"""

def count_char_position(str1): 
    return sum(ord(ch.lower()) - ord('a') == i for i, ch in enumerate(str1))
