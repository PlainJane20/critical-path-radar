#!/usr/bin/env python3
"""
Critical Path Radar — real Critical Path Method math on real Jira
dependency links, with a risk layer that flags critical-path items that
are also showing staleness signals.

Usage:
  python run_analysis.py
  python run_analysis.py --out report.md
"""

import argparse
from pathlib import Path

from dotenv import load_dotenv
from rich import box
from rich.console import Console
from rich.table import Table

load_dotenv(Path(__file__).parent / ".env")

from config import load_config
from jira_graph import fetch_dependency_graph
from cpm import compute_critical_path
from risk import assess_risk

console = Console()

SEVERITY_STYLE = {
    "CRITICAL_AT_RISK": "bold red",
    "CRITICAL_ON_TRACK": "yellow",
    "STALE_WITH_SLACK": "dim yellow",
    "HEALTHY": "green",
}


def render_markdown(nodes, cpm_result, assessments, edges, estimated) -> str:
    lines = ["# Critical Path Analysis\n"]
    critical_chain = [k for k, r in cpm_result.items() if r["critical"]]
    duration = max((r["EF"] for r in cpm_result.values()), default=0)
    lines.append(f"**Project duration: {duration} days.** Critical path: "
                 + " → ".join(sorted(critical_chain, key=lambda k: cpm_result[k]["ES"])) + "\n")

    if estimated:
        lines.append(f"*Duration estimated (no due date set) for: {', '.join(sorted(estimated))} — "
                      f"see jira_graph.py's DEFAULT_DURATION_DAYS assumptions.*\n")

    lines.append("## Risk-Ranked Workstreams\n")
    lines.append("| Severity | Key | Summary | Slack (days) | Days Stale |")
    lines.append("|---|---|---|---|---|")
    for a in assessments:
        lines.append(f"| {a['severity']} | {a['key']} | {a['summary'][:40]} | "
                      f"{a['slack_days']} | {a['days_stale'] if a['days_stale'] is not None else '—'} |")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out")
    args = parser.parse_args()

    cfg = load_config()
    if not cfg["JIRA_URL"]:
        console.print("[red]Missing Jira credentials[/]")
        return

    console.print(f"[bold cyan]Fetching {cfg['JIRA_PROJECT_KEY']} and its dependency links...[/]")
    graph = fetch_dependency_graph(cfg)
    durations = {k: v["duration"] for k, v in graph["nodes"].items()}

    cpm_result = compute_critical_path(durations, graph["edges"])
    assessments = assess_risk(graph["nodes"], cpm_result)

    table = Table(box=box.ROUNDED, show_header=True, header_style="bold dim")
    table.add_column("Severity")
    table.add_column("Key")
    table.add_column("Summary")
    table.add_column("Slack (days)", justify="right")
    table.add_column("Days Stale", justify="right")
    for a in assessments:
        style = SEVERITY_STYLE[a["severity"]]
        table.add_row(f"[{style}]{a['severity']}[/]", a["key"], a["summary"][:45],
                      str(a["slack_days"]), str(a["days_stale"]) if a["days_stale"] is not None else "—")
    console.print(table)

    duration = max((r["EF"] for r in cpm_result.values()), default=0)
    critical_chain = sorted([k for k, r in cpm_result.items() if r["critical"]],
                             key=lambda k: cpm_result[k]["ES"])
    console.print(f"\n[bold]Project duration:[/] {duration} days")
    console.print(f"[bold]Critical path:[/] {' → '.join(critical_chain)}")

    if graph["estimated_durations"]:
        console.print(f"[dim]Duration estimated (no due date) for: "
                       f"{', '.join(sorted(graph['estimated_durations']))}[/]")

    if args.out:
        report = render_markdown(graph["nodes"], cpm_result, assessments, graph["edges"], graph["estimated_durations"])
        Path(args.out).write_text(report)
        console.print(f"\n[green]✓[/] Saved to {args.out}")


if __name__ == "__main__":
    main()
