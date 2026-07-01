"""
Write a function to move all the numbers to the end of the given string.
assert move_num('I1love143you55three3000thousand') == 'Iloveyouthreethousand1143553000'
"""

def move_num(test_str):
  num_str = ''.join(i for i in test_str if i.isdigit())
  else_str = ''.join(i for i in test_str if not i.isdigit())
  return else_str + num_str
