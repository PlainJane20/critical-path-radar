"""
Renders the CPM result as a Gantt-style HTML/CSS chart, screenshotted via
headless Chrome — same technique used for slack-daily-agent's charts, for
the same reason: real gradients and native font rendering read as far more
production-grade than a matplotlib raster.
"""

CRITICAL_COLOR = "#e34948"  # status-critical red — this is the one thing that determines the deadline
SLACK_COLOR = "#2a78d6"     # categorical blue — has room to move


def render_gantt_html(nodes: dict, cpm_result: dict) -> str:
    duration = max((r["EF"] for r in cpm_result.values()), default=1)
    rows_sorted = sorted(cpm_result.items(), key=lambda x: (not x[1]["critical"], x[1]["ES"]))

    px_per_day = 1000 / duration
    row_height = 52
    chart_height = len(rows_sorted) * row_height

    bars = []
    for i, (key, r) in enumerate(rows_sorted):
        y = i * row_height
        summary = nodes[key]["summary"][:38]
        es_px = r["ES"] * px_per_day
        bar_width = (r["EF"] - r["ES"]) * px_per_day
        slack_width = r["slack"] * px_per_day
        color = CRITICAL_COLOR if r["critical"] else SLACK_COLOR
        glow = f"box-shadow: 0 0 24px rgba(227,73,72,0.5);" if r["critical"] else ""
        label = "CRITICAL" if r["critical"] else f"{r['slack']}d slack"

        bars.append(f"""
        <div class="row" style="top: {y}px;">
          <div class="label">{key} — {summary}</div>
          <div class="track" style="left: {180 + es_px}px; width: {bar_width}px; background: {color}; {glow}"></div>
          {"" if r["slack"] == 0 else f'<div class="slack-track" style="left: {180 + es_px + bar_width}px; width: {slack_width}px;"></div>'}
          <div class="tag" style="left: {180 + es_px + bar_width + slack_width + 10}px; color: {color};">{label}</div>
        </div>""")

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    width: 1500px; height: {chart_height + 180}px;
    background: radial-gradient(ellipse 1200px 700px at 15% 0%, #1a2420 0%, #0a0b0d 55%);
    font-family: -apple-system, "SF Pro Display", "Helvetica Neue", sans-serif;
    color: #fff; padding: 60px;
  }}
  .eyebrow {{ font-size: 15px; font-weight: 700; letter-spacing: 3px; text-transform: uppercase; color: #6b7280; margin-bottom: 12px; }}
  .title {{ font-size: 38px; font-weight: 800; letter-spacing: -1px; margin-bottom: 40px; }}
  .chart {{ position: relative; }}
  .row {{ position: absolute; width: 100%; height: {row_height}px; }}
  .label {{ position: absolute; left: 0; top: 16px; width: 175px; font-size: 13px; font-weight: 700; color: #d1d5db; }}
  .track {{ position: absolute; top: 12px; height: 22px; border-radius: 11px; }}
  .slack-track {{ position: absolute; top: 16px; height: 14px; border-radius: 7px; background: rgba(255,255,255,0.08); border: 1px dashed rgba(255,255,255,0.25); }}
  .tag {{ position: absolute; top: 14px; font-size: 12px; font-weight: 800; letter-spacing: 0.5px; white-space: nowrap; }}
  .caption {{ margin-top: 30px; font-size: 13px; color: #6b7280; }}
</style></head>
<body>
  <div class="eyebrow">Critical Path Analysis</div>
  <div class="title">Dependency Timeline — {duration} Day Project</div>
  <div class="chart" style="height: {chart_height}px;">{"".join(bars)}</div>
  <div class="caption">Solid bar = duration &nbsp;·&nbsp; dashed extension = slack (float) &nbsp;·&nbsp; red = critical path (zero slack, determines the end date)</div>
</body></html>"""
