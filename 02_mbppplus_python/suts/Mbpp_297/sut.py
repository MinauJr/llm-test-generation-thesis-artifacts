"""
Write a function to flatten a given nested list structure.
assert flatten_list([0, 10, [20, 30], 40, 50, [60, 70, 80], [90, 100, 110, 120]])==[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120]
"""

def flatten_list(list1):
	result = []
	for item in list1:
		if isinstance(item, list):
			result.extend(flatten_list(item))
		else:
			result.append(item)
	return result
