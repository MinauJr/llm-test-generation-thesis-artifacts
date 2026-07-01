"""
Write a function to find the depth of a dictionary.
assert dict_depth({'a':1, 'b': {'c': {'d': {}}}})==4
"""

def dict_depth_aux(d):
    if isinstance(d, dict):
        return 1 + (max(map(dict_depth_aux, d.values())) if d else 0)
    return 0
def dict_depth(d):
    return dict_depth_aux(d)
