"""
Write a function to subtract two lists element-wise.
assert sub_list([1, 2, 3],[4,5,6])==[-3,-3,-3]
"""

def sub_list(nums1,nums2):
  return [num1 - num2 for num1, num2 in zip(nums1, nums2)]
