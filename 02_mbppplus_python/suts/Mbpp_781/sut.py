"""
Write a python function to check whether the count of divisors is even. 
assert count_divisors(10)
"""

import math 
def count_divisors(n) : 
    cnt = 0
    for i in range(1, (int)(math.sqrt(n)) + 1) : 
        if (n % i == 0) : 
            if (n / i == i) : 
                cnt = cnt + 1
            else : 
                cnt = cnt + 2
    return cnt % 2 == 0
