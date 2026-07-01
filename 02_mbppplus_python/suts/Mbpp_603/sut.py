"""
Write a function to get all lucid numbers smaller than or equal to a given integer.
assert get_ludic(10) == [1, 2, 3, 5, 7]
"""

def get_ludic(n):
	ludics = []
	for i in range(1, n + 1):
		ludics.append(i)
	index = 1
	while(index != len(ludics)):
		first_ludic = ludics[index]
		remove_index = index + first_ludic
		while(remove_index < len(ludics)):
			ludics.remove(ludics[remove_index])
			remove_index = remove_index + first_ludic - 1
		index += 1
	return ludics
