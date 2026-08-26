"""
Combines CPM's slack calculation with real staleness/overdue signals.

The point of this layer: a RED-flagged item with 300 days of slack is a
non-event — it can slip enormously without touching the project end date.
A merely-stale item with ZERO slack is the actual emergency, because it's
the one thing standing between the project and its deadline. Slack is what
turns "this looks bad" into "this is actually urgent" — most status
reporting conflates the two.
"""

from datetime import date, datetime
import re

STALE_AFTER_DAYS = 14


def _parse_date(s):
    if not s:
        return None
    s = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", s)
    return datetime.fromisoformat(s.replace("Z", "+00:00")).date()


def assess_risk(nodes: dict, cpm_result: dict, today: date = None) -> list:
    today = today or date.today()
    assessments = []

    for key, node in nodes.items():
        cpm = cpm_result.get(key, {})
        updated = _parse_date(node.get("updated"))
        days_stale = (today - updated).days if updated else None
        is_stale = days_stale is not None and days_stale > STALE_AFTER_DAYS

        if cpm.get("critical") and is_stale:
            severity = "CRITICAL_AT_RISK"
        elif cpm.get("critical"):
            severity = "CRITICAL_ON_TRACK"
        elif is_stale:
            severity = "STALE_WITH_SLACK"
        else:
            severity = "HEALTHY"

        assessments.append({
            "key": key,
            "summary": node["summary"],
            "slack_days": cpm.get("slack"),
            "days_stale": days_stale,
            "critical_path": cpm.get("critical", False),
            "severity": severity,
        })

    order = {"CRITICAL_AT_RISK": 0, "CRITICAL_ON_TRACK": 1, "STALE_WITH_SLACK": 2, "HEALTHY": 3}
    assessments.sort(key=lambda a: order[a["severity"]])
    return assessments
