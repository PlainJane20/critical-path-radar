"""
Builds a dependency graph from real Jira issues + issue links.

Jira issues don't carry an explicit "duration" field, so one has to be
estimated. Documented openly rather than silently assumed: if an issue has
both a created date and a due date, duration = the gap between them (the
team's own implied estimate). Otherwise, fall back to a per-issue-type
default — these are guesses, not measurements, and the CLI output says so.
"""

import re
from datetime import datetime

import requests
from requests.auth import HTTPBasicAuth

DEFAULT_DURATION_DAYS = {
    "Epic": 30,
    "Feature": 15,
    "Story": 5,
    "Task": 3,
    "Bug": 2,
}
FALLBACK_DURATION = 5


def _parse_date(s):
    if not s:
        return None
    s = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", s)  # Jira's non-colon offset, same fix as exec-status-rollup
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def fetch_dependency_graph(cfg: dict) -> dict:
    """Returns {"nodes": {key: {...}}, "edges": [(blocker, blocked), ...], "estimated_durations": set of keys}."""
    auth = HTTPBasicAuth(cfg["JIRA_EMAIL"], cfg["JIRA_API_TOKEN"])
    resp = requests.get(
        f"{cfg['JIRA_URL']}/rest/api/3/search/jql",
        auth=auth,
        headers={"Accept": "application/json"},
        params={
            "jql": f"project={cfg['JIRA_PROJECT_KEY']}",
            "maxResults": 100,
            "fields": "summary,issuetype,status,duedate,created,issuelinks,updated",
        },
        timeout=30,
    )
    resp.raise_for_status()
    issues = resp.json()["issues"]

    nodes = {}
    edges = []
    estimated_durations = set()

    for issue in issues:
        key = issue["key"]
        f = issue["fields"]
        issue_type = f["issuetype"]["name"]

        created = _parse_date(f.get("created"))
        due = _parse_date(f.get("duedate"))
        # duedate from Jira is a bare date ("2026-10-31", no timezone) while
        # created is a full offset-aware timestamp — subtracting them
        # directly raises TypeError. Only day-level granularity matters
        # here anyway, so compare .date() on both rather than reconciling
        # timezone-awareness.
        if created and due and (due.date() - created.date()).days > 0:
            duration = (due.date() - created.date()).days
        else:
            duration = DEFAULT_DURATION_DAYS.get(issue_type, FALLBACK_DURATION)
            estimated_durations.add(key)

        nodes[key] = {
            "summary": f.get("summary", ""),
            "type": issue_type,
            "status": f["status"]["name"],
            "status_category": f["status"]["statusCategory"]["key"],
            "duration": duration,
            "due_date": f.get("duedate"),
            "updated": f.get("updated"),
        }

        for link in f.get("issuelinks", []):
            if link.get("type", {}).get("name") == "Blocks":
                # Confirmed by inspecting the raw payload, not assumed: when
                # THIS issue's record contains an "inwardIssue" field, this
                # issue itself plays Jira's "outward" role for the link
                # (outward description = "blocks") — so this issue blocks
                # the named inwardIssue. When this issue's record instead
                # shows "outwardIssue", this issue plays the inward role
                # ("is blocked by") — that same edge gets added when we
                # process the OTHER issue's own inwardIssue field, so it's
                # skipped here to avoid double-counting. Got this backwards
                # on the first pass — see README for how it was caught.
                if "inwardIssue" in link:
                    edges.append((key, link["inwardIssue"]["key"]))

    # Keep only edges where both endpoints are in this project's fetched set
    edges = [(a, b) for a, b in edges if a in nodes and b in nodes]

    return {"nodes": nodes, "edges": edges, "estimated_durations": estimated_durations}
