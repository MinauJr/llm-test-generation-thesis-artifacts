"""
Write a python function to toggle bits of the number except the first and the last bit. 
assert toggle_middle_bits(9) == 15
"""

def toggle_middle_bits(n): 
    binary = bin(n)[2:]
    toggled = ''.join(['0' if i == '1' else '1' for i in binary[1:-1]])
    return int(binary[0] + toggled + binary[-1], 2)
