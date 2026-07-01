"""
Write a function that matches a string that has an 'a' followed by anything, ending in 'b'.
assert text_starta_endb("aabbbb")
"""

import re
def text_starta_endb(text):
    patterns = 'a.*?b$'
    return re.search(patterns,  text)
