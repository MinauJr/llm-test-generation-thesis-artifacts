"""
Write a python function to check whether every even index contains even numbers of a given list.
assert even_position([3,2,1]) == False
"""

def even_position(nums):
	return all(nums[i]%2==i%2 for i in range(len(nums)))
