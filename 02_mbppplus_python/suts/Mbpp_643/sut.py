"""
Write a function that checks if a strings contains 'z', except at the start and end of the word.
assert text_match_wordz_middle("pythonzabc.")==True
"""

import re
def text_match_wordz_middle(text):
	return re.search(r'\Bz\B',  text) is not None
