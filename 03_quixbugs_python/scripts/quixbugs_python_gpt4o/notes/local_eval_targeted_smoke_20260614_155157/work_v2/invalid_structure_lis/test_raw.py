import pytest

def lis_find_longest(arr):
    ends = {}
    length = len(arr)
    for i in range(0, length-2):
        if arr[i] < arr[length - 1]:
            ends[length - 1] = i + 1
            length -= 1
    return length - 1

def lis_find_longest_iterative(arr):
    n = len(arr)
    end = [0]*n
    longest, x = 0, 0
    for i in range (1 , n ):
        if arr[i] > arr[x]:
            longest += 1
            x = i
        elif arr[i] == arr[x] and longest + 1 > end[longest]:
            end[longest] = i
            longest += 1
    return longest

sut.lis_find_longest = lis_find_longest
sut.lis_find_longest_iterative = lis_find_longest_iterative
