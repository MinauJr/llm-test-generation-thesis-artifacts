"""
Write a python function takes in an integer and check whether the frequency of each digit in the integer is less than or equal to the digit itself.
assert validate(1234) == True
"""

def validate(n): 
    digits = [int(digit) for digit in str(n)]
    return all(digit >= digits.count(digit) for digit in digits)
