"""
Write a function to check whether it follows the sequence given in the patterns array.
assert is_samepatterns(["red","green","green"], ["a", "b", "b"])==True
"""

def is_samepatterns(colors, patterns):    
    if len(colors) != len(patterns):
        return False    
    pattern_color_dict = {pattern: set() for pattern in patterns}
    for color, pattern in zip(colors, patterns):
        pattern_color_dict[pattern].add(color)
    return all(len(pattern_color_dict[pattern]) == 1 for pattern in patterns)
