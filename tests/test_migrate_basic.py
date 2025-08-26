#!/usr/bin/env python3
"""
Basic test suite for Azure DevOps to GitHub Migration Tool
"""

import unittest
import tempfile
import os
import json
from unittest.mock import Mock, patch
import requests


# Import main classes - handle import errors gracefully
try:
    from azuredevops_github_migration.migrate import (
        AzureDevOpsClient, GitHubClient, MigrationOrchestrator,
        AuthenticationError, MigrationError
    )
    IMPORTS_AVAILABLE = True
except ImportError:
    try:
        from src.migrate import (
            AzureDevOpsClient, GitHubClient, MigrationOrchestrator,
            AuthenticationError, MigrationError
        )
        IMPORTS_AVAILABLE = True
    except ImportError as e:
        print(f"Warning: Could not import migrate module: {e}")
        IMPORTS_AVAILABLE = False


class TestBasicFunctionality(unittest.TestCase):
    """Test basic functionality that doesn't require full imports."""
    
    def test_import_availability(self):
        """Test that required modules can be imported."""
        self.assertTrue(IMPORTS_AVAILABLE, "Main migrate module should be importable")
    
    def test_basic_requirements(self):
        """Test that basic Python requirements are met."""
        import sys
        self.assertGreaterEqual(sys.version_info[:2], (3, 8), "Python 3.8+ required")
        
        # Test required packages
        try:
            import requests
            import yaml
            import json
            import tqdm
        except ImportError as e:
            self.fail(f"Required package not available: {e}")


@unittest.skipUnless(IMPORTS_AVAILABLE, "migrate module not available")
class TestAzureDevOpsClient(unittest.TestCase):
    """Test Azure DevOps client functionality."""
    
    def setUp(self):
        if not IMPORTS_AVAILABLE:
            self.skipTest("migrate module not available")
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


@unittest.skipUnless(IMPORTS_AVAILABLE, "migrate module not available")
class TestGitHubClient(unittest.TestCase):
    """Test GitHub client functionality."""
    
    def setUp(self):
        if not IMPORTS_AVAILABLE:
            self.skipTest("migrate module not available")
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


@unittest.skipUnless(IMPORTS_AVAILABLE, "migrate module not available")
class TestConfigurationHandling(unittest.TestCase):
    """Test configuration handling."""
    
    def setUp(self):
        if not IMPORTS_AVAILABLE:
            self.skipTest("migrate module not available")
        # Create a temporary config file
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        config_data = {
            'azure_devops': {
                'organization': 'test-org',
                'personal_access_token': 'test-pat'
            },
            'github': {
                'token': 'test-token',
                'organization': 'test-github-org'
            },
            'logging': {
                'level': 'DEBUG',
                'console': False
            }
        }
        json.dump(config_data, self.temp_config)
        self.temp_config.close()
    
    def tearDown(self):
        if hasattr(self, 'temp_config'):
            os.unlink(self.temp_config.name)
    
    def test_environment_variable_substitution(self):
        """Test environment variable substitution."""
        orchestrator = MigrationOrchestrator.__new__(MigrationOrchestrator)
        
        # Test simple substitution with placeholder (no actual env var set)
        result = orchestrator._substitute_env_vars('${TEST_VAR}')
        self.assertEqual(result, '[PLACEHOLDER_TEST_VAR]')
        
        # Test nested dict substitution
        config = {
            'section': {
                'key': '${TEST_VAR}',
                'other_key': 'normal_value'
            }
        }
        result = orchestrator._substitute_env_vars(config)
        self.assertEqual(result['section']['key'], '[PLACEHOLDER_TEST_VAR]')
        self.assertEqual(result['section']['other_key'], 'normal_value')


class TestFileStructure(unittest.TestCase):
    """Test that required files exist and are valid."""
    
    def test_main_script_exists(self):
        """Test that migrate.py exists."""
        legacy = os.path.exists('src/migrate.py')
        new_path = os.path.exists('src/azuredevops_github_migration/migrate.py')
        self.assertTrue(legacy or new_path, "migrate module not found in expected locations")
    
    def test_config_template_exists(self):
        """Test that config template exists and is valid JSON."""
        self.assertTrue(os.path.exists('config/config.template.json'), "config/config.template.json should exist")
        
        with open('config/config.template.json', 'r') as f:
            try:
                json.load(f)
            except json.JSONDecodeError as e:
                self.fail(f"config/config.template.json is not valid JSON: {e}")
    
    def test_requirements_exists(self):
        """Test that requirements.txt exists."""
        self.assertTrue(os.path.exists('requirements.txt'), "requirements.txt should exist")
        
        with open('requirements.txt', 'r') as f:
            content = f.read()
            self.assertIn('requests', content)
            self.assertIn('pyyaml', content)
            self.assertIn('tqdm', content)
    
    def test_documentation_exists(self):
        """Test that key documentation files exist."""
        docs = ['README.md', 'docs/user-guide/HOW_TO_GUIDE.md', 'docs/user-guide/TESTING.md', 'docs/user-guide/PRE_MIGRATION_CHECKLIST.md']
        for doc in docs:
            self.assertTrue(os.path.exists(doc), f"{doc} should exist")


class TestScriptSyntax(unittest.TestCase):
    """Test that Python scripts have valid syntax."""
    
    def test_main_script_syntax(self):
        """Test that migrate.py has valid Python syntax."""
        import py_compile
        target = 'src/azuredevops_github_migration/migrate.py'
        if not os.path.exists(target):
            target = 'src/migrate.py'
        try:
            py_compile.compile(target, doraise=True)
        except py_compile.PyCompileError as e:
            self.fail(f"Syntax error in {target}: {e}")
    
    def test_utility_scripts_syntax(self):
        """Test that utility scripts have valid syntax."""
        scripts = ['src/analyze.py', 'src/batch_migrate.py', 'src/utils.py']
        for script in scripts:
            if os.path.exists(script):
                try:
                    import py_compile
                    py_compile.compile(script, doraise=True)
                except py_compile.PyCompileError as e:
                    self.fail(f"{script} has syntax errors: {e}")


if __name__ == '__main__':
    # Run basic tests first
    print("Running basic Azure DevOps to GitHub Migration Tool tests...")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestBasicFunctionality,
        TestFileStructure, 
        TestScriptSyntax
    ]
    
    # Add import-dependent tests if available
    if IMPORTS_AVAILABLE:
        test_classes.extend([
            TestAzureDevOpsClient,
            TestGitHubClient,
            TestConfigurationHandling
        ])
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, buffer=True)
    result = runner.run(suite)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"TESTS RUN: {result.testsRun}")
    print(f"FAILURES: {len(result.failures)}")
    print(f"ERRORS: {len(result.errors)}")
    print(f"SKIPPED: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
    success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100) if result.testsRun > 0 else 0
    print(f"SUCCESS RATE: {success_rate:.1f}%")
    print(f"{'='*60}")
    
    if not result.wasSuccessful():
        print("\nFAILURES AND ERRORS:")
        for test, error in result.failures + result.errors:
            print(f"- {test}: {error}")
    
    # Exit with proper code
    exit(0 if result.wasSuccessful() else 1)