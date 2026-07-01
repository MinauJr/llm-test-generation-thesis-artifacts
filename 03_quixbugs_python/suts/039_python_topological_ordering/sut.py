_MAX_NODES = 1000


def _normalise_nodes(value):
    if isinstance(value, (list, tuple, set)):
        return list(value)[:_MAX_NODES]
    return []


class Node:
    def __init__(self, incoming_nodes=None, outgoing_nodes=None):
        self.incoming_nodes = _normalise_nodes(incoming_nodes)
        self.outgoing_nodes = _normalise_nodes(outgoing_nodes)

    def __lt__(self, other):
        return id(self) < id(other)


def topological_ordering(nodes):
    if not isinstance(nodes, (list, tuple, set)):
        return []

    remaining = list(nodes)[:_MAX_NODES]
    ordered = []
    ordered_ids = set()
    guard = 0

    while remaining and guard < _MAX_NODES:
        progress = False
        remaining_ids = {id(node) for node in remaining}

        for node in list(remaining):
            incoming = _normalise_nodes(getattr(node, "incoming_nodes", []))
            if all(id(pred) in ordered_ids or id(pred) not in remaining_ids for pred in incoming):
                ordered.append(node)
                ordered_ids.add(id(node))
                remaining.remove(node)
                progress = True

        if not progress:
            break

        guard += 1

    return ordered
