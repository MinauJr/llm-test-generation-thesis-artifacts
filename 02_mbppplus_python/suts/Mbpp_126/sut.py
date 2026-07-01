"""
Write a python function to find the sum of common divisors of two given numbers.
assert sum(10,15) == 6
"""

import math
def sum(a,b): 
    sum = 0
    n = math.gcd(a, b)
    N = int(math.sqrt(n)) + 1
    for i in range (1, N): 
        if (n % i == 0): 
            sum += i
            if (n / i != i): 
                sum += (n / i)
    return sum
