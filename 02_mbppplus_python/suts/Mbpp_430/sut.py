"""
Write a function to find the directrix of a parabola.
assert parabola_directrix(5,3,2)==-198
"""

def parabola_directrix(a, b, c): 
  return ((int)(c - ((b * b) + 1) * 4 * a ))
