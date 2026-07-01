"""
Write a function to search a string for a regex pattern. The function should return the matching subtring, a start index and an end index.
assert find_literals('The quick brown fox jumps over the lazy dog.', 'fox') == ('fox', 16, 19)
"""

import re
def find_literals(text, pattern):
  match = re.search(pattern, text)
  if match is None:
    return None
  s = match.start()
  e = match.end()
  return (match.re.pattern, s, e)
