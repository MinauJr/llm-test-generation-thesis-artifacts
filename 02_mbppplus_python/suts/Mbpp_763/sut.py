"""
Write a python function to find the minimum difference between any two elements in a given array. 
assert find_min_diff((1,5,3,19,18,25),6) == 1
"""

def find_min_diff(arr,n): 
    arr = sorted(arr) 
    diff = 10**20 
    for i in range(n-1): 
        if arr[i+1] - arr[i] < diff: 
            diff = arr[i+1] - arr[i]  
    return diff 
