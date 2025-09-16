# Repository Guidelines

## Project Structure & Module Organization
- Source lives in `src/azuredevops_github_migration/` (CLI entry points: `cli.py`, `migrate.py`, `analyze.py`, `doctor.py`, `interactive.py`, `quickstart.py`).
- Tests are in `tests/` (`test_*.py`). Keep unit tests close to modules they cover.
- Supporting folders: `docs/` (user guides), `examples/`, `scripts/`, `config/`. Generated outputs go to `migration_reports/` and logs in repo root; do not commit local artifacts.
- Packaging via `pyproject.toml`/`setuptools`; GitHub workflows live in `.github/`.

## Build, Test, and Development Commands
- Environment setup: `python -m venv venv && .\\venv\\Scripts\\Activate.ps1` (Windows) then `pip install -e .[dev]` and `pre-commit install`.
- Lint/format/type check: `black . && isort . && flake8 && mypy src`.
- Run tests: `pytest -q` or `pytest --cov=src --cov-report=term-missing`.
- CLI usage: `azuredevops-github-migration --help`, `ado2gh-analyze`, `ado2gh-migrate`, `ado2gh-batch`, `ado2gh-doctor`. Alternative: `python -m azuredevops_github_migration`.

## Coding Style & Naming Conventions
- Python 3.8+; 4-space indent; PEP8/PEP257 docstrings.
- Formatting: Black (88 chars) and isort (profile "black"). Keep imports grouped and sorted.
- Naming: modules/files `snake_case.py`; functions/vars `snake_case`; classes `CamelCase`. CLI command names are kebab-case.
- Type hints encouraged; keep public functions typed and covered by tests.

## Testing Guidelines
- Framework: `pytest` with config in `pyproject.toml`. Test files match `tests/test_*.py`; test functions `test_*`.
- Prefer isolated unit tests; mock external network/process calls. Add regression tests for fixes.
- Measure coverage with `pytest --cov`. Include edge cases for CLI flags and config parsing.

## Commit & Pull Request Guidelines
- Use Conventional Commits: `feat:`, `fix:`, `docs:`, `chore:` with optional scope, e.g., `feat(quickstart): add project paginator`.
- PRs must: describe changes, link issues, include verification steps (commands/output), update docs/`.env.example` when configs change, and add/adjust tests. Ensure `pre-commit` and CI pass.

## Security & Configuration Tips
- Never commit secrets. Copy `.env.example` to `.env` and set tokens locally; keep backups as `*.bak` (already gitignored). Update `config.json` locally.
- Validate environments with `ado2gh-doctor --skip-network` before running migrations. Run `bandit -r src` and `safety check` locally.
