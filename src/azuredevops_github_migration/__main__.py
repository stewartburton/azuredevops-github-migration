"""Module entry point for `python -m azuredevops_github_migration`.

This delegates to the package CLI dispatcher so users have an
alternative invocation style beyond the installed console script.
"""

from .cli import main


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
