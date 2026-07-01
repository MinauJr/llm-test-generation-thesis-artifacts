"""
Write a function to remove all the words with k length in the given string.
assert remove_length('The person is most value tet', 3) == 'person is most value'
"""

def remove_length(test_str, K):
  return ' '.join([i for i in test_str.split() if len(i) != K])
