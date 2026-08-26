import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from risk import assess_risk

TODAY = date(2026, 8, 26)


def node(updated="2026-08-25T10:00:00.000-0700", summary="Test"):
    return {"summary": summary, "updated": updated}


def test_critical_and_stale_is_highest_severity():
    nodes = {"A": node(updated="2026-08-01T10:00:00.000-0700")}
    cpm = {"A": {"critical": True, "slack": 0}}
    result = assess_risk(nodes, cpm, today=TODAY)
    assert result[0]["severity"] == "CRITICAL_AT_RISK"


def test_critical_but_fresh_is_lower_severity_than_at_risk():
    nodes = {"A": node()}
    cpm = {"A": {"critical": True, "slack": 0}}
    result = assess_risk(nodes, cpm, today=TODAY)
    assert result[0]["severity"] == "CRITICAL_ON_TRACK"


def test_stale_but_high_slack_is_not_the_top_priority():
    nodes = {
        "A": node(updated="2026-08-01T10:00:00.000-0700"),  # stale, huge slack
        "B": node(updated="2026-08-01T10:00:00.000-0700"),  # stale, zero slack
    }
    cpm = {"A": {"critical": False, "slack": 300}, "B": {"critical": True, "slack": 0}}
    result = assess_risk(nodes, cpm, today=TODAY)
    assert result[0]["key"] == "B"  # critical+stale ranks above stale-with-slack even though both are "stale"


def test_healthy_item_ranks_last():
    nodes = {"A": node(), "B": node(updated="2026-08-01T10:00:00.000-0700")}
    cpm = {"A": {"critical": False, "slack": 50}, "B": {"critical": True, "slack": 0}}
    result = assess_risk(nodes, cpm, today=TODAY)
    assert result[-1]["key"] == "A"
    assert result[-1]["severity"] == "HEALTHY"
