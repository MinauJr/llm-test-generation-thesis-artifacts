"""
Write a python function to find even numbers from a list of numbers.
assert Split([1,2,3,4,5]) == [2,4]
"""

def Split(l): 
    return [num for num in l if num % 2 == 0]
