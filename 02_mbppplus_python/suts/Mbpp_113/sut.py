"""
Write a function to check if a string represents an integer or not.
assert check_integer("python")==False
"""

def check_integer(text):
 text = text.strip()
 if len(text) < 1:
    return None
 else:
    if text[0] in '+-':
        text = text[1:]
    return text.isdigit()
