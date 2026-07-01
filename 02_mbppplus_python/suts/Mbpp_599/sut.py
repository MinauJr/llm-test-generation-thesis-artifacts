"""
Write a function to find sum and average of first n natural numbers.
assert sum_average(10)==(55, 5.5)
"""

def sum_average(number):
   sum_ = sum(range(1, number+1))
   average = sum_/number
   return sum_, average
