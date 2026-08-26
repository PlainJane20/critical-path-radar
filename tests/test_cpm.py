"""
Verified against a textbook CPM example first — a wrong critical-path
algorithm is worse than none, since it would confidently point leadership
at the wrong bottleneck. This is the standard 6-activity example used in
project-management courses, with a known, independently-verifiable answer:
critical path A -> C -> E -> F, duration 19, and B/D carry slack.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from cpm import CycleError, compute_critical_path


def test_textbook_example_matches_known_answer():
    # A(5) -> C(7) -> E(4) -> F(3)   = 19  (critical path)
    # A(5) -> B(3) -> D(6) -> F(3)   = 17  (2 days of slack)
    nodes = {"A": 5, "B": 3, "C": 7, "D": 6, "E": 4, "F": 3}
    edges = [("A", "B"), ("A", "C"), ("B", "D"), ("C", "E"), ("D", "F"), ("E", "F")]

    result = compute_critical_path(nodes, edges)

    assert result["F"]["EF"] == 19  # total project duration
    for k in ["A", "C", "E", "F"]:
        assert result[k]["critical"] is True, f"{k} should be on the critical path"
    for k in ["B", "D"]:
        assert result[k]["critical"] is False
        assert result[k]["slack"] == 2


def test_single_node_no_dependencies():
    result = compute_critical_path({"A": 5}, [])
    assert result["A"] == {"ES": 0, "EF": 5, "LS": 0, "LF": 5, "slack": 0, "critical": True}


def test_two_parallel_independent_chains_longer_one_is_critical():
    nodes = {"A": 10, "B": 2}
    result = compute_critical_path(nodes, [])
    assert result["A"]["critical"] is True   # the longer chain determines the project end date
    assert result["A"]["slack"] == 0
    assert result["B"]["critical"] is False  # B can slip up to 8 days without delaying the project
    assert result["B"]["slack"] == 8


def test_cycle_raises_cycle_error():
    nodes = {"A": 1, "B": 1}
    edges = [("A", "B"), ("B", "A")]
    with pytest.raises(CycleError):
        compute_critical_path(nodes, edges)


def test_empty_graph_returns_empty():
    assert compute_critical_path({}, []) == {}


def test_diamond_dependency_slack_is_correct():
    # A blocks both B and C; both B and C block D. B is longer, so C carries slack.
    nodes = {"A": 2, "B": 8, "C": 3, "D": 1}
    edges = [("A", "B"), ("A", "C"), ("B", "D"), ("C", "D")]
    result = compute_critical_path(nodes, edges)
    assert result["D"]["EF"] == 11  # 2 + 8 + 1
    assert result["B"]["critical"] is True
    assert result["C"]["critical"] is False
    assert result["C"]["slack"] == 5  # B's chain (8) minus C's chain (3)
