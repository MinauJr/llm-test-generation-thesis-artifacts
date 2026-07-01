"""
Write a function to remove all whitespaces from the given string.
assert remove_whitespaces(' Google    Flutter ') == 'GoogleFlutter'
"""

import re
def remove_whitespaces(text1):
  return text1.replace(' ', '')
