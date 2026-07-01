"""
Write a function to check if a string is present as a substring in a given list of string values.
assert find_substring(["red", "black", "white", "green", "orange"],"ack")==True
"""

def find_substring(str1, sub_str):
   return any(sub_str in s for s in str1)
