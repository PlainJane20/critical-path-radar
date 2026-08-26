"""
Critical Path Method (CPM) — real project-scheduling math, not an LLM
estimate. Forward pass computes the earliest each task can start/finish
given its dependencies; backward pass computes the latest it can start/
finish without delaying the project end date; slack (float) is the gap
between them. Zero-slack tasks are the critical path — the actual
determinant of the project's end date, not just "the biggest" or "the
reddest" ticket.

This is deliberately plain graph algorithms, no LLM in this module at all.
Getting Claude to "estimate" a critical path would be asking a language
model to do arithmetic it has no mechanism to verify — the wrong tool for
a problem with an exact, checkable answer.
"""


class CycleError(Exception):
    """Raised when the dependency graph isn't a DAG — CPM is undefined on a cycle."""
    pass


def _topological_order(nodes: dict, edges: list) -> list:
    """Kahn's algorithm. Raises CycleError if the graph isn't a DAG —
    a real risk with hand-maintained Jira issue links, not a hypothetical."""
    in_degree = {k: 0 for k in nodes}
    successors = {k: [] for k in nodes}
    for src, dst in edges:
        successors[src].append(dst)
        in_degree[dst] += 1

    queue = [k for k, d in in_degree.items() if d == 0]
    order = []
    while queue:
        node = queue.pop(0)
        order.append(node)
        for succ in successors[node]:
            in_degree[succ] -= 1
            if in_degree[succ] == 0:
                queue.append(succ)

    if len(order) != len(nodes):
        remaining = set(nodes) - set(order)
        raise CycleError(f"Dependency graph has a cycle involving: {sorted(remaining)}")

    return order


def compute_critical_path(nodes: dict, edges: list) -> dict:
    """
    nodes: {key: duration_in_days}
    edges: list of (blocker_key, blocked_key) — blocker must finish before
           blocked can start.

    Returns {key: {"ES", "EF", "LS", "LF", "slack", "critical"}}.
    """
    if not nodes:
        return {}

    order = _topological_order(nodes, edges)

    predecessors = {k: [] for k in nodes}
    successors = {k: [] for k in nodes}
    for src, dst in edges:
        successors[src].append(dst)
        predecessors[dst].append(src)

    # Forward pass: earliest start/finish
    es, ef = {}, {}
    for node in order:
        es[node] = max((ef[p] for p in predecessors[node]), default=0)
        ef[node] = es[node] + nodes[node]

    project_duration = max(ef.values())

    # Backward pass: latest start/finish, walking the topological order in reverse
    lf, ls = {}, {}
    for node in reversed(order):
        lf[node] = min((ls[s] for s in successors[node]), default=project_duration)
        ls[node] = lf[node] - nodes[node]

    result = {}
    for node in nodes:
        slack = ls[node] - es[node]
        result[node] = {
            "ES": es[node], "EF": ef[node],
            "LS": ls[node], "LF": lf[node],
            "slack": slack,
            "critical": slack == 0,
        }
    return result
