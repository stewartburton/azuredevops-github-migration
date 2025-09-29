from __future__ import annotations

"""Utility functions for the Azure DevOps to GitHub migration tool with improved typing."""

import logging
import os
import re
import time
from datetime import datetime
from typing import Any, Callable, Dict, Iterable, List, Optional, TypeVar, Union, cast

import html2text
import markdown


def sanitize_github_name(name: str) -> str:
    """Sanitize repository name for GitHub."""
    # Convert to lowercase and replace invalid characters
    sanitized = re.sub(r"[^a-zA-Z0-9._-]", "-", name)
    sanitized = re.sub(
        r"-+", "-", sanitized
    )  # Replace multiple dashes with single dash
    sanitized = sanitized.strip("-._")  # Remove leading/trailing special chars

    # Ensure it doesn't start with a dot
    if sanitized.startswith("."):
        sanitized = "repo-" + sanitized

    return sanitized[:100]  # GitHub repo name limit


def convert_html_to_markdown(html_content: str) -> str:
    """Convert HTML content to Markdown."""
    if not html_content:
        return ""

    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = False
    h.ignore_tables = False
    h.body_width = 0  # Don't wrap lines

    return h.handle(html_content)


def format_work_item_body(work_item: Dict[str, Any]) -> str:
    """Format Azure DevOps work item as GitHub issue body."""
    fields = work_item.get("fields", {})

    body_parts = []

    # Add migration header
    body_parts.append(f"**Migrated from Azure DevOps Work Item #{work_item['id']}**")
    body_parts.append("")

    # Add metadata table
    metadata = []
    if fields.get("System.WorkItemType"):
        metadata.append(f"**Type:** {fields['System.WorkItemType']}")
    if fields.get("System.State"):
        metadata.append(f"**State:** {fields['System.State']}")
    if fields.get("System.AssignedTo"):
        assignee = fields["System.AssignedTo"]
        if isinstance(assignee, dict):
            assignee = assignee.get("displayName", assignee.get("uniqueName", ""))
        metadata.append(f"**Assigned To:** {assignee}")
    if fields.get("System.CreatedDate"):
        created_date = fields["System.CreatedDate"]
        if isinstance(created_date, str):
            try:
                dt = datetime.fromisoformat(created_date.replace("Z", "+00:00"))
                created_date = dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                pass
        metadata.append(f"**Created:** {created_date}")
    if fields.get("Microsoft.VSTS.Common.Priority"):
        metadata.append(f"**Priority:** {fields['Microsoft.VSTS.Common.Priority']}")

    if metadata:
        body_parts.extend(metadata)
        body_parts.append("")

    # Add description
    description = fields.get("System.Description", "")
    if description:
        body_parts.append("## Description")
        body_parts.append(convert_html_to_markdown(description))
        body_parts.append("")

    # Add acceptance criteria
    acceptance_criteria = fields.get("Microsoft.VSTS.Common.AcceptanceCriteria", "")
    if acceptance_criteria:
        body_parts.append("## Acceptance Criteria")
        body_parts.append(convert_html_to_markdown(acceptance_criteria))
        body_parts.append("")

    # Add reproduction steps for bugs
    repro_steps = fields.get("Microsoft.VSTS.TCM.ReproSteps", "")
    if repro_steps:
        body_parts.append("## Reproduction Steps")
        body_parts.append(convert_html_to_markdown(repro_steps))
        body_parts.append("")

    # Add system info for bugs
    system_info = fields.get("Microsoft.VSTS.TCM.SystemInfo", "")
    if system_info:
        body_parts.append("## System Information")
        body_parts.append(convert_html_to_markdown(system_info))
        body_parts.append("")

    return "\n".join(body_parts).strip()


def generate_labels_for_work_item(
    work_item: Dict[str, Any],
    work_item_mapping: Optional[Dict[str, str]] = None,
    state_mapping: Optional[Dict[str, str]] = None,
) -> List[str]:
    """Generate GitHub labels for a work item."""
    fields = work_item.get("fields", {})
    labels = ["migrated"]

    # Add work item type label
    work_item_type = fields.get("System.WorkItemType", "")
    if work_item_type:
        if work_item_mapping and work_item_type in work_item_mapping:
            labels.append(work_item_mapping[work_item_type])
        else:
            labels.append(f"type:{work_item_type.lower().replace(' ', '-')}")

    # Add state label
    state = fields.get("System.State", "")
    if state:
        if state_mapping and state in state_mapping:
            # Don't add state as label since GitHub issues have their own state
            pass
        else:
            labels.append(f"state:{state.lower().replace(' ', '-')}")

    # Add priority label
    priority = fields.get("Microsoft.VSTS.Common.Priority")
    if priority:
        labels.append(f"priority:{priority}")

    # Add area path as label
    area_path = fields.get("System.AreaPath", "")
    if area_path and "\\" in area_path:
        area = area_path.split("\\")[-1]  # Get the last part of the area path
        labels.append(f"area:{area.lower().replace(' ', '-')}")

    return labels


