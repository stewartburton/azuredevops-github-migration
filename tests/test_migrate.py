#!/usr/bin/env python3
"""Minimal clean tests for migrate module (final reset)."""
import json
import os
import tempfile
import unittest
from unittest.mock import Mock, patch

try:
    from azuredevops_github_migration.migrate import (
        AuthenticationError,
        AzureDevOpsClient,
        GitHubClient,
        GitMigrator,
        MigrationError,
        MigrationOrchestrator,
        PipelineConverter,
    )

    PATCH_BASE = "azuredevops_github_migration.migrate"
except ImportError:  # legacy fallback
    from src.migrate import (
        AuthenticationError,
        AzureDevOpsClient,
        GitHubClient,
        GitMigrator,
        MigrationError,
        MigrationOrchestrator,
        PipelineConverter,
    )

    PATCH_BASE = "src.migrate"


class TestAzureDevOpsClient(unittest.TestCase):
    @patch("requests.Session.get")
    def test_get_projects_success(self, mock_get):
        resp = Mock()
        resp.json.return_value = {"value": [{"name": "P1"}]}
        resp.raise_for_status.return_value = None
        mock_get.return_value = resp
        client = AzureDevOpsClient("org", "pat")
        self.assertEqual(client.get_projects()[0]["name"], "P1")


class TestGitHubClient(unittest.TestCase):
    def test_validate_repo_name(self):
        client = GitHubClient("tok", "org")
        self.assertTrue(client._validate_repo_name("good-repo"))
        self.assertFalse(client._validate_repo_name("bad repo"))


class TestGitMigrator(unittest.TestCase):
    def test_add_auth_to_url(self):
        migrator = GitMigrator(
            Mock(spec=AzureDevOpsClient), Mock(spec=GitHubClient), Mock()
        )
        self.assertEqual(
            migrator._add_auth_to_url("https://dev.azure.com/org/repo", "", "pat"),
            "https://:pat@dev.azure.com/org/repo",
        )


class TestPipelineConverter(unittest.TestCase):
    def test_sanitize_filename(self):
        conv = PipelineConverter(Mock())
        self.assertEqual(conv._sanitize_filename("My Pipeline"), "my-pipeline")
