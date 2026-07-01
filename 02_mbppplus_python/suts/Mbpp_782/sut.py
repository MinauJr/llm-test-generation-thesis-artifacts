"""
Write a python function to find the sum of all odd length subarrays. 
assert odd_length_sum([1,2,4]) == 14
"""

def odd_length_sum(arr):
    sum_ = 0
    n = len(arr)
    for i in range(n):
        # arr[i] occurs (i + 1) * (n - i) times in all subarrays
        times = ((i + 1) * (n - i) + 1) // 2
        sum_ += arr[i] * times
    return sum_
