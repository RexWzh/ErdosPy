from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from erdospy.cli.app import app
from erdospy.dashboard import write_dashboard_html


runner = CliRunner()


def test_stats_command_renders_key_sections():
    result = runner.invoke(app, ["stats"])

    assert result.exit_code == 0
    assert "erdospy Stats" in result.stdout
    assert "Total problems" in result.stdout
    assert "Status Breakdown" in result.stdout
    assert "Top Tags" in result.stdout


def test_get_command_json_output_contains_expected_fields():
    result = runner.invoke(app, ["get", "1", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["number"] == "1"
    assert payload["status"]
    assert isinstance(payload["tags"], list)


def test_get_command_with_comments_shows_comments_table():
    result = runner.invoke(app, ["get", "1", "--comments"])

    assert result.exit_code == 0
    assert "Problem #1" in result.stdout
    assert "Comments for #1" in result.stdout


def test_search_command_shows_matching_results():
    result = runner.invoke(app, ["search", "Sidon", "--limit", "3"])

    assert result.exit_code == 0
    assert "Search Results for 'Sidon'" in result.stdout
    assert "30" in result.stdout or "39" in result.stdout or "42" in result.stdout


def test_list_command_applies_filters():
    result = runner.invoke(
        app, ["list", "--status", "open", "--has-prize", "--limit", "5"]
    )

    assert result.exit_code == 0
    assert "Problem List" in result.stdout
    assert "status=open" in result.stdout


def test_missing_problem_returns_nonzero_exit():
    result = runner.invoke(app, ["get", "999999"])

    assert result.exit_code == 1
    assert "not found" in result.stdout.lower()


def test_build_command_creates_workspace_database(tmp_path: Path):
    db_path = tmp_path / "workspace" / "erdos.db"

    result = runner.invoke(app, ["build", "--db", str(db_path)])

    assert result.exit_code == 0
    assert db_path.exists()
    assert (db_path.parent / "history.jsonl").exists()
    assert "Initialized workspace database" in result.stdout


def test_daily_command_reads_recorded_progress(tmp_path: Path):
    db_path = tmp_path / "workspace" / "erdos.db"
    db_path.parent.mkdir(parents=True)
    db_path.write_text("placeholder", encoding="utf-8")
    (db_path.parent / "history.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "kind": "run",
                        "recorded_at": "2026-04-07T10:00:00+00:00",
                        "mode": "update",
                        "total_changes": 1,
                        "status_changes": 1,
                        "comment_changes": 0,
                    }
                ),
                json.dumps(
                    {
                        "kind": "change",
                        "recorded_at": "2026-04-07T10:00:00+00:00",
                        "problem_number": "42",
                        "change_type": "status_change",
                        "description": "Problem #42 changed status from open to solved.",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["daily", "--db", str(db_path), "--date", "2026-04-07"])

    assert result.exit_code == 0
    assert "Daily Progress for 2026-04-07" in result.stdout
    assert "Problem #42 changed status" in result.stdout


def test_record_command_filters_specific_problem_history(tmp_path: Path):
    db_path = tmp_path / "workspace" / "erdos.db"
    db_path.parent.mkdir(parents=True)
    db_path.write_text("placeholder", encoding="utf-8")
    (db_path.parent / "history.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "kind": "change",
                        "recorded_at": "2026-04-07T10:00:00+00:00",
                        "problem_number": "42",
                        "change_type": "comment_delta",
                        "description": "Problem #42 comments increased from 3 to 5.",
                    }
                ),
                json.dumps(
                    {
                        "kind": "change",
                        "recorded_at": "2026-04-07T11:00:00+00:00",
                        "problem_number": "12",
                        "change_type": "status_change",
                        "description": "Problem #12 changed status from open to proved.",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["record", "42", "--db", str(db_path)])

    assert result.exit_code == 0
    assert "Recorded History for Problem #42" in result.stdout
    assert "comments increased" in result.stdout
    assert "Problem #12" not in result.stdout


def test_update_command_renders_summary_with_mocked_result(monkeypatch):
    class FakeRun:
        recorded_at = "2026-04-07T10:00:00+00:00"
        total_changes = 2
        status_changes = 1
        comment_changes = 1

    class FakeChange:
        problem_number = "42"
        change_type = "status_change"
        description = "Problem #42 changed status from open to solved."

    class FakeResult:
        db_path = Path("/tmp/demo.db")
        run = FakeRun()
        changes = [FakeChange()]

    monkeypatch.setattr(
        "erdospy.cli.workspace.update_workspace", lambda *args, **kwargs: FakeResult()
    )

    result = runner.invoke(app, ["update", "--db", "/tmp/demo.db", "--quick"])

    assert result.exit_code == 0
    assert "Update Summary" in result.stdout
    assert "Detected Changes" in result.stdout
    assert "Problem #42 changed status" in result.stdout


def test_write_dashboard_html_generates_expected_sections(tmp_path: Path):
    output = tmp_path / "site" / "dashboard" / "index.html"

    write_dashboard_html(output)

    assert output.exists()
    text = output.read_text(encoding="utf-8")
    assert "Erdos problem dashboard" in text
    assert "Latest progress signals" in text


def test_serve_dashboard_help_lists_command():
    result = runner.invoke(app, ["serve", "dashboard", "--help"])

    assert result.exit_code == 0
    assert "serve" in result.stdout.lower()
    assert "dashboard" in result.stdout.lower()
