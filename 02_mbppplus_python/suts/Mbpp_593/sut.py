"""
Write a function to remove leading zeroes from an ip address.
assert removezero_ip("216.08.094.196")==('216.8.94.196')
"""

import re
def removezero_ip(ip):
 return re.sub('\.[0]*', '.', ip)
