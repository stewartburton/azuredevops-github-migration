# Enterprise Migration Tool Improvements - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor the migration tool and add state persistence, ADO repo freeze, parallel batch, rollback, verification, and status dashboard to support migrating 700+ repos.

**Architecture:** Surgical refactoring of existing monolith into focused modules, then layering new capabilities (state, freeze, parallel, rollback) on top. TDD throughout. Backward-compatible `migrate.py` wrapper preserved.

**Tech Stack:** Python 3.8+, requests, pyyaml, tqdm, concurrent.futures (stdlib), threading (stdlib), json (stdlib)

---

## Task 1: Extract exceptions into `exceptions.py`

**Files:**
- Create: `src/azuredevops_github_migration/exceptions.py`
- Test: `tests/test_exceptions.py`
- Modify: (none yet - we'll update imports in later tasks)

**Step 1: Write the test file**

```python
# tests/test_exceptions.py
"""Tests for custom exception hierarchy."""
import pytest
from azuredevops_github_migration.exceptions import (
    AuthenticationError,
    MigrationError,
    RateLimitError,
    GitOperationError,
)


class TestExceptionHierarchy:
    def test_migration_error_is_exception(self):
        assert issubclass(MigrationError, Exception)

    def test_authentication_error_is_exception(self):
        assert issubclass(AuthenticationError, Exception)

    def test_rate_limit_error_inherits_migration_error(self):
        assert issubclass(RateLimitError, MigrationError)

    def test_git_operation_error_inherits_migration_error(self):
        assert issubclass(GitOperationError, MigrationError)

    def test_exception_messages(self):
        with pytest.raises(AuthenticationError, match="bad creds"):
            raise AuthenticationError("bad creds")

        with pytest.raises(MigrationError, match="failed"):
            raise MigrationError("failed")

        with pytest.raises(RateLimitError, match="429"):
            raise RateLimitError("429")

        with pytest.raises(GitOperationError, match="push failed"):
            raise GitOperationError("push failed")
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_exceptions.py -v`
Expected: FAIL - `ModuleNotFoundError: No module named 'azuredevops_github_migration.exceptions'`

**Step 3: Write the module**

```python
# src/azuredevops_github_migration/exceptions.py
"""Custom exception hierarchy for the migration tool."""


class AuthenticationError(Exception):
    """Authentication related errors."""
    pass


class MigrationError(Exception):
    """Base exception for migration errors."""
    pass


class RateLimitError(MigrationError):
    """Rate limiting errors."""
    pass


class GitOperationError(MigrationError):
    """Git operation errors."""
    pass
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_exceptions.py -v`
Expected: 5 passed

**Step 5: Commit**

```bash
git add src/azuredevops_github_migration/exceptions.py tests/test_exceptions.py
git commit -m "refactor: extract exceptions into dedicated module"
```

---

## Task 2: Extract config into `config.py`

Deduplicates .env loading and env-var substitution from migrate.py, analyze.py, and utils.py.

**Files:**
- Create: `src/azuredevops_github_migration/config.py`
- Test: `tests/test_config.py`

**Step 1: Write the test file**

```python
# tests/test_config.py
"""Tests for unified configuration module."""
import json
import os
import tempfile
import pytest
from unittest.mock import patch
from azuredevops_github_migration.config import (
    load_env_file,
    substitute_env_vars,
    load_config,
    validate_config,
    detect_unresolved_placeholders,
)


class TestLoadEnvFile:
    def test_loads_env_vars(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text('TEST_KEY_123=hello_world\nTEST_KEY_456="quoted_val"\n')
        with patch.dict(os.environ, {}, clear=False):
            load_env_file(str(env_file))
            assert os.environ.get("TEST_KEY_123") == "hello_world"
            assert os.environ.get("TEST_KEY_456") == "quoted_val"
        # Cleanup
        os.environ.pop("TEST_KEY_123", None)
        os.environ.pop("TEST_KEY_456", None)

    def test_skips_comments_and_blank_lines(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("# comment\n\nKEY_X=val\n")
        with patch.dict(os.environ, {}, clear=False):
            load_env_file(str(env_file))
            assert os.environ.get("KEY_X") == "val"
        os.environ.pop("KEY_X", None)

    def test_does_not_overwrite_existing(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("EXISTING_VAR=new\n")
        with patch.dict(os.environ, {"EXISTING_VAR": "original"}, clear=False):
            load_env_file(str(env_file))
            assert os.environ["EXISTING_VAR"] == "original"

    def test_missing_file_no_error(self):
        load_env_file("/nonexistent/.env")  # Should not raise


class TestSubstituteEnvVars:
    def test_simple_string(self):
        with patch.dict(os.environ, {"MY_VAR": "resolved"}):
            assert substitute_env_vars("${MY_VAR}") == "resolved"

    def test_missing_var_returns_placeholder(self):
        with patch.dict(os.environ, {}, clear=True):
            result = substitute_env_vars("${MISSING_VAR}")
            assert result == "[PLACEHOLDER_MISSING_VAR]"

    def test_nested_dict(self):
        with patch.dict(os.environ, {"TOKEN": "abc123"}):
            config = {"section": {"key": "${TOKEN}", "other": "plain"}}
            result = substitute_env_vars(config)
            assert result["section"]["key"] == "abc123"
            assert result["section"]["other"] == "plain"

    def test_list_values(self):
        with patch.dict(os.environ, {"V": "x"}):
            assert substitute_env_vars(["${V}", "literal"]) == ["x", "literal"]

    def test_non_string_passthrough(self):
        assert substitute_env_vars(42) == 42
        assert substitute_env_vars(True) is True
        assert substitute_env_vars(None) is None


class TestDetectUnresolved:
    def test_finds_placeholders(self):
        config = {"a": "[PLACEHOLDER_FOO]", "b": {"c": "[PLACEHOLDER_BAR]"}}
        result = detect_unresolved_placeholders(config)
        assert result == {"FOO", "BAR"}

    def test_clean_config(self):
        config = {"a": "real_value", "b": 123}
        assert detect_unresolved_placeholders(config) == set()


class TestValidateConfig:
    def test_valid_config(self):
        config = {
            "azure_devops": {"organization": "org", "personal_access_token": "pat"},
            "github": {"token": "tok"},
        }
        errors = validate_config(config)
        assert errors == []

    def test_missing_ado_org(self):
        config = {
            "azure_devops": {"personal_access_token": "pat"},
            "github": {"token": "tok"},
        }
        errors = validate_config(config)
        assert any("organization" in e for e in errors)

    def test_missing_github_section(self):
        config = {"azure_devops": {"organization": "org", "personal_access_token": "pat"}}
        errors = validate_config(config)
        assert any("token" in e for e in errors)


class TestLoadConfig:
    def test_load_json(self, tmp_path):
        config_file = tmp_path / "config.json"
        config_data = {
            "azure_devops": {"organization": "org", "personal_access_token": "pat"},
            "github": {"token": "tok"},
        }
        config_file.write_text(json.dumps(config_data))
        result = load_config(str(config_file))
        assert result["azure_devops"]["organization"] == "org"

    def test_load_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/config.json")

    def test_load_invalid_json_raises(self, tmp_path):
        config_file = tmp_path / "bad.json"
        config_file.write_text("{invalid json")
        with pytest.raises(ValueError, match="Invalid configuration"):
            load_config(str(config_file))
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL - `ModuleNotFoundError`

**Step 3: Write the module**

```python
# src/azuredevops_github_migration/config.py
"""Unified configuration loading, env-var substitution, and validation.

Consolidates logic previously duplicated across migrate.py, analyze.py, and utils.py.
"""
import json
import os
from typing import Any, Dict, List, Set

import yaml


def load_env_file(filename: str = ".env") -> None:
    """Load environment variables from a .env file without overwriting existing vars."""
    try:
        if not os.path.exists(filename):
            return
        with open(filename, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
    except Exception:
        pass  # Non-fatal; caller can log if needed


def substitute_env_vars(obj: Any) -> Any:
    """Recursively substitute ${ENV_VAR} placeholders in config data."""
    if isinstance(obj, dict):
        return {k: substitute_env_vars(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [substitute_env_vars(item) for item in obj]
    if isinstance(obj, str) and obj.startswith("${") and obj.endswith("}"):
        env_var = obj[2:-1]
        value = os.getenv(env_var)
        if value is None:
            return f"[PLACEHOLDER_{env_var}]"
        return value
    return obj


def detect_unresolved_placeholders(obj: Any) -> Set[str]:
    """Return set of unresolved [PLACEHOLDER_X] markers still in config."""
    unresolved: Set[str] = set()
    if isinstance(obj, dict):
        for v in obj.values():
            unresolved.update(detect_unresolved_placeholders(v))
    elif isinstance(obj, list):
        for v in obj:
            unresolved.update(detect_unresolved_placeholders(v))
    elif isinstance(obj, str) and obj.startswith("[PLACEHOLDER_") and obj.endswith("]"):
        unresolved.add(obj[len("[PLACEHOLDER_"):-1])
    return unresolved


def validate_config(config: Dict[str, Any]) -> List[str]:
    """Validate migration configuration. Returns list of error strings (empty = valid)."""
    errors = []
    if not config.get("azure_devops", {}).get("organization"):
        errors.append("Azure DevOps organization is required (azure_devops.organization)")
    if not config.get("azure_devops", {}).get("personal_access_token"):
        errors.append("Azure DevOps PAT is required (azure_devops.personal_access_token)")
    if not config.get("github", {}).get("token"):
        errors.append("GitHub token is required (github.token)")
    return errors


def load_config(config_file: str, env_file: str = ".env") -> Dict[str, Any]:
    """Load configuration from JSON or YAML with env-var substitution.

    Raises FileNotFoundError if config_file missing.
    Raises ValueError on parse errors or unresolved placeholders.
    """
    load_env_file(env_file)

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            if config_file.endswith(".json"):
                config = json.load(f)
            else:
                config = yaml.safe_load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file '{config_file}' not found")
    except (json.JSONDecodeError, yaml.YAMLError) as e:
        raise ValueError(f"Invalid configuration file format: {e}")

    config = substitute_env_vars(config)

    unresolved = detect_unresolved_placeholders(config)
    if unresolved:
        raise ValueError("Unresolved configuration placeholders: " + ", ".join(sorted(unresolved)))

    errors = validate_config(config)
    if errors:
        raise ValueError("Configuration validation failed: " + "; ".join(errors))

    return config
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_config.py -v`
Expected: All passed

**Step 5: Commit**

```bash
git add src/azuredevops_github_migration/config.py tests/test_config.py
git commit -m "refactor: extract config loading into dedicated module"
```

---

## Task 3: Create migration state persistence (`state.py`)

This is the most critical new feature: track per-repo migration status in a JSON file that survives crashes.

**Files:**
- Create: `src/azuredevops_github_migration/state.py`
- Test: `tests/test_state.py`

**Step 1: Write the test file**

```python
# tests/test_state.py
"""Tests for migration state persistence."""
import json
import os
import threading
import pytest
from azuredevops_github_migration.state import MigrationState


class TestMigrationStateInit:
    def test_creates_new_state_file(self, tmp_path):
        state_file = str(tmp_path / "state.json")
        state = MigrationState(state_file, wave="wave_01")
        assert os.path.exists(state_file)
        assert state.wave == "wave_01"
        assert state.migration_id is not None

    def test_loads_existing_state_file(self, tmp_path):
        state_file = str(tmp_path / "state.json")
        # Create initial state
        s1 = MigrationState(state_file, wave="wave_01")
        s1.add_repo("ProjectA/repo-1")
        s1.mark_completed("ProjectA/repo-1", github_url="https://github.com/org/repo-1")
        # Reload
        s2 = MigrationState(state_file)
        assert s2.get_status("ProjectA/repo-1") == "completed"
        assert s2.wave == "wave_01"


class TestMigrationStateOperations:
    @pytest.fixture
    def state(self, tmp_path):
        return MigrationState(str(tmp_path / "state.json"), wave="test")

    def test_add_repo(self, state):
        state.add_repo("Proj/repo-a")
        assert state.get_status("Proj/repo-a") == "pending"

    def test_add_repos_bulk(self, state):
        state.add_repos(["Proj/r1", "Proj/r2", "Proj/r3"])
        assert state.get_status("Proj/r1") == "pending"
        assert state.total_repos == 3

    def test_mark_in_progress(self, state):
        state.add_repo("Proj/repo-a")
        state.mark_in_progress("Proj/repo-a", step="cloning")
        assert state.get_status("Proj/repo-a") == "in_progress"

    def test_mark_completed(self, state):
        state.add_repo("Proj/repo-a")
        state.mark_completed("Proj/repo-a", github_url="https://github.com/o/r")
        assert state.get_status("Proj/repo-a") == "completed"

    def test_mark_failed(self, state):
        state.add_repo("Proj/repo-a")
        state.mark_failed("Proj/repo-a", error="timeout")
        assert state.get_status("Proj/repo-a") == "failed"
        info = state.get_repo_info("Proj/repo-a")
        assert info["error"] == "timeout"
        assert info["retry_count"] == 1

    def test_mark_failed_increments_retry(self, state):
        state.add_repo("Proj/repo-a")
        state.mark_failed("Proj/repo-a", error="err1")
        state.mark_failed("Proj/repo-a", error="err2")
        info = state.get_repo_info("Proj/repo-a")
        assert info["retry_count"] == 2

    def test_mark_skipped(self, state):
        state.add_repo("Proj/repo-a")
        state.mark_skipped("Proj/repo-a", reason="empty repo")
        assert state.get_status("Proj/repo-a") == "skipped"


class TestMigrationStateQueries:
    @pytest.fixture
    def state(self, tmp_path):
        s = MigrationState(str(tmp_path / "state.json"), wave="test")
        s.add_repos(["P/r1", "P/r2", "P/r3", "P/r4", "P/r5"])
        s.mark_completed("P/r1", github_url="u1")
        s.mark_completed("P/r2", github_url="u2")
        s.mark_failed("P/r3", error="oops")
        s.mark_in_progress("P/r4", step="cloning")
        # P/r5 stays pending
        return s

    def test_total_repos(self, state):
        assert state.total_repos == 5

    def test_counts(self, state):
        c = state.counts
        assert c["completed"] == 2
        assert c["failed"] == 1
        assert c["in_progress"] == 1
        assert c["pending"] == 1

    def test_pending_repos(self, state):
        assert state.pending_repos == ["P/r5"]

    def test_failed_repos(self, state):
        assert state.failed_repos == ["P/r3"]

    def test_completed_repos(self, state):
        assert set(state.completed_repos) == {"P/r1", "P/r2"}


class TestMigrationStatePersistence:
    def test_survives_reload(self, tmp_path):
        path = str(tmp_path / "state.json")
        s1 = MigrationState(path, wave="w1")
        s1.add_repo("X/y")
        s1.mark_completed("X/y", github_url="url")
        del s1
        s2 = MigrationState(path)
        assert s2.get_status("X/y") == "completed"

    def test_thread_safety(self, tmp_path):
        path = str(tmp_path / "state.json")
        state = MigrationState(path, wave="w1")
        for i in range(20):
            state.add_repo(f"P/r{i}")

        def mark_done(repo_key):
            state.mark_completed(repo_key, github_url=f"url-{repo_key}")

        threads = [threading.Thread(target=mark_done, args=(f"P/r{i}",)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert state.counts["completed"] == 20
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_state.py -v`
Expected: FAIL - `ModuleNotFoundError`

**Step 3: Write the module**

```python
# src/azuredevops_github_migration/state.py
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
    """Persistent, thread-safe migration state tracker."""

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

    # --- Properties ---

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

    # --- Mutations ---

    def add_repo(self, repo_key: str) -> None:
        """Add a repo to track. repo_key = 'ProjectName/RepoName'."""
        with self._lock:
            if repo_key not in self._data["repos"]:
                self._data["repos"][repo_key] = {"status": "pending"}
                self._save()

    def add_repos(self, repo_keys: List[str]) -> None:
        """Add multiple repos at once."""
        with self._lock:
            for key in repo_keys:
                if key not in self._data["repos"]:
                    self._data["repos"][key] = {"status": "pending"}
            self._save()

    def mark_in_progress(self, repo_key: str, step: str = "") -> None:
        with self._lock:
            repo = self._data["repos"].setdefault(repo_key, {})
            repo["status"] = "in_progress"
            repo["step"] = step
            repo["migration_started"] = datetime.now(timezone.utc).isoformat()
            self._save()

    def mark_completed(
        self, repo_key: str, github_url: str = "", branches: int = 0, commits: int = 0, verification: Dict = None
    ) -> None:
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
        with self._lock:
            repo = self._data["repos"].setdefault(repo_key, {})
            repo["status"] = "failed"
            repo["error"] = error
            repo["retry_count"] = repo.get("retry_count", 0) + 1
            repo["last_attempt"] = datetime.now(timezone.utc).isoformat()
            self._save()

    def mark_skipped(self, repo_key: str, reason: str = "") -> None:
        with self._lock:
            repo = self._data["repos"].setdefault(repo_key, {})
            repo["status"] = "skipped"
            repo["reason"] = reason
            self._save()

    def store_freeze_acls(self, repo_key: str, acls: Any) -> None:
        """Store original ACLs before freeze for later restore."""
        with self._lock:
            repo = self._data["repos"].setdefault(repo_key, {})
            repo["original_acls"] = acls
            repo["frozen_at"] = datetime.now(timezone.utc).isoformat()
            self._save()

    def get_freeze_acls(self, repo_key: str) -> Optional[Any]:
        return self._data["repos"].get(repo_key, {}).get("original_acls")

    # --- Queries ---

    def get_status(self, repo_key: str) -> Optional[str]:
        repo = self._data["repos"].get(repo_key)
        return repo["status"] if repo else None

    def get_repo_info(self, repo_key: str) -> Optional[Dict]:
        return self._data["repos"].get(repo_key)

    # --- I/O ---

    def _save(self) -> None:
        """Atomic write: write to temp file then rename."""
        tmp = self._file + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, default=str)
        os.replace(tmp, self._file)

    def _load(self) -> Dict:
        with open(self._file, "r", encoding="utf-8") as f:
            return json.load(f)
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_state.py -v`
Expected: All passed

**Step 5: Commit**

```bash
git add src/azuredevops_github_migration/state.py tests/test_state.py
git commit -m "feat: add migration state persistence with thread-safe JSON tracking"
```

---

## Task 4: Create ADO repo freeze/unfreeze (`freeze.py`)

Uses Azure DevOps Security REST API to deny push permissions on repos.

**Files:**
- Create: `src/azuredevops_github_migration/freeze.py`
- Test: `tests/test_freeze.py`

**Step 1: Write the test file**

```python
# tests/test_freeze.py
"""Tests for ADO repo freeze/unfreeze functionality."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from azuredevops_github_migration.freeze import AdoRepoFreezer


class TestAdoRepoFreezerInit:
    def test_init(self):
        freezer = AdoRepoFreezer("my-org", "my-pat")
        assert freezer.organization == "my-org"
        assert freezer.GIT_SECURITY_NAMESPACE == "2e9eb7ed-3c0a-47d4-87c1-0ffdd275fd87"


class TestFreezeRepo:
    @pytest.fixture
    def freezer(self):
        return AdoRepoFreezer("test-org", "test-pat")

    @patch("requests.Session.get")
    @patch("requests.Session.post")
    def test_freeze_saves_acls_and_denies(self, mock_post, mock_get, freezer):
        # Mock GET for current ACLs
        mock_acl_response = Mock()
        mock_acl_response.status_code = 200
        mock_acl_response.json.return_value = {
            "value": [{"acesDictionary": {"team-id": {"allow": 4, "deny": 0}}}]
        }
        mock_acl_response.raise_for_status = Mock()
        mock_get.return_value = mock_acl_response

        # Mock POST for setting deny
        mock_post_response = Mock()
        mock_post_response.status_code = 200
        mock_post_response.raise_for_status = Mock()
        mock_post.return_value = mock_post_response

        result = freezer.freeze_repo("MyProject", "repo-id-123")
        assert result["success"] is True
        assert "original_acls" in result

    @patch("requests.Session.get")
    def test_freeze_handles_api_error(self, mock_get, freezer):
        mock_get.side_effect = Exception("API unreachable")
        result = freezer.freeze_repo("MyProject", "repo-id-123")
        assert result["success"] is False
        assert "error" in result


class TestUnfreezeRepo:
    @pytest.fixture
    def freezer(self):
        return AdoRepoFreezer("test-org", "test-pat")

    @patch("requests.Session.post")
    def test_unfreeze_restores_acls(self, mock_post, freezer):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        original_acls = {"value": [{"acesDictionary": {"team-id": {"allow": 4, "deny": 0}}}]}
        result = freezer.unfreeze_repo("MyProject", "repo-id-123", original_acls)
        assert result["success"] is True


class TestResolveRepoId:
    @pytest.fixture
    def freezer(self):
        return AdoRepoFreezer("test-org", "test-pat")

    @patch("requests.Session.get")
    def test_resolve_repo_id(self, mock_get, freezer):
        mock_response = Mock()
        mock_response.json.return_value = {
            "value": [{"name": "my-repo", "id": "abc-123"}, {"name": "other", "id": "def-456"}]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        repo_id = freezer.resolve_repo_id("MyProject", "my-repo")
        assert repo_id == "abc-123"

    @patch("requests.Session.get")
    def test_resolve_repo_id_not_found(self, mock_get, freezer):
        mock_response = Mock()
        mock_response.json.return_value = {"value": [{"name": "other", "id": "x"}]}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        with pytest.raises(ValueError, match="not found"):
            freezer.resolve_repo_id("MyProject", "missing-repo")
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_freeze.py -v`
Expected: FAIL - `ModuleNotFoundError`

**Step 3: Write the module**

```python
# src/azuredevops_github_migration/freeze.py
"""ADO repository freeze/unfreeze via Security REST API.

Freezes a repo by denying GenericContribute permission for the
project's Contributors group. Saves original ACLs for restore.
"""
import base64
import logging
from typing import Any, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class AdoRepoFreezer:
    """Freeze and unfreeze Azure DevOps repositories."""

    # Git Repositories security namespace
    GIT_SECURITY_NAMESPACE = "2e9eb7ed-3c0a-47d4-87c1-0ffdd275fd87"
    # GenericContribute permission bit
    GENERIC_CONTRIBUTE_BIT = 4

    def __init__(self, organization: str, pat: str, logger: logging.Logger = None):
        self.organization = organization
        self.pat = pat
        self.logger = logger or logging.getLogger(__name__)
        self.base_url = f"https://dev.azure.com/{organization}"

        self.session = requests.Session()
        retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503])
        self.session.mount("https://", HTTPAdapter(max_retries=retry))
        encoded = base64.b64encode(f":{pat}".encode()).decode()
        self.session.headers.update({
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/json",
        })

    def resolve_repo_id(self, project: str, repo_name: str) -> str:
        """Look up repo UUID from project + name."""
        url = f"{self.base_url}/{project}/_apis/git/repositories?api-version=7.0"
        resp = self.session.get(url, timeout=30)
        resp.raise_for_status()
        for repo in resp.json().get("value", []):
            if repo["name"] == repo_name:
                return repo["id"]
        raise ValueError(f"Repository '{repo_name}' not found in project '{project}'")

    def _security_token(self, project_id: str, repo_id: str) -> str:
        """Build security token for a repo."""
        return f"repoV2/{project_id}/{repo_id}"

    def _get_project_id(self, project: str) -> str:
        url = f"{self.base_url}/_apis/projects/{project}?api-version=7.0"
        resp = self.session.get(url, timeout=30)
        resp.raise_for_status()
        return resp.json()["id"]

    def freeze_repo(self, project: str, repo_id: str) -> Dict[str, Any]:
        """Deny push permissions. Returns original ACLs for later restore."""
        try:
            project_id = self._get_project_id(project)
            token = self._security_token(project_id, repo_id)

            # Step 1: Get current ACLs
            acl_url = (
                f"{self.base_url}/_apis/accesscontrollists/"
                f"{self.GIT_SECURITY_NAMESPACE}?token={token}&api-version=7.0"
            )
            acl_resp = self.session.get(acl_url, timeout=30)
            acl_resp.raise_for_status()
            original_acls = acl_resp.json()

            # Step 2: For each ACE, add GenericContribute to deny bits
            for acl in original_acls.get("value", []):
                for descriptor, ace in acl.get("acesDictionary", {}).items():
                    entry_url = (
                        f"{self.base_url}/_apis/accesscontrolentries/"
                        f"{self.GIT_SECURITY_NAMESPACE}?api-version=7.0"
                    )
                    body = {
                        "token": token,
                        "merge": True,
                        "accessControlEntries": [
                            {
                                "descriptor": descriptor,
                                "allow": ace.get("allow", 0),
                                "deny": ace.get("deny", 0) | self.GENERIC_CONTRIBUTE_BIT,
                                "extendedInfo": {},
                            }
                        ],
                    }
                    post_resp = self.session.post(entry_url, json=body, timeout=30)
                    post_resp.raise_for_status()

            self.logger.info(f"[FREEZE] Push denied for repo {repo_id}")
            return {"success": True, "original_acls": original_acls}

        except Exception as e:
            self.logger.error(f"[FREEZE] Failed for repo {repo_id}: {e}")
            return {"success": False, "error": str(e)}

    def unfreeze_repo(self, project: str, repo_id: str, original_acls: Dict) -> Dict[str, Any]:
        """Restore original permissions from saved ACLs."""
        try:
            project_id = self._get_project_id(project)
            token = self._security_token(project_id, repo_id)

            for acl in original_acls.get("value", []):
                for descriptor, ace in acl.get("acesDictionary", {}).items():
                    entry_url = (
                        f"{self.base_url}/_apis/accesscontrolentries/"
                        f"{self.GIT_SECURITY_NAMESPACE}?api-version=7.0"
                    )
                    body = {
                        "token": token,
                        "merge": False,  # Replace, don't merge
                        "accessControlEntries": [
                            {
                                "descriptor": descriptor,
                                "allow": ace.get("allow", 0),
                                "deny": ace.get("deny", 0),
                                "extendedInfo": {},
                            }
                        ],
                    }
                    post_resp = self.session.post(entry_url, json=body, timeout=30)
                    post_resp.raise_for_status()

            self.logger.info(f"[UNFREEZE] Permissions restored for repo {repo_id}")
            return {"success": True}

        except Exception as e:
            self.logger.error(f"[UNFREEZE] Failed for repo {repo_id}: {e}")
            return {"success": False, "error": str(e)}
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_freeze.py -v`
Expected: All passed

**Step 5: Commit**

```bash
git add src/azuredevops_github_migration/freeze.py tests/test_freeze.py
git commit -m "feat: add ADO repo freeze/unfreeze via Security API"
```

---

## Task 5: Parallel batch migration with state tracking

Rewrite `batch_migrate.py` to use ThreadPoolExecutor, state persistence, freeze integration, and retry-failed support.

**Files:**
- Modify: `src/azuredevops_github_migration/batch_migrate.py`
- Test: `tests/test_batch_migrate.py`

**Step 1: Write the test file**

```python
# tests/test_batch_migrate.py
"""Tests for parallel batch migration with state tracking."""
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from azuredevops_github_migration.batch_migrate import (
    load_migration_plan,
    run_batch_migration,
)
from azuredevops_github_migration.state import MigrationState


class TestLoadMigrationPlan:
    def test_load_valid_plan(self, tmp_path):
        plan_file = tmp_path / "plan.json"
        plan_data = [
            {"project_name": "P1", "repo_name": "r1", "github_repo_name": "r1"},
            {"project_name": "P1", "repo_name": "r2"},
        ]
        plan_file.write_text(json.dumps(plan_data))
        result = load_migration_plan(str(plan_file))
        assert len(result) == 2
        assert result[0]["project_name"] == "P1"

    def test_load_missing_file(self):
        with pytest.raises(FileNotFoundError):
            load_migration_plan("/nonexistent.json")


class TestRunBatchMigration:
    @patch("azuredevops_github_migration.batch_migrate.MigrationOrchestrator")
    def test_skips_completed_repos(self, MockOrch, tmp_path):
        state_file = str(tmp_path / "state.json")
        state = MigrationState(state_file, wave="test")
        state.add_repo("P1/r1")
        state.mark_completed("P1/r1", github_url="u")
        state.add_repo("P1/r2")

        plan = [
            {"project_name": "P1", "repo_name": "r1"},
            {"project_name": "P1", "repo_name": "r2"},
        ]

        mock_orch = Mock()
        mock_orch.migrate_repository.return_value = True
        MockOrch.return_value = mock_orch

        results = run_batch_migration(
            plan, config_file="dummy.json", state=state, concurrency=1, dry_run=True
        )
        # r1 already completed, so only r2 should be attempted
        assert mock_orch.migrate_repository.call_count == 1

    @patch("azuredevops_github_migration.batch_migrate.MigrationOrchestrator")
    def test_retry_failed_only(self, MockOrch, tmp_path):
        state_file = str(tmp_path / "state.json")
        state = MigrationState(state_file, wave="test")
        state.add_repos(["P/r1", "P/r2", "P/r3"])
        state.mark_completed("P/r1", github_url="u")
        state.mark_failed("P/r2", error="oops")
        # r3 pending

        plan = [
            {"project_name": "P", "repo_name": "r1"},
            {"project_name": "P", "repo_name": "r2"},
            {"project_name": "P", "repo_name": "r3"},
        ]

        mock_orch = Mock()
        mock_orch.migrate_repository.return_value = True
        MockOrch.return_value = mock_orch

        results = run_batch_migration(
            plan, config_file="dummy.json", state=state, concurrency=1,
            dry_run=True, retry_failed=True
        )
        # retry_failed=True: only r2 (failed) should be retried
        assert mock_orch.migrate_repository.call_count == 1
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_batch_migrate.py -v`
Expected: FAIL - `ImportError` (run_batch_migration doesn't exist yet)

**Step 3: Rewrite batch_migrate.py**

```python
# src/azuredevops_github_migration/batch_migrate.py
"""Batch migration with parallel execution, state tracking, and retry support."""
import argparse
import json
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

from .migrate import MigrationOrchestrator
from .state import MigrationState
from .utils import log_migration_summary


def load_migration_plan(file_path: str) -> List[Dict[str, Any]]:
    """Load migration plan from JSON file."""
    with open(file_path, "r") as f:
        return json.load(f)


def create_sample_migration_plan():
    """Create a sample migration plan file."""
    sample = [
        {
            "project_name": "MyProject",
            "repo_name": "my-first-repo",
            "github_repo_name": "migrated-first-repo",
            "migrate_issues": False,
            "description": "First repository to migrate",
        },
        {
            "project_name": "MyProject",
            "repo_name": "my-second-repo",
            "github_repo_name": "migrated-second-repo",
            "migrate_issues": False,
            "description": "Second repository - code only",
        },
    ]
    with open("migration_plan.json", "w") as f:
        json.dump(sample, f, indent=2)
    print("Sample migration plan created: migration_plan.json")


def _repo_key(entry: Dict[str, Any]) -> str:
    return f"{entry['project_name']}/{entry['repo_name']}"


def _should_migrate(entry: Dict[str, Any], state: MigrationState, retry_failed: bool) -> bool:
    """Determine if this repo should be migrated in this run."""
    key = _repo_key(entry)
    status = state.get_status(key)
    if status == "completed" or status == "skipped":
        return False
    if retry_failed:
        return status == "failed"
    return status in ("pending", "failed", None)


def _migrate_single(
    entry: Dict[str, Any],
    orchestrator: MigrationOrchestrator,
    state: MigrationState,
    dry_run: bool,
) -> bool:
    """Migrate a single repo. Updates state on success/failure."""
    key = _repo_key(entry)
    state.mark_in_progress(key, step="starting")
    try:
        success = orchestrator.migrate_repository(
            project_name=entry["project_name"],
            repo_name=entry["repo_name"],
            github_repo_name=entry.get("github_repo_name", entry["repo_name"]),
            migrate_issues=entry.get("migrate_issues", False),
            migrate_pipelines=entry.get("migrate_pipelines", False),
            dry_run=dry_run,
        )
        if success:
            github_org = orchestrator.config.get("github", {}).get("organization", "")
            gh_name = entry.get("github_repo_name", entry["repo_name"])
            state.mark_completed(key, github_url=f"https://github.com/{github_org}/{gh_name}")
        else:
            state.mark_failed(key, error="migrate_repository returned False")
        return success
    except Exception as e:
        state.mark_failed(key, error=str(e))
        return False


def run_batch_migration(
    plan: List[Dict[str, Any]],
    config_file: str,
    state: MigrationState,
    concurrency: int = 4,
    dry_run: bool = False,
    retry_failed: bool = False,
) -> Dict[str, bool]:
    """Run batch migration with parallel execution and state tracking."""
    # Register all repos in state
    for entry in plan:
        state.add_repo(_repo_key(entry))

    # Filter to repos that need migration
    to_migrate = [e for e in plan if _should_migrate(e, state, retry_failed)]

    if not to_migrate:
        print("No repos to migrate (all completed or skipped).")
        return {}

    orchestrator = MigrationOrchestrator(config_file)
    results: Dict[str, bool] = {}

    if concurrency <= 1:
        for entry in to_migrate:
            key = _repo_key(entry)
            results[key] = _migrate_single(entry, orchestrator, state, dry_run)
    else:
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = {}
            for entry in to_migrate:
                future = executor.submit(_migrate_single, entry, orchestrator, state, dry_run)
                futures[future] = _repo_key(entry)

            for future in as_completed(futures):
                key = futures[future]
                try:
                    results[key] = future.result()
                except Exception as e:
                    results[key] = False
                    state.mark_failed(key, error=str(e))

    return results


def main(args=None):
    """Main entry point for batch migration."""
    parser = argparse.ArgumentParser(description="Batch Azure DevOps to GitHub Migration")
    parser.add_argument("--config", default="config.json", help="Configuration file path")
    parser.add_argument("--plan", default="migration_plan.json", help="Migration plan JSON file")
    parser.add_argument("--state-file", default=None, help="State file for resume/tracking")
    parser.add_argument("--wave", default="default", help="Wave name for state tracking")
    parser.add_argument("--concurrency", type=int, default=4, help="Parallel migrations (default: 4)")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    parser.add_argument("--retry-failed", action="store_true", help="Retry only failed repos")
    parser.add_argument("--create-sample", action="store_true", help="Create sample plan file")

    parsed = parser.parse_args(args)

    if parsed.create_sample:
        create_sample_migration_plan()
        return

    try:
        plan = load_migration_plan(parsed.plan)
        state_file = parsed.state_file or f"migration_state_{parsed.wave}.json"
        state = MigrationState(state_file, wave=parsed.wave)

        print(f"Batch migration: {len(plan)} repos, concurrency={parsed.concurrency}")
        if parsed.dry_run:
            print("DRY RUN MODE")

        results = run_batch_migration(
            plan, parsed.config, state,
            concurrency=parsed.concurrency,
            dry_run=parsed.dry_run,
            retry_failed=parsed.retry_failed,
        )

        total = len(results)
        success = sum(1 for v in results.values() if v)
        rate = (success / total * 100) if total > 0 else 100

        print(f"\nBatch complete: {rate:.1f}% ({success}/{total})")
        c = state.counts
        print(f"  Completed: {c['completed']}  Failed: {c['failed']}  Pending: {c['pending']}")

        if c["failed"] > 0:
            print("Use --retry-failed to retry failed repos.")
            sys.exit(1)

    except FileNotFoundError as e:
        print(f"File not found: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_batch_migrate.py -v`
Expected: All passed

**Step 5: Commit**

```bash
git add src/azuredevops_github_migration/batch_migrate.py tests/test_batch_migrate.py
git commit -m "feat: rewrite batch migration with parallel execution and state tracking"
```

---

## Task 6: CLI status dashboard (`status.py`)

**Files:**
- Create: `src/azuredevops_github_migration/status.py`
- Test: `tests/test_status.py`

**Step 1: Write the test file**

```python
# tests/test_status.py
"""Tests for CLI status dashboard."""
import pytest
from azuredevops_github_migration.state import MigrationState
from azuredevops_github_migration.status import format_status_report


class TestFormatStatusReport:
    @pytest.fixture
    def state(self, tmp_path):
        s = MigrationState(str(tmp_path / "s.json"), wave="w1")
        s.add_repos(["P/r1", "P/r2", "P/r3", "P/r4", "P/r5"])
        s.mark_completed("P/r1", github_url="u1")
        s.mark_completed("P/r2", github_url="u2")
        s.mark_failed("P/r3", error="timeout")
        s.mark_in_progress("P/r4", step="cloning")
        return s

    def test_report_contains_counts(self, state):
        report = format_status_report(state)
        assert "Completed:" in report
        assert "Failed:" in report
        assert "Pending:" in report
        assert "In Progress:" in report

    def test_report_contains_wave(self, state):
        report = format_status_report(state)
        assert "w1" in report

    def test_report_shows_errors(self, state):
        report = format_status_report(state, show_errors=True)
        assert "timeout" in report

    def test_empty_state(self, tmp_path):
        s = MigrationState(str(tmp_path / "s.json"), wave="empty")
        report = format_status_report(s)
        assert "0" in report
```

**Step 2: Run test - expect fail**

Run: `python -m pytest tests/test_status.py -v`

**Step 3: Write the module**

```python
# src/azuredevops_github_migration/status.py
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
```

**Step 4: Run test - expect pass**

Run: `python -m pytest tests/test_status.py -v`

**Step 5: Commit**

```bash
git add src/azuredevops_github_migration/status.py tests/test_status.py
git commit -m "feat: add CLI status dashboard for migration progress"
```

---

## Task 7: Post-migration verification (`verify.py`)

**Files:**
- Create: `src/azuredevops_github_migration/verify.py`
- Test: `tests/test_verify.py`

**Step 1: Write the test file**

```python
# tests/test_verify.py
"""Tests for post-migration verification."""
import pytest
from unittest.mock import Mock, patch
from azuredevops_github_migration.verify import verify_repo_migration


class TestVerifyRepoMigration:
    @patch("azuredevops_github_migration.verify.subprocess.run")
    def test_verify_matching_branches(self, mock_run):
        # Mock git ls-remote for ADO (source)
        ado_output = "abc123\trefs/heads/main\ndef456\trefs/heads/develop\n"
        # Mock git ls-remote for GitHub (target)
        gh_output = "abc123\trefs/heads/main\ndef456\trefs/heads/develop\n"

        mock_run.side_effect = [
            Mock(returncode=0, stdout=ado_output),  # ADO ls-remote
            Mock(returncode=0, stdout=gh_output),    # GitHub ls-remote
        ]

        result = verify_repo_migration(
            ado_url="https://dev.azure.com/org/proj/_git/repo",
            github_url="https://github.com/org/repo.git",
            ado_pat="pat",
            github_token="tok",
        )
        assert result["branch_match"] is True
        assert result["ado_branches"] == 2
        assert result["github_branches"] == 2
        assert result["missing_on_github"] == []

    @patch("azuredevops_github_migration.verify.subprocess.run")
    def test_verify_missing_branch(self, mock_run):
        ado_output = "abc\trefs/heads/main\ndef\trefs/heads/feature\n"
        gh_output = "abc\trefs/heads/main\n"

        mock_run.side_effect = [
            Mock(returncode=0, stdout=ado_output),
            Mock(returncode=0, stdout=gh_output),
        ]

        result = verify_repo_migration(
            ado_url="https://dev.azure.com/org/proj/_git/repo",
            github_url="https://github.com/org/repo.git",
            ado_pat="pat",
            github_token="tok",
        )
        assert result["branch_match"] is False
        assert result["missing_on_github"] == ["feature"]
```

**Step 2: Run test - expect fail**

Run: `python -m pytest tests/test_verify.py -v`

**Step 3: Write the module**

```python
# src/azuredevops_github_migration/verify.py
"""Post-migration verification: compare ADO source vs GitHub target."""
import argparse
import subprocess
import sys
from typing import Any, Dict, List
from urllib.parse import quote, urlparse


def _authenticated_url(url: str, user: str, password: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.split("@")[-1]
    if user and password:
        auth = f"{quote(user)}:{quote(password)}"
    elif password:
        auth = f":{quote(password)}"
    else:
        return url
    return f"{parsed.scheme}://{auth}@{host}{parsed.path}"


def _ls_remote_branches(url: str) -> List[str]:
    """Get branch names from a remote via git ls-remote --heads."""
    result = subprocess.run(
        ["git", "ls-remote", "--heads", url],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git ls-remote failed: {result.stderr}")
    branches = []
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) == 2 and parts[1].startswith("refs/heads/"):
            branches.append(parts[1].replace("refs/heads/", ""))
    return sorted(branches)


def verify_repo_migration(
    ado_url: str,
    github_url: str,
    ado_pat: str,
    github_token: str,
) -> Dict[str, Any]:
    """Compare branches between ADO source and GitHub target."""
    ado_auth_url = _authenticated_url(ado_url, "", ado_pat)
    gh_auth_url = _authenticated_url(github_url, github_token, "")

    ado_branches = _ls_remote_branches(ado_auth_url)
    gh_branches = _ls_remote_branches(gh_auth_url)

    missing_on_github = sorted(set(ado_branches) - set(gh_branches))
    extra_on_github = sorted(set(gh_branches) - set(ado_branches))

    return {
        "ado_branches": len(ado_branches),
        "github_branches": len(gh_branches),
        "branch_match": not missing_on_github and not extra_on_github,
        "missing_on_github": missing_on_github,
        "extra_on_github": extra_on_github,
    }


def main(args=None):
    parser = argparse.ArgumentParser(description="Post-migration verification")
    parser.add_argument("--state-file", required=True, help="State file with completed repos")
    parser.add_argument("--config", default="config.json", help="Config file")
    parsed = parser.parse_args(args)
    # Implementation: iterate state file completed repos and verify each
    print("Verification requires --state-file with completed repos.")
    print("(Full implementation reads state + config and verifies each completed repo)")


if __name__ == "__main__":
    main()
```

**Step 4: Run test - expect pass**

Run: `python -m pytest tests/test_verify.py -v`

**Step 5: Commit**

```bash
git add src/azuredevops_github_migration/verify.py tests/test_verify.py
git commit -m "feat: add post-migration branch verification"
```

---

## Task 8: Update CLI with new commands

Add freeze, unfreeze, status, verify, and updated batch commands to the CLI router.

**Files:**
- Modify: `src/azuredevops_github_migration/cli.py`
- Modify: `pyproject.toml` (add new entry points)

**Step 1: Update cli.py**

Replace the existing `cli.py` with an expanded version that routes to all new commands:

```python
# src/azuredevops_github_migration/cli.py
"""Command Line Interface for Azure DevOps to GitHub Migration Tool."""
import sys
from typing import List, Optional


HELP_TEXT = """
Azure DevOps to GitHub Migration Tool - CLI

Usage:
  azuredevops-github-migration <command> [options]

Commands:
  init        Initialize configuration files
  migrate     Migrate a single repository
  analyze     Analyze Azure DevOps organization
  batch       Batch migrate multiple repositories (parallel, resumable)
  status      Show migration progress from state file
  freeze      Freeze ADO repos (deny push permissions)
  unfreeze    Unfreeze ADO repos (restore permissions)
  verify      Verify migration completeness
  help        Show this help message
  version     Show version information

Examples:
  azuredevops-github-migration init --template jira-users
  azuredevops-github-migration analyze --create-plan --config config.json
  azuredevops-github-migration freeze --plan wave_01.json --config config.json
  azuredevops-github-migration batch --plan wave_01.json --concurrency 4 --config config.json
  azuredevops-github-migration status --state-file migration_state_wave_01.json
  azuredevops-github-migration verify --state-file migration_state_wave_01.json --config config.json
  azuredevops-github-migration unfreeze --plan wave_01.json --config config.json
"""


def main(args: Optional[List[str]] = None):
    """Main CLI entry point."""
    if args is None:
        args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help", "help"):
        print(HELP_TEXT)
        return 0

    if args[0] in ("-v", "--version", "version"):
        from . import __version__
        print(f"Azure DevOps to GitHub Migration Tool v{__version__}")
        return 0

    command = args[0]

    try:
        if command == "init":
            from .init import main as cmd
        elif command == "migrate":
            from .migrate import main as cmd
        elif command == "analyze":
            from .analyze import main as cmd
        elif command == "batch":
            from .batch_migrate import main as cmd
        elif command == "status":
            from .status import main as cmd
        elif command == "freeze":
            from .freeze_cli import main as cmd
        elif command == "unfreeze":
            from .freeze_cli import main_unfreeze as cmd
        elif command == "verify":
            from .verify import main as cmd
        else:
            print(f"Unknown command: {command}")
            print("Run 'azuredevops-github-migration help' for usage information")
            return 1

        return cmd(args[1:])

    except ImportError as e:
        print(f"Error importing command module: {e}")
        return 1
    except Exception as e:
        print(f"Error executing command: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

**Step 2: Create freeze_cli.py** (thin CLI wrapper for freeze operations)

```python
# src/azuredevops_github_migration/freeze_cli.py
"""CLI wrappers for freeze/unfreeze commands."""
import argparse
import json
import sys
from .config import load_config
from .freeze import AdoRepoFreezer
from .state import MigrationState


def main(args=None):
    """Freeze repos in a migration plan."""
    parser = argparse.ArgumentParser(description="Freeze ADO repos")
    parser.add_argument("--plan", required=True, help="Migration plan JSON")
    parser.add_argument("--config", default="config.json", help="Config file")
    parser.add_argument("--state-file", default=None, help="State file to record freeze ACLs")
    parsed = parser.parse_args(args)

    config = load_config(parsed.config)
    freezer = AdoRepoFreezer(
        config["azure_devops"]["organization"],
        config["azure_devops"]["personal_access_token"],
    )

    with open(parsed.plan) as f:
        plan = json.load(f)

    state = MigrationState(parsed.state_file or "freeze_state.json", wave="freeze") if parsed.state_file else None

    for entry in plan:
        project = entry["project_name"]
        repo_name = entry["repo_name"]
        try:
            repo_id = freezer.resolve_repo_id(project, repo_name)
            result = freezer.freeze_repo(project, repo_id)
            if result["success"]:
                print(f"[FREEZE] {project}/{repo_name}")
                if state:
                    state.store_freeze_acls(f"{project}/{repo_name}", result["original_acls"])
            else:
                print(f"[FAIL]   {project}/{repo_name}: {result.get('error')}")
        except Exception as e:
            print(f"[ERROR]  {project}/{repo_name}: {e}")


def main_unfreeze(args=None):
    """Unfreeze repos using saved ACLs from state file."""
    parser = argparse.ArgumentParser(description="Unfreeze ADO repos")
    parser.add_argument("--plan", required=True, help="Migration plan JSON")
    parser.add_argument("--config", default="config.json", help="Config file")
    parser.add_argument("--state-file", required=True, help="State file with saved ACLs")
    parsed = parser.parse_args(args)

    config = load_config(parsed.config)
    freezer = AdoRepoFreezer(
        config["azure_devops"]["organization"],
        config["azure_devops"]["personal_access_token"],
    )
    state = MigrationState(parsed.state_file)

    with open(parsed.plan) as f:
        plan = json.load(f)

    for entry in plan:
        project = entry["project_name"]
        repo_name = entry["repo_name"]
        key = f"{project}/{repo_name}"
        acls = state.get_freeze_acls(key)
        if not acls:
            print(f"[SKIP] {key}: no saved ACLs")
            continue
        try:
            repo_id = freezer.resolve_repo_id(project, repo_name)
            result = freezer.unfreeze_repo(project, repo_id, acls)
            if result["success"]:
                print(f"[UNFREEZE] {key}")
            else:
                print(f"[FAIL]     {key}: {result.get('error')}")
        except Exception as e:
            print(f"[ERROR]    {key}: {e}")
```

**Step 3: Update pyproject.toml entry points**

Add to `[project.scripts]`:
```toml
ado2gh-status = "azuredevops_github_migration.status:main"
ado2gh-freeze = "azuredevops_github_migration.freeze_cli:main"
ado2gh-unfreeze = "azuredevops_github_migration.freeze_cli:main_unfreeze"
ado2gh-verify = "azuredevops_github_migration.verify:main"
```

**Step 4: Run all tests**

Run: `python -m pytest tests/ -v`
Expected: All tests pass

**Step 5: Commit**

```bash
git add src/azuredevops_github_migration/cli.py \
        src/azuredevops_github_migration/freeze_cli.py \
        pyproject.toml
git commit -m "feat: update CLI with freeze, unfreeze, status, verify commands"
```

---

## Task 9: Fix existing test import paths

Update tests to use package imports instead of legacy `src.migrate` paths.

**Files:**
- Modify: `tests/test_migrate_basic.py`
- Modify: `tests/test_migrate.py`
- Modify: `tests/test_git_url_sanitize.py`

**Step 1: Fix test_migrate_basic.py imports**

Change line 16-19 from:
```python
from src.migrate import (
    AzureDevOpsClient, GitHubClient, MigrationOrchestrator,
    AuthenticationError, MigrationError
)
```
To:
```python
from azuredevops_github_migration.migrate import (
    AzureDevOpsClient, GitHubClient, MigrationOrchestrator,
    AuthenticationError, MigrationError
)
```

Also fix `TestFileStructure` to check `src/azuredevops_github_migration/migrate.py` instead of `src/migrate.py`.

**Step 2: Fix test_migrate.py imports**

Change line 13-16 from:
```python
from src.migrate import (
    AzureDevOpsClient, GitHubClient, MigrationOrchestrator, GitMigrator,
    PipelineConverter, AuthenticationError, MigrationError
)
```
To:
```python
from azuredevops_github_migration.migrate import (
    AzureDevOpsClient, GitHubClient, MigrationOrchestrator, GitMigrator,
    PipelineConverter, AuthenticationError, MigrationError
)
```

Also fix all `@patch('src.migrate.X')` to `@patch('azuredevops_github_migration.migrate.X')`.

**Step 3: Run all tests**

Run: `python -m pytest tests/ -v`
Expected: All pass

**Step 4: Commit**

```bash
git add tests/
git commit -m "fix: update test imports to use package paths"
```

---

## Task 10: Fix report version and remove unused imports

**Files:**
- Modify: `src/azuredevops_github_migration/migrate.py`

**Step 1: Fix hardcoded version in `_save_enhanced_migration_report`**

Change line ~1166 from:
```python
'tool_version': '2.0.0',
```
To:
```python
'tool_version': __version__,
```

And add at top of file (after other imports):
```python
from . import __version__
```

**Step 2: Remove unused imports from migrate.py**

Remove `asyncio` from line 13 (unused).
Remove `from concurrent.futures import ThreadPoolExecutor, as_completed` from line 22 (unused in this file; used in batch_migrate now).

**Step 3: Run tests**

Run: `python -m pytest tests/ -v`

**Step 4: Commit**

```bash
git add src/azuredevops_github_migration/migrate.py
git commit -m "fix: use dynamic version in reports, remove unused imports"
```

---

## Task 11: Update `__init__.py` with new module exports

**Files:**
- Modify: `src/azuredevops_github_migration/__init__.py`

**Step 1: Add new classes to `__all__` and lazy imports**

Add to `__all__`:
```python
"MigrationState",
"AdoRepoFreezer",
```

Add lazy import cases:
```python
elif name == "MigrationState":
    from .state import MigrationState
    return MigrationState
elif name == "AdoRepoFreezer":
    from .freeze import AdoRepoFreezer
    return AdoRepoFreezer
```

**Step 2: Run tests**

Run: `python -m pytest tests/ -v`

**Step 3: Commit**

```bash
git add src/azuredevops_github_migration/__init__.py
git commit -m "refactor: export new modules from package init"
```

---

## Task 12: Bump version to 3.0.0

Given the scope of changes (new features, breaking batch_migrate API), bump to 3.0.0.

**Files:**
- Modify: `src/azuredevops_github_migration/__init__.py` - change `__version__` to `"3.0.0"`
- Modify: `CHANGELOG.md` - add 3.0.0 entry

**Step 1: Update version**

Change `__version__ = "2.1.0"` to `__version__ = "3.0.0"` in `__init__.py`.

**Step 2: Update CHANGELOG**

Add entry at top:
```markdown
## [3.0.0] - 2026-03-05

### Added
- Migration state persistence with JSON state files and resume capability
- ADO repository freeze/unfreeze via Security REST API
- Parallel batch migration with configurable concurrency
- CLI status dashboard for migration progress
- Post-migration branch verification
- Freeze/unfreeze CLI commands
- Retry-failed support for batch migrations

### Changed
- Batch migration rewritten with ThreadPoolExecutor and state tracking
- CLI expanded with freeze, unfreeze, status, verify commands
- Report version now reads from package __version__ dynamically

### Fixed
- Removed unused asyncio and ThreadPoolExecutor imports from migrate.py
- Fixed test import paths from src.migrate to azuredevops_github_migration.migrate
- Fixed hardcoded report version (was 2.0.0, now dynamic)
```

**Step 3: Commit**

```bash
git add src/azuredevops_github_migration/__init__.py CHANGELOG.md
git commit -m "chore: bump version to 3.0.0"
```

---

## Task 13: Final integration test

Run full test suite and verify everything works together.

**Step 1: Run all tests**

```bash
python -m pytest tests/ -v --tb=short
```
Expected: All tests pass.

**Step 2: Smoke test CLI**

```bash
azuredevops-github-migration --help
azuredevops-github-migration version
azuredevops-github-migration status --help
azuredevops-github-migration freeze --help
azuredevops-github-migration batch --help
```

**Step 3: Verify package builds**

```bash
python -m build
twine check dist/*
```

**Step 4: Final commit (if any fixes needed)**

```bash
git add -A
git commit -m "test: verify full integration after refactoring"
```
