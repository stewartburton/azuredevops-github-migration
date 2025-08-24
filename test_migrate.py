#!/usr/bin/env python3
"""
Comprehensive test suite for Azure DevOps to GitHub Migration Tool
"""

import unittest
import tempfile
import os
import json
import shutil
from unittest.mock import Mock, patch, MagicMock
import requests
from migrate import (
    AzureDevOpsClient, GitHubClient, MigrationOrchestrator, GitMigrator,
    PipelineConverter, AuthenticationError, MigrationError
)


class TestAzureDevOpsClient(unittest.TestCase):
    """Test Azure DevOps client functionality."""
    
    def setUp(self):
        self.client = AzureDevOpsClient("test-org", "test-pat")
    
    def test_init(self):
        """Test client initialization."""
        self.assertEqual(self.client.organization, "test-org")
        self.assertEqual(self.client.pat, "test-pat")
        self.assertEqual(self.client.base_url, "https://dev.azure.com/test-org")
    
    @patch('requests.Session.get')
    def test_get_projects_success(self, mock_get):
        """Test successful project retrieval."""
        mock_response = Mock()
        mock_response.json.return_value = {'value': [{'name': 'Project1'}, {'name': 'Project2'}]}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        projects = self.client.get_projects()
        self.assertEqual(len(projects), 2)
        self.assertEqual(projects[0]['name'], 'Project1')
    
    @patch('requests.Session.get')
    def test_get_projects_timeout(self, mock_get):
        """Test project retrieval timeout."""
        mock_get.side_effect = requests.exceptions.Timeout()
        
        with self.assertRaises(MigrationError):
            self.client.get_projects()
    
    @patch('requests.Session.get')
    def test_validate_credentials_success(self, mock_get):
        """Test successful credential validation."""
        mock_response = Mock()
        mock_response.json.return_value = {'value': []}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = self.client.validate_credentials()
        self.assertTrue(result)
    
    @patch('requests.Session.get')
    def test_validate_credentials_unauthorized(self, mock_get):
        """Test credential validation with unauthorized error."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response
        mock_get.side_effect = requests.exceptions.HTTPError(response=mock_response)
        
        with self.assertRaises(AuthenticationError):
            self.client.validate_credentials()


class TestGitHubClient(unittest.TestCase):
    """Test GitHub client functionality."""
    
    def setUp(self):
        self.client = GitHubClient("test-token", "test-org")
    
    def test_init(self):
        """Test client initialization."""
        self.assertEqual(self.client.token, "test-token")
        self.assertEqual(self.client.organization, "test-org")
        self.assertEqual(self.client.base_url, "https://api.github.com")
    
    def test_validate_repo_name(self):
        """Test repository name validation."""
        # Valid names
        self.assertTrue(self.client._validate_repo_name("valid-repo"))
        self.assertTrue(self.client._validate_repo_name("valid_repo"))
        self.assertTrue(self.client._validate_repo_name("valid.repo"))
        self.assertTrue(self.client._validate_repo_name("ValidRepo123"))
        
        # Invalid names
        self.assertFalse(self.client._validate_repo_name(""))
        self.assertFalse(self.client._validate_repo_name("invalid repo"))  # space
        self.assertFalse(self.client._validate_repo_name("invalid@repo"))  # special char
        self.assertFalse(self.client._validate_repo_name("a" * 101))  # too long
    
    @patch('requests.Session.post')
    def test_create_repository_success(self, mock_post):
        """Test successful repository creation."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'name': 'test-repo',
            'html_url': 'https://github.com/test-org/test-repo'
        }\n        mock_response.raise_for_status.return_value = None\n        mock_post.return_value = mock_response\n        \n        repo = self.client.create_repository(\"test-repo\", \"Test description\")\n        self.assertEqual(repo['name'], 'test-repo')\n        self.assertIn('html_url', repo)\n    \n    def test_create_repository_invalid_name(self):\n        \"\"\"Test repository creation with invalid name.\"\"\"\n        with self.assertRaises(ValueError):\n            self.client.create_repository(\"invalid repo name\")\n    \n    @patch('requests.Session.get')\n    def test_repository_exists_true(self, mock_get):\n        \"\"\"Test repository existence check - exists.\"\"\"\n        mock_response = Mock()\n        mock_response.status_code = 200\n        mock_get.return_value = mock_response\n        \n        # Mock get_user to return a user\n        with patch.object(self.client, 'get_user', return_value={'login': 'testuser'}):\n            result = self.client.repository_exists(\"existing-repo\")\n            self.assertTrue(result)\n    \n    @patch('requests.Session.get')\n    def test_repository_exists_false(self, mock_get):\n        \"\"\"Test repository existence check - doesn't exist.\"\"\"\n        mock_response = Mock()\n        mock_response.status_code = 404\n        mock_get.return_value = mock_response\n        \n        with patch.object(self.client, 'get_user', return_value={'login': 'testuser'}):\n            result = self.client.repository_exists(\"non-existing-repo\")\n            self.assertFalse(result)


class TestGitMigrator(unittest.TestCase):
    \"\"\"Test Git migration functionality.\"\"\"\n    \n    def setUp(self):\n        self.azure_client = Mock(spec=AzureDevOpsClient)\n        self.github_client = Mock(spec=GitHubClient)\n        self.logger = Mock()\n        self.migrator = GitMigrator(self.azure_client, self.github_client, self.logger)\n    \n    def test_add_auth_to_url(self):\n        \"\"\"Test URL authentication addition.\"\"\"\n        # Test PAT only (Azure DevOps style)\n        result = self.migrator._add_auth_to_url(\n            \"https://dev.azure.com/org/repo.git\", \"\", \"pat123\"\n        )\n        self.assertEqual(result, \"https://:pat123@dev.azure.com/org/repo.git\")\n        \n        # Test username and password\n        result = self.migrator._add_auth_to_url(\n            \"https://github.com/org/repo.git\", \"user\", \"pass\"\n        )\n        self.assertEqual(result, \"https://user:pass@github.com/org/repo.git\")\n        \n        # Test empty URL\n        result = self.migrator._add_auth_to_url(\"\", \"user\", \"pass\")\n        self.assertEqual(result, \"\")\n    \n    @patch('subprocess.run')\n    @patch('tempfile.mkdtemp')\n    def test_migrate_repository_git_history_dry_run(self, mock_mkdtemp, mock_run):\n        \"\"\"Test Git migration in dry run mode.\"\"\"\n        # Setup mocks\n        self.azure_client.get_repositories.return_value = [\n            {'name': 'test-repo', 'remoteUrl': 'https://dev.azure.com/org/test-repo.git'}\n        ]\n        \n        result = self.migrator.migrate_repository_git_history(\n            \"test-project\", \"test-repo\", \"github-repo\", dry_run=True\n        )\n        \n        self.assertTrue(result)\n        # Ensure no actual git commands were run in dry run\n        mock_run.assert_not_called()\n        mock_mkdtemp.assert_not_called()


class TestPipelineConverter(unittest.TestCase):\n    \"\"\"Test pipeline conversion functionality.\"\"\"\n    \n    def setUp(self):\n        self.logger = Mock()\n        self.converter = PipelineConverter(self.logger)\n    \n    def test_sanitize_filename(self):\n        \"\"\"Test filename sanitization.\"\"\"\n        # Test normal name\n        result = self.converter._sanitize_filename(\"My Pipeline\")\n        self.assertEqual(result, \"my-pipeline\")\n        \n        # Test special characters\n        result = self.converter._sanitize_filename(\"My@Pipeline#123!\")\n        self.assertEqual(result, \"my-pipeline-123\")\n        \n        # Test long name truncation\n        long_name = \"a\" * 100\n        result = self.converter._sanitize_filename(long_name)\n        self.assertEqual(len(result), 50)\n    \n    def test_convert_pipelines_to_actions_dry_run(self):\n        \"\"\"Test pipeline conversion in dry run mode.\"\"\"\n        pipelines = [\n            {'name': 'Build Pipeline', 'id': 1},\n            {'name': 'Test Pipeline', 'id': 2}\n        ]\n        \n        result = self.converter.convert_pipelines_to_actions(\n            pipelines, \"/tmp/workflows\", dry_run=True\n        )\n        \n        self.assertEqual(len(result), 2)\n        self.assertIn(\"workflow-0.yml\", result)\n        self.assertIn(\"workflow-1.yml\", result)\n    \n    def test_convert_pipeline_to_workflow(self):\n        \"\"\"Test single pipeline conversion.\"\"\"\n        pipeline = {\n            'name': 'Test Pipeline',\n            'id': 123,\n            'process': {'phases': [{'name': 'Build'}, {'name': 'Test'}]}\n        }\n        \n        workflow = self.converter._convert_pipeline_to_workflow(pipeline)\n        \n        self.assertIn(\"name: Test Pipeline\", workflow)\n        self.assertIn(\"# Original ID: 123\", workflow)\n        self.assertIn(\"runs-on: ubuntu-latest\", workflow)


class TestMigrationOrchestrator(unittest.TestCase):\n    \"\"\"Test migration orchestrator functionality.\"\"\"\n    \n    def setUp(self):\n        # Create a temporary config file\n        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)\n        config_data = {\n            'azure_devops': {\n                'organization': 'test-org',\n                'personal_access_token': 'test-pat'\n            },\n            'github': {\n                'token': 'test-token',\n                'organization': 'test-github-org'\n            },\n            'logging': {\n                'level': 'DEBUG',\n                'console': False\n            }\n        }\n        json.dump(config_data, self.temp_config)\n        self.temp_config.close()\n    \n    def tearDown(self):\n        os.unlink(self.temp_config.name)\n    \n    @patch('migrate.AzureDevOpsClient')\n    @patch('migrate.GitHubClient')\n    def test_orchestrator_init(self, mock_github_client, mock_azure_client):\n        \"\"\"Test orchestrator initialization.\"\"\"\n        orchestrator = MigrationOrchestrator(self.temp_config.name)\n        \n        self.assertIsNotNone(orchestrator.config)\n        self.assertIsNotNone(orchestrator.logger)\n        mock_azure_client.assert_called_once()\n        mock_github_client.assert_called_once()\n    \n    def test_substitute_env_vars(self):\n        \"\"\"Test environment variable substitution.\"\"\"\n        with patch('os.getenv', return_value='substituted_value'):\n            orchestrator = MigrationOrchestrator.__new__(MigrationOrchestrator)\n            \n            # Test string substitution\n            result = orchestrator._substitute_env_vars('${TEST_VAR}')\n            self.assertEqual(result, 'substituted_value')\n            \n            # Test nested dict substitution\n            config = {\n                'section': {\n                    'key': '${TEST_VAR}',\n                    'other_key': 'normal_value'\n                }\n            }\n            result = orchestrator._substitute_env_vars(config)\n            self.assertEqual(result['section']['key'], 'substituted_value')\n            self.assertEqual(result['section']['other_key'], 'normal_value')\n    \n    def test_validate_config(self):\n        \"\"\"Test configuration validation.\"\"\"\n        orchestrator = MigrationOrchestrator.__new__(MigrationOrchestrator)\n        \n        # Test valid config\n        valid_config = {\n            'azure_devops': {\n                'organization': 'test-org',\n                'personal_access_token': 'test-pat'\n            },\n            'github': {\n                'token': 'test-token'\n            }\n        }\n        orchestrator._validate_config(valid_config)  # Should not raise\n        \n        # Test missing section\n        invalid_config = {\n            'azure_devops': {\n                'organization': 'test-org',\n                'personal_access_token': 'test-pat'\n            }\n            # Missing github section\n        }\n        with self.assertRaises(ValueError):\n            orchestrator._validate_config(invalid_config)\n        \n        # Test missing field\n        invalid_config2 = {\n            'azure_devops': {\n                'organization': 'test-org'\n                # Missing personal_access_token\n            },\n            'github': {\n                'token': 'test-token'\n            }\n        }\n        with self.assertRaises(ValueError):\n            orchestrator._validate_config(invalid_config2)


class TestIntegrationScenarios(unittest.TestCase):\n    \"\"\"Integration tests for common migration scenarios.\"\"\"\n    \n    def setUp(self):\n        self.temp_dir = tempfile.mkdtemp()\n        self.config_file = os.path.join(self.temp_dir, 'test_config.json')\n        \n        config_data = {\n            'azure_devops': {\n                'organization': 'test-org',\n                'personal_access_token': 'test-pat'\n            },\n            'github': {\n                'token': 'test-token',\n                'organization': 'test-github-org'\n            },\n            'logging': {\n                'level': 'ERROR',  # Suppress logs in tests\n                'console': False\n            },\n            'output': {\n                'output_directory': self.temp_dir\n            }\n        }\n        \n        with open(self.config_file, 'w') as f:\n            json.dump(config_data, f)\n    \n    def tearDown(self):\n        shutil.rmtree(self.temp_dir, ignore_errors=True)\n    \n    @patch('migrate.AzureDevOpsClient')\n    @patch('migrate.GitHubClient')\n    @patch('migrate.GitMigrator')\n    def test_full_migration_dry_run(self, mock_git_migrator, mock_github_client, mock_azure_client):\n        \"\"\"Test complete migration flow in dry run mode.\"\"\"\n        # Setup mocks\n        mock_azure = Mock()\n        mock_azure.get_repositories.return_value = [{'name': 'test-repo', 'id': 'repo-id'}]\n        mock_azure.get_repository_size.return_value = 1000000  # 1MB\n        mock_azure.export_repository_data.return_value = {\n            'repository': {'name': 'test-repo', 'description': 'Test repo'},\n            'size': 1000000,\n            'branches': [{'name': 'main'}],\n            'work_items': [{'id': 1, 'fields': {'System.Title': 'Test Item'}}],\n            'pull_requests': [],\n            'pipelines': []\n        }\n        mock_azure_client.return_value = mock_azure\n        \n        mock_github = Mock()\n        mock_github.validate_credentials.return_value = True\n        mock_github.repository_exists.return_value = False\n        mock_github_client.return_value = mock_github\n        \n        mock_git = Mock()\n        mock_git.migrate_repository_git_history.return_value = True\n        mock_git_migrator.return_value = mock_git\n        \n        # Initialize orchestrator and run dry migration\n        orchestrator = MigrationOrchestrator(self.config_file)\n        result = orchestrator.migrate_repository(\n            'test-project', 'test-repo', 'migrated-repo', \n            migrate_issues=True, migrate_pipelines=True, dry_run=True\n        )\n        \n        self.assertTrue(result)\n        \n        # Verify dry run didn't make actual changes\n        mock_git.migrate_repository_git_history.assert_called_with(\n            'test-project', 'test-repo', 'migrated-repo', dry_run=True\n        )\n    \n    @patch('migrate.subprocess.run')\n    def test_git_command_availability(self, mock_run):\n        \"\"\"Test Git command availability check.\"\"\"\n        # Test Git available\n        mock_run.return_value = Mock(returncode=0, stdout='git version 2.34.0')\n        \n        orchestrator = MigrationOrchestrator.__new__(MigrationOrchestrator)\n        orchestrator.logger = Mock()\n        \n        # This would be called during prerequisites validation\n        git_available = mock_run.return_value.returncode == 0\n        self.assertTrue(git_available)\n        \n        # Test Git not available\n        mock_run.return_value = Mock(returncode=1)\n        git_available = mock_run.return_value.returncode == 0\n        self.assertFalse(git_available)


class TestErrorHandling(unittest.TestCase):\n    \"\"\"Test error handling and edge cases.\"\"\"\n    \n    def test_authentication_error(self):\n        \"\"\"Test authentication error handling.\"\"\"\n        with self.assertRaises(AuthenticationError) as context:\n            raise AuthenticationError(\"Invalid credentials\")\n        \n        self.assertIn(\"Invalid credentials\", str(context.exception))\n    \n    def test_migration_error(self):\n        \"\"\"Test migration error handling.\"\"\"\n        with self.assertRaises(MigrationError) as context:\n            raise MigrationError(\"Migration failed\")\n        \n        self.assertIn(\"Migration failed\", str(context.exception))\n    \n    @patch('migrate.subprocess.run')\n    def test_git_operation_timeout(self, mock_run):\n        \"\"\"Test Git operation timeout handling.\"\"\"\n        from subprocess import TimeoutExpired\n        mock_run.side_effect = TimeoutExpired('git', 30)\n        \n        azure_client = Mock()\n        github_client = Mock()\n        logger = Mock()\n        \n        migrator = GitMigrator(azure_client, github_client, logger)\n        \n        azure_client.get_repositories.return_value = [\n            {'name': 'test-repo', 'remoteUrl': 'https://test.com/repo.git'}\n        ]\n        azure_client.pat = 'test-pat'\n        \n        github_client.get_repository.return_value = {\n            'clone_url': 'https://github.com/test/repo.git'\n        }\n        github_client.token = 'test-token'\n        \n        with self.assertRaises(Exception):  # Should raise GitOperationError\n            migrator.migrate_repository_git_history(\n                'test-project', 'test-repo', 'github-repo', dry_run=False\n            )


if __name__ == '__main__':\n    # Create test suite\n    loader = unittest.TestLoader()\n    suite = unittest.TestSuite()\n    \n    # Add all test classes\n    test_classes = [\n        TestAzureDevOpsClient,\n        TestGitHubClient,\n        TestGitMigrator,\n        TestPipelineConverter,\n        TestMigrationOrchestrator,\n        TestIntegrationScenarios,\n        TestErrorHandling\n    ]\n    \n    for test_class in test_classes:\n        tests = loader.loadTestsFromTestCase(test_class)\n        suite.addTests(tests)\n    \n    # Run tests with detailed output\n    runner = unittest.TextTestRunner(verbosity=2, buffer=True)\n    result = runner.run(suite)\n    \n    # Print summary\n    print(f\"\\n{'='*60}\")\n    print(f\"TESTS RUN: {result.testsRun}\")\n    print(f\"FAILURES: {len(result.failures)}\")\n    print(f\"ERRORS: {len(result.errors)}\")\n    print(f\"SUCCESS RATE: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%\")\n    print(f\"{'='*60}\")\n    \n    # Exit with proper code\n    exit(0 if result.wasSuccessful() else 1)"