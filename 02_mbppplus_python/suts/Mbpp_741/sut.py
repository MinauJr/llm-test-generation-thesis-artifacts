"""
Write a python function to check whether all the characters are same or not.
assert all_Characters_Same("python") == False
"""

def all_Characters_Same(s) :
    return all(ch == s[0] for ch in s[1:])
