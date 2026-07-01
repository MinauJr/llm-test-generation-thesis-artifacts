"""
Write a function to return two words from a list of words starting with letter 'p'.
assert start_withp(["Python PHP", "Java JavaScript", "c c++"])==('Python', 'PHP')
"""

import re
def start_withp(words):
    for w in words:
        m = re.match("(P\w+)\W(P\w+)", w)
        if m:
            return m.groups()
