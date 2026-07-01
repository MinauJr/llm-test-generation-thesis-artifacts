from heapq import heappush, heappop

_MAX_VISITS = 1000
_MAX_SUCCESSORS = 100


def _normalise_nodes(value):
    if isinstance(value, (list, tuple, set)):
        return list(value)[:_MAX_SUCCESSORS]
    return []


class Node:
    def __init__(self, successors=None, label=None):
        self.successors = _normalise_nodes(successors)
        self.label = label

    def __lt__(self, other):
        return id(self) < id(other)


def _safe_successors(node):
    return _normalise_nodes(getattr(node, "successors", []))


def _edge_length(length_by_edge, node, nextnode):
    if not isinstance(length_by_edge, dict):
        return None

    candidates = [
        (node, nextnode),
        (id(node), id(nextnode)),
        (getattr(node, "label", None), getattr(nextnode, "label", None)),
    ]

    for key in candidates:
        if key in length_by_edge:
            try:
                value = float(length_by_edge[key])
            except Exception:
                return None
            return value if value >= 0 else None

    return None


def shortest_path_length(length_by_edge, startnode, goalnode):
    if startnode is goalnode:
        return 0.0

    if not isinstance(length_by_edge, dict):
        return float("inf")

    if not hasattr(startnode, "successors") or not hasattr(goalnode, "successors"):
        return float("inf")

    heap = [(0.0, 0, id(startnode), startnode)]
    best = {id(startnode): 0.0}
    visited = set()
    visits = 0

    while heap and visits < _MAX_VISITS:
        dist, order, node_id, node = heappop(heap)

        if node_id in visited:
            continue

        visited.add(node_id)
        visits += 1

        if node is goalnode:
            return dist

        for index, nextnode in enumerate(_safe_successors(node)):
            next_id = id(nextnode)

            if next_id in visited:
                continue

            edge = _edge_length(length_by_edge, node, nextnode)
            if edge is None:
                continue

            candidate = dist + edge
            if candidate < best.get(next_id, float("inf")):
                best[next_id] = candidate
                heappush(heap, (candidate, order + index + 1, next_id, nextnode))

    return float("inf")
