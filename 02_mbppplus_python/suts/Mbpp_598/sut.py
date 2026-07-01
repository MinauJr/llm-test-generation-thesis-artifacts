"""
Write a function to check whether the given number is armstrong or not.
assert armstrong_number(153)==True
"""

def armstrong_number(number):
    order = len(str(number))
    return sum([int(i) ** order for i in str(number)]) == number
