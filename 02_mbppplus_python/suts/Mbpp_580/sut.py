"""
Write a function to remove uneven elements in the nested mixed tuple.
assert extract_even((4, 5, (7, 6, (2, 4)), 6, 8)) == (4, (6, (2, 4)), 6, 8)
"""

def even_ele(test_tuple, ): 
	res = tuple() 
	for ele in test_tuple: 
		if isinstance(ele, tuple): 
			res += (even_ele(ele), ) 
		elif ele % 2 == 0: 
			res += (ele, ) 
	return res 
def extract_even(test_tuple):
	return even_ele(test_tuple)
