"""CLI status dashboard for migration progress."""
import argparse
import sys
from .state import MigrationState


def format_status_report(state: MigrationState, show_errors: bool = False) -> str:
    """Format a human-readable status report."""
    c = state.counts
    total = state.total_repos
    pct = (c["completed"] / total * 100) if total > 0 else 0

    bar_width = 40
    filled = int(bar_width * pct / 100) if total > 0 else 0
    bar = "#" * filled + "." * (bar_width - filled)

    lines = [
        f"Migration: {state.wave} | ID: {state.migration_id[:8]}",
        "=" * 60,
        f"Total:       {total}",
        f"Completed:   {c['completed']:>4}  [{bar}] {pct:.1f}%",
        f"In Progress: {c['in_progress']:>4}  {', '.join(state.in_progress_repos) or '-'}",
        f"Failed:      {c['failed']:>4}",
        f"Pending:     {c['pending']:>4}",
        f"Skipped:     {c['skipped']:>4}",
    ]

    if show_errors and state.failed_repos:
        lines.append("")
        lines.append("Errors:")
        for repo_key in state.failed_repos:
            info = state.get_repo_info(repo_key)
            error = info.get("error", "unknown")
            retries = info.get("retry_count", 0)
            lines.append(f"  {repo_key}: {error} (retry {retries})")

    return "\n".join(lines)


def main(args=None):
    parser = argparse.ArgumentParser(description="Migration status dashboard")
    parser.add_argument("--state-file", required=True, help="State file path")
    parser.add_argument("--show-errors", action="store_true", help="Show error details")
    parsed = parser.parse_args(args)

    try:
        state = MigrationState(parsed.state_file)
        print(format_status_report(state, show_errors=parsed.show_errors))
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
