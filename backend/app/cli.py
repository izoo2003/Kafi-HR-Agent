"""Command-line entry point for the HR & Admin agent's CV ranking module.

Examples:
    python -m app.cli init-db
    python -m app.cli fetch --source gmail
    python -m app.cli score
    python -m app.cli rank
    python -m app.cli report --position "AI Engineer"
    python -m app.cli run-all
"""
from __future__ import annotations

import logging

import click

from app.db.database import get_session, init_db
from app.db.models import SourceChannel
from app.pipeline import (
    fetch_submissions,
    generate_all_reports,
    parse_and_score_pending,
    rank_all,
    run_full_pipeline,
)
from app.reporting.excel_report import generate_position_report

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


@click.group()
def cli() -> None:
    """HR & Admin Agent - CV Ranking CLI."""


@cli.command("init-db")
def init_db_command() -> None:
    """Creates the SQLite tables if they don't exist yet."""
    init_db()
    click.echo("Database initialized.")


@cli.command("fetch")
@click.option(
    "--source",
    type=click.Choice(["gmail", "google_form", "whatsapp", "all"]),
    default="all",
)
def fetch_command(source: str) -> None:
    """Pulls new CV submissions from the selected source(s)."""
    sources = None if source == "all" else [SourceChannel(source)]
    with get_session() as session:
        created = fetch_submissions(session, sources)
    click.echo(f"Ingested {created} new application(s).")


@cli.command("score")
def score_command() -> None:
    """Parses CV text and scores every pending application via Gemini."""
    with get_session() as session:
        succeeded, failed = parse_and_score_pending(session)
    click.echo(f"Scored {succeeded} application(s), {failed} failed.")


@cli.command("rank")
def rank_command() -> None:
    """Recomputes rank order within each position."""
    with get_session() as session:
        rank_all(session)
    click.echo("Rankings recomputed.")


@cli.command("report")
@click.option("--position", default=None, help="Generate for a single position only.")
def report_command(position: str | None) -> None:
    """Generates formatted Excel report(s) for HR review."""
    with get_session() as session:
        if position:
            path = generate_position_report(session, position)
            click.echo(f"Report written to {path}")
        else:
            paths = generate_all_reports(session)
            for path in paths:
                click.echo(f"Report written to {path}")


@cli.command("run-all")
def run_all_command() -> None:
    """Runs the full pipeline end to end: fetch -> score -> rank -> report."""
    with get_session() as session:
        summary = run_full_pipeline(session)
    click.echo(
        f"New applications: {summary['new_applications']} | "
        f"Scored: {summary['scored']} | Failed: {summary['failed']}"
    )
    for path in summary["reports"]:
        click.echo(f"Report: {path}")


if __name__ == "__main__":
    cli()
