import logging

try:
    from azuredevops_github_migration.migrate import (
        AzureDevOpsClient,
        GitHubClient,
        GitMigrator,
    )
except ImportError:  # fallback for legacy layout
    from src.migrate import AzureDevOpsClient, GitHubClient, GitMigrator


class Dummy:
    pass


def test_sanitize_clone_url_removes_userinfo(monkeypatch):
    logger = logging.getLogger("test")
    dummy_azure = Dummy()
    dummy_azure.pat = "PAT"
    dummy_azure._get_repository_by_name = lambda p, r: None
    dummy_github = Dummy()
    dummy_github.token = "TOK"
    migrator = GitMigrator(dummy_azure, dummy_github, logger)

    url = "https://ORG@dev.azure.com/ORG/Project/_git/Repo"
    sanitized = migrator.sanitize_clone_url(url)
    assert "@" not in sanitized.split("//", 1)[1].split("/")[0]


def test_add_auth_to_url_no_double_userinfo(monkeypatch):
    logger = logging.getLogger("test")
    dummy_azure = Dummy()
    dummy_azure.pat = "PAT"
    dummy_azure._get_repository_by_name = lambda p, r: None
    dummy_github = Dummy()
    dummy_github.token = "TOK"
    migrator = GitMigrator(dummy_azure, dummy_github, logger)

    base = "https://dev.azure.com/ORG/Project/_git/Repo"
    authed = migrator._add_auth_to_url(base, "", "PAT")
    # Should contain exactly one '@'
    assert authed.count("@") == 1
    assert authed.startswith("https://:PAT@")
