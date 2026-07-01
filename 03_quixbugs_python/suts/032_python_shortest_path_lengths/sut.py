from collections import defaultdict


def shortest_path_lengths(n, length_by_edge):
    if type(n) is not int or n < 0:
        raise TypeError("n must be a non-negative int")
    if not isinstance(length_by_edge, dict):
        raise TypeError("length_by_edge must be a dict")

    length_by_path = defaultdict(lambda: float("inf"))
    length_by_path.update({(i, i): 0 for i in range(n)})
    length_by_path.update(length_by_edge)

    for k in range(n):
        for i in range(n):
            for j in range(n):
                length_by_path[i, j] = min(
                    length_by_path[i, j],
                    length_by_path[i, k] + length_by_path[k, j]
                )

    return length_by_path
