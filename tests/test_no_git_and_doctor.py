import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure local source is importable when package not installed editable
if 'azuredevops_github_migration' not in sys.modules:
    src_path = Path(__file__).resolve().parents[1] / 'src'
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))


class TestNoGitFlag(unittest.TestCase):
    def setUp(self):
        # Dynamically import after path is ready
        from azuredevops_github_migration.migrate import MigrationOrchestrator
        self.orchestrator_cls = MigrationOrchestrator

        # Minimal config written to temp file
        self.tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.json', mode='w', encoding='utf-8')
        json.dump({
            "azure_devops": {"organization": "org", "personal_access_token": "pat"},
            "github": {"token": "gh", "organization": "ghorg"},
            "logging": {"console": False},
            "output": {"output_directory": "./migration_reports"}
        }, self.tmp)
        self.tmp.close()

    def tearDown(self):
        try:
            os.unlink(self.tmp.name)
        except Exception:
            pass

    @patch('azuredevops_github_migration.migrate.MigrationOrchestrator._migrate_git_repository')
    @patch('azuredevops_github_migration.migrate.MigrationOrchestrator._setup_github_repository')
    @patch('azuredevops_github_migration.migrate.AzureDevOpsClient.export_repository_data')
    @patch('azuredevops_github_migration.migrate.MigrationOrchestrator._validate_repository_prerequisites')
    def test_no_git_skips_git_history(self, mock_validate, mock_export, mock_setup, mock_git):
        mock_validate.return_value = True
        mock_export.return_value = {
            'repository': {'name': 'repo'},
            'branches': [], 'pull_requests': [], 'work_items': [], 'pipelines': [], 'size': 0
        }
        mock_setup.return_value = {'name': 'repo'}

        orch = self.orchestrator_cls(self.tmp.name)
        # Inject args with no_git True
        class Args: no_git = True; verify_remote = False
        orch.args = Args()
        ok = orch.migrate_repository('proj', 'repo', migrate_issues=False, migrate_pipelines=False, dry_run=True)
        self.assertTrue(ok)
        mock_git.assert_not_called()


class TestDoctorCommand(unittest.TestCase):
    def test_doctor_runs(self):
        from azuredevops_github_migration import doctor
        rc = doctor.main(['--json'])
        self.assertIn(rc, (0, 1))  # 1 allowed if git missing in CI


if __name__ == '__main__':  # pragma: no cover
    unittest.main()
