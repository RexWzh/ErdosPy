"""Static dashboard rendering for erdospy."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from .db import ErdosDB
from .workflow import daily_history, resolve_db_path


def resolve_dashboard_db_path(db_path: Path | None = None) -> Path:
    if db_path is not None:
        return resolve_db_path(db_path)

    workspace_db = resolve_db_path(None)
    if workspace_db.exists():
        return workspace_db
    raise FileNotFoundError("No workspace database found for dashboard rendering.")


def dashboard_payload(db_path: Path | None = None) -> dict[str, Any]:
    resolved = resolve_dashboard_db_path(db_path)
    with ErdosDB(resolved) as db:
        stats = db.get_statistics()
        forum = db.get_forum_statistics()
        digest = db.get_forum_digest(limit=12)

    latest_entries = daily_history(resolved)
    latest_date = latest_entries[0]["recorded_at"][:10] if latest_entries else None
    latest_changes = [
        entry for entry in latest_entries if entry.get("kind") == "change"
    ][:12]

    return {
        "db_path": str(resolved),
        "stats": stats,
        "forum": forum,
        "digest": digest,
        "latest_date": latest_date,
        "latest_changes": latest_changes,
    }


def _metric_card(label: str, value: Any) -> str:
    return (
        "<div class='card metric-card'>"
        f"<div class='metric-label'>{html.escape(str(label))}</div>"
        f"<div class='metric-value'>{html.escape(str(value))}</div>"
        "</div>"
    )


def _list_items(rows: list[str]) -> str:
    if not rows:
        return "<p class='muted'>No data yet.</p>"
    return "<ul class='activity-list'>" + "".join(rows) + "</ul>"


def render_dashboard_html(db_path: Path | None = None) -> str:
    try:
        payload = dashboard_payload(db_path)
    except FileNotFoundError:
        return """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>erdospy dashboard</title>
    <style>
      body { margin: 0; font-family: Inter, ui-sans-serif, system-ui, sans-serif; background: #0b1020; color: #edf2ff; }
      main { max-width: 760px; margin: 0 auto; padding: 48px 20px; }
      .card { background: #141b34; border: 1px solid rgba(255,255,255,0.12); border-radius: 18px; padding: 24px; }
      code { font-family: ui-monospace, SFMono-Regular, monospace; }
      .muted { color: #a9b6d3; }
    </style>
  </head>
  <body>
    <main>
      <div class="card">
        <h1>erdospy dashboard</h1>
        <p>No workspace database was found.</p>
        <p class="muted">Run <code>erdospy build</code> to initialize <code>~/.erdospy/erdos_problems.db</code>, then refresh this page.</p>
      </div>
    </main>
  </body>
</html>
"""

    stats = payload["stats"]
    forum = payload["forum"]
    digest = payload["digest"]
    latest_changes = payload["latest_changes"]

    status_rows = sorted(
        stats["by_status"].items(), key=lambda item: (-item[1], item[0])
    )[:8]
    thread_rows = forum["top_problem_threads"][:8]

    latest_thread_rows = [
        (
            "<li>"
            f"<strong>#{html.escape(row['problem_number'] or row['thread_key'])}</strong> "
            f"<span>{html.escape(row['last_activity'])}</span> "
            f"<span class='muted'>by {html.escape(row['last_author'] or '-')}"
            f" · {row['post_count']} posts</span>"
            "</li>"
        )
        for row in digest["latest_threads"][:8]
    ]
    latest_change_rows = [
        (
            "<li>"
            f"<strong>#{html.escape(entry['problem_number'])}</strong> "
            f"<span>{html.escape(entry['change_type'])}</span> "
            f"<span class='muted'>{html.escape(entry['recorded_at'])}</span>"
            f"<div>{html.escape(entry['description'])}</div>"
            "</li>"
        )
        for entry in latest_changes
    ]

    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>erdospy dashboard</title>
    <style>
      :root {{
        color-scheme: light dark;
        --bg: #0b1020;
        --panel: #141b34;
        --panel-2: #1b2444;
        --text: #edf2ff;
        --muted: #a9b6d3;
        --accent: #86efac;
        --accent-2: #7dd3fc;
        --border: rgba(255, 255, 255, 0.12);
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        font-family: Inter, ui-sans-serif, system-ui, sans-serif;
        background: radial-gradient(circle at top, #182347, var(--bg) 52%);
        color: var(--text);
      }}
      main {{ max-width: 1120px; margin: 0 auto; padding: 32px 20px 72px; }}
      .hero {{ display: grid; gap: 10px; margin-bottom: 28px; }}
      .eyebrow {{ color: var(--accent); font-size: 13px; letter-spacing: 0.08em; text-transform: uppercase; }}
      h1 {{ margin: 0; font-size: clamp(30px, 5vw, 52px); }}
      .muted {{ color: var(--muted); }}
      .grid {{ display: grid; gap: 16px; }}
      .metrics {{ grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); margin-bottom: 24px; }}
      .columns {{ grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); }}
      .card {{
        background: linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.02));
        border: 1px solid var(--border);
        border-radius: 18px;
        padding: 18px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.18);
      }}
      .metric-card {{ min-height: 108px; display: flex; flex-direction: column; justify-content: space-between; }}
      .metric-label {{ color: var(--muted); font-size: 14px; }}
      .metric-value {{ font-size: 34px; font-weight: 700; }}
      h2 {{ margin: 0 0 14px; font-size: 18px; }}
      table {{ width: 100%; border-collapse: collapse; }}
      th, td {{ text-align: left; padding: 10px 0; border-bottom: 1px solid var(--border); font-size: 14px; vertical-align: top; }}
      th {{ color: var(--muted); font-weight: 600; }}
      .activity-list {{ list-style: none; margin: 0; padding: 0; display: grid; gap: 12px; }}
      .activity-list li {{ padding-bottom: 12px; border-bottom: 1px solid var(--border); }}
      .footer {{ margin-top: 22px; color: var(--muted); font-size: 13px; }}
      code {{ font-family: ui-monospace, SFMono-Regular, monospace; }}
    </style>
  </head>
  <body>
    <main>
      <section class="hero">
        <div class="eyebrow">erdospy serve</div>
        <h1>Erdos problem dashboard</h1>
        <div class="muted">Local workspace overview for <code>{html.escape(payload["db_path"])}</code></div>
        <div class="muted">Latest tracked date: {html.escape(payload["latest_date"] or "n/a")}</div>
      </section>

      <section class="grid metrics">
        {_metric_card("Problems", stats["total"])}
        {_metric_card("Formalized", stats["formalized"])}
        {_metric_card("Contributors", stats["total_contributors"])}
        {_metric_card("Comments", stats["total_comments"])}
        {_metric_card("Forum threads", forum["problem_threads"])}
        {_metric_card("Forum posts", forum["forum_posts"])}
      </section>

      <section class="grid columns">
        <div class="card">
          <h2>Status breakdown</h2>
          <table>
            <thead><tr><th>Status</th><th>Count</th></tr></thead>
            <tbody>
              {"".join(f"<tr><td>{html.escape(name)}</td><td>{count}</td></tr>" for name, count in status_rows)}
            </tbody>
          </table>
        </div>

        <div class="card">
          <h2>Top forum threads</h2>
          <table>
            <thead><tr><th>Problem</th><th>Comments</th><th>Title</th></tr></thead>
            <tbody>
              {"".join(f"<tr><td>#{html.escape(item['problem_number'])}</td><td>{item['comment_count']}</td><td>{html.escape(item['title'] or '-')}</td></tr>" for item in thread_rows)}
            </tbody>
          </table>
        </div>

        <div class="card">
          <h2>Latest active threads</h2>
          {_list_items(latest_thread_rows)}
        </div>

        <div class="card">
          <h2>Latest progress signals</h2>
          {_list_items(latest_change_rows)}
        </div>
      </section>

      <div class="footer">Generated by erdospy. The GitHub Pages build can publish this page from the current workspace snapshot.</div>
      <script id="erdospy-dashboard-data" type="application/json">{html.escape(json.dumps(payload, ensure_ascii=False))}</script>
    </main>
  </body>
</html>
"""


def write_dashboard_html(output_path: Path, db_path: Path | None = None) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_dashboard_html(db_path), encoding="utf-8")
    return output_path
