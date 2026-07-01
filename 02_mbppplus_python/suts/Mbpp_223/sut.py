"""
Write a function that takes in a sorted array, its length (n), and an element and returns whether the element is the majority element in the given sorted array. (The majority element is the element that occurs more than n/2 times.)
assert is_majority([1, 2, 3, 3, 3, 3, 10], 7, 3) == True
"""

from bisect import bisect_left, bisect_right
def is_majority(arr, n, x):
	if x not in arr:
		return False
	l = bisect_left(arr, x)
	r = bisect_right(arr, x)
	return r - l > n / 2
