"""
Write a function to count number items that are identical in the same position of three given lists.
assert count_samepair([1,2,3,4,5,6,7,8],[2,2,3,1,2,6,7,9],[2,1,3,1,2,6,7,9])==3
"""

def count_samepair(list1,list2,list3):
    return sum(m == n == o for m, n, o in zip(list1,list2,list3))
