_MAX_STEPS = 2000


class Node:
    def __init__(self, successor=None):
        self.successor = successor


def _next(node):
    return getattr(node, "successor", None)


def detect_cycle(node):
    slow = node
    fast = node
    steps = 0

    while fast is not None and _next(fast) is not None and steps < _MAX_STEPS:
        slow = _next(slow)
        fast = _next(_next(fast))
        steps += 1

        if slow is fast and slow is not None:
            return True

    return False
