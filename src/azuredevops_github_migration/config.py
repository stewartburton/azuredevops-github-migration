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
        pass


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
    """Load config from JSON or YAML with env-var substitution.

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
        raise ValueError(
            "Unresolved configuration placeholders: " + ", ".join(sorted(unresolved))
        )

    errors = validate_config(config)
    if errors:
        raise ValueError("Configuration validation failed: " + "; ".join(errors))

    return config
