from collections import deque

_MAX_VISITS = 1000
_MAX_SUCCESSORS = 100


def _normalise_nodes(value):
    if isinstance(value, (list, tuple, set)):
        return list(value)[:_MAX_SUCCESSORS]
    return []


class Node:
    def __init__(self, successors=None):
        self.successors = _normalise_nodes(successors)


def breadth_first_search(startnode, goalnode):
    if startnode is goalnode:
        return True

    if not hasattr(startnode, "successors"):
        return False

    queue = deque([startnode])
    seen = {id(startnode)}
    visits = 0

    while queue and visits < _MAX_VISITS:
        node = queue.popleft()
        visits += 1

        if node is goalnode:
            return True

        for successor in _normalise_nodes(getattr(node, "successors", [])):
            sid = id(successor)
            if sid not in seen:
                seen.add(sid)
                queue.append(successor)

    return False