F = TypeVar("F", bound=Callable[..., Any])


def retry_on_failure(
    func: F, max_retries: int = 3, delay: float = 1.0, backoff_factor: float = 2.0
) -> Callable[..., Any]:
    """Decorator for retrying API calls on failure.

    Returns the wrapped function preserving its type signature.
    """

    def wrapper(*args: Any, **kwargs: Any):  # type: ignore[override]
        last_exception: Optional[Exception] = None
        for attempt in range(max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:  # pragma: no cover - retry logic
                last_exception = e
                if attempt < max_retries:
                    wait_time = delay * (backoff_factor**attempt)
                    logging.warning(
                        f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time:.1f}s..."
                    )
                    time.sleep(wait_time)
                else:
                    logging.error(f"All {max_retries + 1} attempts failed")
                    raise last_exception

    return cast(F, wrapper)


def validate_config(config: Dict[str, Any]) -> List[str]:
    """Validate migration configuration."""
    errors = []

    # Check required Azure DevOps config
    if not config.get("azure_devops", {}).get("organization"):
        errors.append("Azure DevOps organization is required")

    if not config.get("azure_devops", {}).get("personal_access_token"):
        errors.append("Azure DevOps personal access token is required")

    # Check required GitHub config
    if not config.get("github", {}).get("token"):
        errors.append("GitHub token is required")

    # Validate work item mapping
    work_item_mapping = config.get("work_item_mapping", {})
    if not isinstance(work_item_mapping, dict):
        errors.append("work_item_mapping must be a dictionary")

    # Validate state mapping
    state_mapping = config.get("state_mapping", {})
    if not isinstance(state_mapping, dict):
        errors.append("state_mapping must be a dictionary")

    return errors


def load_environment_variables(config: Dict[str, Any]) -> Dict[str, Any]:
    """Load environment variables and substitute them in config mapping ${VAR}."""

    def substitute_env_vars(value: Any) -> Any:
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            env_var = value[2:-1]
            return os.getenv(env_var, value)
        if isinstance(value, dict):
            return {k: substitute_env_vars(v) for k, v in value.items()}
        if isinstance(value, list):
            return [substitute_env_vars(item) for item in value]
        return value

    return cast(Dict[str, Any], substitute_env_vars(config))


def create_progress_bar(current: int, total: int, width: int = 50) -> str:
    """Create a simple text-based progress bar."""
    if total == 0:
        return "[" + "=" * width + "] 100%"

    progress = current / total
    filled_width = int(width * progress)
    bar = "=" * filled_width + "-" * (width - filled_width)
    percentage = int(progress * 100)

    return f"[{bar}] {percentage}% ({current}/{total})"


def log_migration_summary(results: Dict[str, bool], logger: logging.Logger):
    """Log a summary of migration results."""
    total = len(results)
    successful = sum(1 for success in results.values() if success)
    failed = total - successful

    logger.info("=" * 50)
    logger.info("MIGRATION SUMMARY")
    logger.info("=" * 50)
    logger.info(f"Total repositories: {total}")
    logger.info(f"Successfully migrated: {successful}")
    logger.info(f"Failed migrations: {failed}")

    if failed > 0:
        logger.info("\nFailed repositories:")
        for repo, success in results.items():
            if not success:
                logger.info(f"  ❌ {repo}")

    if successful > 0:
        logger.info("\nSuccessfully migrated:")
        for repo, success in results.items():
            if success:
                logger.info(f"  ✅ {repo}")

    logger.info("=" * 50)


class RateLimiter:
    """Simple rate limiter for API calls."""

    def __init__(self, max_calls_per_second: float = 10.0):
        self.max_calls_per_second = max_calls_per_second
        self.min_interval = 1.0 / max_calls_per_second
        self.last_called = 0.0

    def wait_if_needed(self):
        """Wait if necessary to respect rate limits."""
        now = time.time()
        time_since_last = now - self.last_called

        if time_since_last < self.min_interval:
            sleep_time = self.min_interval - time_since_last
            time.sleep(sleep_time)

        self.last_called = time.time()


def extract_mentions_and_links(text: str) -> Dict[str, List[str]]:
    """Extract @mentions and links from text."""
    if not text:
        return {"mentions": [], "links": []}

    # Extract @mentions
    mention_pattern = r"@([a-zA-Z0-9_.-]+)"
    mentions = re.findall(mention_pattern, text)

    # Extract links
    link_pattern = r'https?://[^\s<>"{}|\\^`[\]]+'
    links = re.findall(link_pattern, text)

    return {
        "mentions": list(set(mentions)),  # Remove duplicates
        "links": list(set(links)),
    }


def truncate_text(text: str, max_length: int = 65536) -> str:
    """Truncate text to maximum length (GitHub issue body limit)."""
    if len(text) <= max_length:
        return text

    truncated = text[: max_length - 100]  # Leave room for truncation message
    truncated += "\n\n... [Content truncated due to length limits] ..."

    return truncated
