"""
Write a function to calculate whether the matrix is a magic square.
assert magic_square_test([[7, 12, 1, 14], [2, 13, 8, 11], [16, 3, 10, 5], [9, 6, 15, 4]])==True
"""

def magic_square_test(my_matrix):
    s = sum(my_matrix[0])
    # row
    if any(sum(row) != s for row in my_matrix):
        return False
    # column
    if any(sum(row[i] for row in my_matrix) != s for i in range(len(my_matrix[0]))):
        return False
    # diagonal
    if sum(my_matrix[i][i] for i in range(len(my_matrix))) != s:
        return False
    # anti-diagonal
    if sum(my_matrix[i][len(my_matrix) - i - 1] for i in range(len(my_matrix))) != s:
        return False
    return True
