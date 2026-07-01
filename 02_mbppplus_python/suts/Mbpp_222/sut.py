"""
Write a function to check if all the elements in tuple have same data type or not.
assert check_type((5, 6, 7, 3, 5, 6) ) == True
"""

def check_type(test_tuple):
    return all(isinstance(item, type(test_tuple[0])) for item in test_tuple)
