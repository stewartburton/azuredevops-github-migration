"""Migration state persistence.

Tracks per-repo migration status in a JSON file that survives crashes.
Thread-safe for parallel batch migration.
"""
import json
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class MigrationState:
    """Persistent, thread-safe migration state tracker.

    Each repo is tracked with a status of:
      pending -> in_progress -> completed | failed | skipped

    Every mutation is immediately flushed to disk via atomic rename,
    so the state file survives process crashes.  A threading lock
    serialises concurrent access within a single process.
    """

    def __init__(self, state_file: str, wave: str = None):
        self._file = state_file
        self._lock = threading.Lock()

        if os.path.exists(state_file):
            self._data = self._load()
        else:
            self._data = {
                "migration_id": str(uuid.uuid4()),
                "wave": wave or "default",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "repos": {},
            }
            self._save()

    # ------------------------------------------------------------------
    # Read-only properties
    # ------------------------------------------------------------------

    @property
    def migration_id(self) -> str:
        return self._data["migration_id"]

    @property
    def wave(self) -> str:
        return self._data["wave"]

    @property
    def total_repos(self) -> int:
        return len(self._data["repos"])

    @property
    def counts(self) -> Dict[str, int]:
        counts = {"pending": 0, "in_progress": 0, "completed": 0, "failed": 0, "skipped": 0}
        for info in self._data["repos"].values():
            status = info.get("status", "pending")
            counts[status] = counts.get(status, 0) + 1
        return counts

    @property
    def pending_repos(self) -> List[str]:
        return [k for k, v in self._data["repos"].items() if v["status"] == "pending"]

    @property
    def failed_repos(self) -> List[str]:
        return [k for k, v in self._data["repos"].items() if v["status"] == "failed"]

    @property
    def completed_repos(self) -> List[str]:
        return [k for k, v in self._data["repos"].items() if v["status"] == "completed"]

    @property
    def in_progress_repos(self) -> List[str]:
        return [k for k, v in self._data["repos"].items() if v["status"] == "in_progress"]

    # ------------------------------------------------------------------
    # Mutation methods (all thread-safe, all persist immediately)
    # ------------------------------------------------------------------

    def add_repo(self, repo_key: str) -> None:
        """Add a single repo with *pending* status (idempotent)."""
        with self._lock:
            if repo_key not in self._data["repos"]:
                self._data["repos"][repo_key] = {"status": "pending"}
                self._save()

    def add_repos(self, repo_keys: List[str]) -> None:
        """Bulk-add repos with *pending* status (idempotent per key)."""
        with self._lock:
            for key in repo_keys:
                if key not in self._data["repos"]:
                    self._data["repos"][key] = {"status": "pending"}
            self._save()

    def mark_in_progress(self, repo_key: str, step: str = "") -> None:
        """Transition a repo to *in_progress*."""
        with self._lock:
            repo = self._data["repos"].setdefault(repo_key, {})
            repo["status"] = "in_progress"
            repo["step"] = step
            repo["migration_started"] = datetime.now(timezone.utc).isoformat()
            self._save()

    def mark_completed(
        self,
        repo_key: str,
        github_url: str = "",
        branches: int = 0,
        commits: int = 0,
        verification: Dict = None,
    ) -> None:
        """Transition a repo to *completed*."""
        with self._lock:
            repo = self._data["repos"].setdefault(repo_key, {})
            repo["status"] = "completed"
            repo["github_url"] = github_url
            repo["migration_completed"] = datetime.now(timezone.utc).isoformat()
            if branches:
                repo["branches_migrated"] = branches
            if commits:
                repo["commits_migrated"] = commits
            if verification:
                repo["verification"] = verification
            self._save()

    def mark_failed(self, repo_key: str, error: str = "") -> None:
        """Transition a repo to *failed* and bump the retry counter."""
        with self._lock:
            repo = self._data["repos"].setdefault(repo_key, {})
            repo["status"] = "failed"
            repo["error"] = error
            repo["retry_count"] = repo.get("retry_count", 0) + 1
            repo["last_attempt"] = datetime.now(timezone.utc).isoformat()
            self._save()

    def mark_skipped(self, repo_key: str, reason: str = "") -> None:
        """Transition a repo to *skipped*."""
        with self._lock:
            repo = self._data["repos"].setdefault(repo_key, {})
            repo["status"] = "skipped"
            repo["reason"] = reason
            self._save()

    # ------------------------------------------------------------------
    # Freeze / ACL helpers (used by the freeze step)
    # ------------------------------------------------------------------

    def store_freeze_acls(self, repo_key: str, acls: Any) -> None:
        """Persist original ACLs so they can be restored after migration."""
        with self._lock:
            repo = self._data["repos"].setdefault(repo_key, {})
            repo["original_acls"] = acls
            repo["frozen_at"] = datetime.now(timezone.utc).isoformat()
            self._save()

    def get_freeze_acls(self, repo_key: str) -> Optional[Any]:
        """Retrieve stored ACLs for a repo, or ``None``."""
        return self._data["repos"].get(repo_key, {}).get("original_acls")

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def get_status(self, repo_key: str) -> Optional[str]:
        """Return the current status string, or ``None`` if unknown."""
        repo = self._data["repos"].get(repo_key)
        return repo["status"] if repo else None

    def get_repo_info(self, repo_key: str) -> Optional[Dict]:
        """Return the full info dict for a repo, or ``None``."""
        return self._data["repos"].get(repo_key)

    # ------------------------------------------------------------------
    # Internal persistence
    # ------------------------------------------------------------------

    def _save(self) -> None:
        """Atomically write state to disk (write-to-tmp + rename).

        On Windows, os.replace can raise PermissionError when the target
        file is momentarily locked by another thread/process (e.g. antivirus).
        We retry a few times with a short sleep to handle this.
        """
        tmp = self._file + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, default=str)
        for attempt in range(5):
            try:
                os.replace(tmp, self._file)
                return
            except PermissionError:
                if attempt < 4:
                    import time
                    time.sleep(0.01 * (attempt + 1))
                else:
                    raise

    def _load(self) -> Dict:
        """Read state from disk."""
        with open(self._file, "r", encoding="utf-8") as f:
            return json.load(f)
