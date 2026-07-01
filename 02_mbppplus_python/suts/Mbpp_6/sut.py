"""
Write a python function to check whether the two numbers differ at one bit position only or not.
assert differ_At_One_Bit_Pos(13,9) == True
"""

def is_Power_Of_Two(x: int): 
    return x > 0 and (x & (x - 1)) == 0
def differ_At_One_Bit_Pos(a: int,b: int):
    return is_Power_Of_Two(a ^ b)
