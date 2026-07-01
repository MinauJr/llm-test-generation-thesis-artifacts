"""
Write a function to find the median of three numbers.
assert median_numbers(25,55,65)==55.0
"""

def median_numbers(a,b,c):
    return sorted([a,b,c])[1]
