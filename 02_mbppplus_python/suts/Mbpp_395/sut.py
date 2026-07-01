"""
Write a python function to find the first non-repeated character in a given string.
assert first_non_repeating_character("abcabc") == None
"""

def first_non_repeating_character(str1):
  for ch in str1:
    if str1.count(ch) == 1:
      return ch
  return None
