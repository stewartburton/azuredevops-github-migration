"""Global naming normalization utilities for repositories and workflow filenames.

This centralizes normalization logic so behavior is consistent and configurable.
"""
from __future__ import annotations
import re
from typing import Dict, Set

DEFAULT_WORKFLOW_MAX = 50
ALLOWED_CHARS_PATTERN = re.compile(r'[^A-Za-z0-9._-]')


def _apply_basic(raw: str) -> str:
    return raw.strip()

def normalize_repo_name(raw: str, config: Dict | None = None) -> str:
    if not raw:
        return 'repo'
    cfg = (config or {}).get('naming', {}).get('repository', {})
    whitespace_strategy = cfg.get('whitespace_strategy', 'underscore')  # or 'dash'
    force_lower = cfg.get('force_lowercase', False)
    name = _apply_basic(raw)
    if whitespace_strategy == 'dash':
        name = re.sub(r'\s+', '-', name)
    else:
        name = re.sub(r'\s+', '_', name)
    # Leave other characters as-is; GitHub validation happens elsewhere
    if force_lower:
        name = name.lower()
    return name

def normalize_workflow_stem(raw: str, existing: Set[str], config: Dict | None = None) -> str:
    if not raw:
        raw = 'workflow'
    cfg = (config or {}).get('naming', {}).get('workflow', {})
    sep = cfg.get('separator', '-')
    lower = cfg.get('lowercase', True)
    max_len = int(cfg.get('max_length', DEFAULT_WORKFLOW_MAX))

    # 1. Trim
    stem = _apply_basic(raw)
    # 2. Whitespace collapse
    stem = re.sub(r'\s+', sep, stem)
    # 3. Disallowed chars -> sep
    stem = ALLOWED_CHARS_PATTERN.sub(sep, stem)
    # 4. Collapse multiple separators
    pattern_multi = re.compile(re.escape(sep) + r'{2,}')
    stem = pattern_multi.sub(sep, stem)
    # 5. Strip leading/trailing separators or periods
    stem = stem.strip(sep + '.-_')
    if not stem:
        stem = 'workflow'
    # 6. Case
    if lower:
        stem = stem.lower()
    # 7. Truncate (reserve space for potential suffix if collision later)
    if len(stem) > max_len:
        stem = stem[:max_len]

    base = stem
    counter = 1
    while stem in existing:
        counter += 1
        suffix = f"{sep}{counter}"
        limit = max_len - len(suffix)
        trimmed = base[:limit] if limit > 0 else base
        stem = f"{trimmed}{suffix}"
    existing.add(stem)
    return stem

__all__ = [
    'normalize_repo_name',
    'normalize_workflow_stem'
]
