"""
Write a python function to find the area of the largest triangle that can be inscribed in a semicircle with a given radius.
assert triangle_area(-1) == None
"""

def triangle_area(r) :  
    if r < 0 : 
        return None
    return r * r 
