"""
Write a function that takes in a list and an element and inserts the element before each element in the list, and returns the resulting list.
assert insert_element(['Red', 'Green', 'Black'] ,'c')==['c', 'Red', 'c', 'Green', 'c', 'Black']
"""

def insert_element(list1, element):
    list1 = [v for elt in list1 for v in (element, elt)]
    return list1
