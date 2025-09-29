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

    class TestMigrationOrchestrator(unittest.TestCase):
        @patch(f"{PATCH_BASE}.AzureDevOpsClient")
        @patch(f"{PATCH_BASE}.GitHubClient")
        def test_init(self, mock_gh, mock_ado):
            tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
            json.dump(
                {
                    "azure_devops": {"organization": "o", "personal_access_token": "p"},
                    "github": {"token": "t"},
                },
                tmp,
            )
            tmp.close()
            try:
                orch = MigrationOrchestrator(tmp.name)
                self.assertIsNotNone(orch.config)
                mock_ado.assert_called_once()
                mock_gh.assert_called_once()
            finally:
                os.unlink(tmp.name)

    class TestErrors(unittest.TestCase):
        def test_auth_error(self):
            with self.assertRaises(AuthenticationError):
                raise AuthenticationError("x")

        def test_migration_error(self):
            with self.assertRaises(MigrationError):
                raise MigrationError("y")

    if __name__ == "__main__":  # pragma: no cover
        unittest.main(verbosity=2)
