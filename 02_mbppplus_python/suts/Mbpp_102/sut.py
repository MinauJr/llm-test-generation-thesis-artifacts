"""
Write a function to convert a snake case string to camel case string.
assert snake_to_camel('python_program')=='PythonProgram'
"""

def snake_to_camel(word):
    return ''.join(x.capitalize() or '_' for x in word.split('_'))
