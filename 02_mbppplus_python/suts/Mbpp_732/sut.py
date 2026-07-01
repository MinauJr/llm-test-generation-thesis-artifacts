"""
Write a function to replace all occurrences of spaces, commas, or dots with a colon.
assert replace_specialchar('Python language, Programming language.')==('Python:language::Programming:language:')
"""

import re
def replace_specialchar(text):
 return re.sub("[ ,.]", ":", text)
