# Testing Guide for Azure DevOps to GitHub Migration Tool

This guide covers comprehensive testing procedures for the migration tool to ensure reliability and correctness before production use.

## Test Suite Overview

The migration tool includes a comprehensive test suite (`test_migrate.py`) that covers:

- **Unit Tests**: Individual component functionality
- **Integration Tests**: End-to-end migration scenarios  
- **Error Handling**: Edge cases and failure scenarios
- **Security Tests**: Credential handling and data protection
- **Performance Tests**: Large repository handling

## Running Tests

### Prerequisites

```bash
# Install test dependencies
pip install -r requirements.txt

# Ensure Git is available
git --version
```

### Execute Test Suite

```bash
# Run all tests with detailed output
python test_migrate.py

# Run specific test class
python -m unittest test_migrate.TestAzureDevOpsClient -v

# Run tests with coverage (if coverage installed)
pip install coverage
coverage run test_migrate.py
coverage report -m
```

### Expected Output

```
test_add_auth_to_url (test_migrate.TestGitMigrator) ... ok
test_convert_pipeline_to_workflow (test_migrate.TestPipelineConverter) ... ok
test_create_repository_invalid_name (test_migrate.TestGitHubClient) ... ok
test_full_migration_dry_run (test_migrate.TestIntegrationScenarios) ... ok

============================================================
TESTS RUN: 25
FAILURES: 0
ERRORS: 0
SUCCESS RATE: 100.0%
============================================================
```

## Manual Testing Procedures

### 1. Credential Validation Testing

Test authentication with various credential scenarios:

```bash
# Valid credentials
azuredevops-github-migration migrate --validate-only --config config.json

# Invalid Azure DevOps PAT
azuredevops-github-migration migrate --validate-only --config invalid_azure_config.json

# Invalid GitHub token
azuredevops-github-migration migrate --validate-only --config invalid_github_config.json

# Missing organization access
azuredevops-github-migration migrate --validate-only --config no_access_config.json
```

**Expected Results:**
- ✅ Valid credentials: "All validations passed! Ready for migration."
- ❌ Invalid credentials: Specific error messages without credential exposure

### 2. Dry Run Testing

Test complete migration flow without making changes:

```bash
# Small repository dry run
azuredevops-github-migration migrate --project "TestProject" --repo "small-repo" --dry-run --config config.json

# Large repository dry run  
azuredevops-github-migration migrate --project "TestProject" --repo "large-repo" --dry-run --config config.json

# Repository with work items and pipelines
azuredevops-github-migration migrate --project "TestProject" --repo "full-repo" --dry-run --config config.json

# Jira users (work items automatically disabled)
azuredevops-github-migration migrate --project "TestProject" --repo "jira-repo" --dry-run --config examples/jira-users-config.json

# Pipeline scope control testing
azuredevops-github-migration migrate --project "TestProject" --repo "test-repo" --pipelines-scope repository --dry-run --config config.json

# Remote verification testing
azuredevops-github-migration migrate --project "TestProject" --repo "test-repo" --verify-remote --dry-run --config config.json
```

**Verify:**
- All steps show "[DRY RUN]" prefix
- No actual repositories created on GitHub
- No Git operations performed
- Reports generated with dry_run: true

### 3. Connection Testing

Test API connectivity and rate limits:

```bash
# Test connections only
python migrate.py --test-connections --config config.json

# List projects (tests Azure DevOps connection)
python migrate.py --list-projects --config config.json

# List repositories (tests project access)
python migrate.py --list-repos "MyProject" --config config.json
```

### 4. Configuration Testing

Test various configuration scenarios:

```bash
# JSON configuration
python migrate.py --config config.json --validate-only

# YAML configuration
python migrate.py --config config.yaml --validate-only

# Environment variable substitution
AZURE_DEVOPS_PAT="real_pat" GITHUB_TOKEN="real_token" \
python migrate.py --config env_config.json --validate-only

# Missing required fields
python migrate.py --config incomplete_config.json --validate-only
```

### 5. Error Scenario Testing

Test handling of various error conditions:

```bash
# Non-existent project
python migrate.py --project "NonExistent" --repo "test" --dry-run

# Non-existent repository
python migrate.py --project "RealProject" --repo "nonexistent" --dry-run

# Repository name conflicts
python migrate.py --project "Project" --repo "source" --github-repo "existing-repo" --dry-run

# Network timeout simulation (requires network manipulation)
# Use tools like tc or toxiproxy for network delay testing
```

## Integration Testing with Real Services

### Safe Testing Setup

1. **Create Test Organizations:**
   - Azure DevOps test organization with sample projects
   - GitHub test organization for target repositories

2. **Test Data Preparation:**
   ```bash
   # Create test repositories in Azure DevOps with:
   # - Small repository (< 10MB, few commits)
   # - Medium repository (100MB, moderate history) 
   # - Repository with work items
   # - Repository with pipelines
   # - Empty repository
   ```

3. **Isolated Testing:**
   ```bash
   # Use separate GitHub organization
   # Test with non-production Azure DevOps organization
   # Use dedicated test configuration files
   ```

### Integration Test Scenarios

#### Scenario 1: Small Repository Migration
```bash
python migrate.py \
  --project "TestProject" \
  --repo "small-test-repo" \
  --github-repo "migrated-small-repo" \
  --config test_config.json
```

**Validation:**
- Verify all Git history migrated
- Check all branches present
- Confirm work items became issues
- Validate pipeline conversion files created

#### Scenario 2: Large Repository Handling
```bash
python migrate.py \
  --project "TestProject" \
  --repo "large-test-repo" \
  --github-repo "migrated-large-repo" \
  --config test_config.json \
  --debug
```

**Validation:**
- Monitor memory usage during migration
- Check migration doesn't timeout
- Verify progress reporting works
- Confirm cleanup of temporary files

#### Scenario 3: Selective Migration
```bash
python migrate.py \
  --project "TestProject" \
  --repo "full-feature-repo" \
  --github-repo "selective-migration" \
  --no-issues \
  --no-pipelines \
  --config test_config.json
```

**Validation:**
- Only Git history migrated
- No GitHub issues created
- No workflow files generated

### Performance Testing

#### Memory Usage Testing
```bash
# Monitor memory during large repository migration
/usr/bin/time -v python migrate.py \
  --project "TestProject" \
  --repo "large-repo" \
  --dry-run \
  --config test_config.json
```

#### Concurrent Migration Testing
```bash
# Test multiple migrations simultaneously
azuredevops-github-migration batch \
  --plan concurrent_test_plan.json \
  --dry-run
```

#### Rate Limit Testing
```bash
# Configure aggressive rate limits and test backoff
# Modify config.json:
{
  "rate_limiting": {
    "azure_devops_requests_per_second": 1,
    "github_requests_per_second": 1
  }
}

azuredevops-github-migration migrate --project "Test" --repo "test" --dry-run --debug --config test_config.json
```

## Security Testing

### Credential Security Tests

1. **Log File Analysis:**
   ```bash
   # Run migration and check logs for credential exposure
   azuredevops-github-migration migrate --project "Test" --repo "test" --dry-run --debug --config config.json
   grep -i "pat\|token\|password" migration.log
   # Should find no exposed credentials
   ```

2. **Configuration Security:**
   ```bash
   # Test environment variable substitution
   echo '{"github": {"token": "${GITHUB_TOKEN}"}}' > secure_test.json
   GITHUB_TOKEN="secret123" python migrate.py --config secure_test.json --validate-only
   ```

3. **Error Message Security:**
   ```bash
   # Trigger authentication errors and verify no credential leakage
   python migrate.py --config invalid_creds.json --validate-only 2>&1 | \
   grep -i "secret\|token\|pat"
   # Should return no matches
   ```

## Automated Test Pipeline

### GitHub Actions Workflow

```yaml
name: Migration Tool Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, 3.10, 3.11]
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install coverage
    
    - name: Run tests with coverage
      run: |
        coverage run test_migrate.py
        coverage report -m
        coverage xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

### Pre-commit Testing Hook

```bash
#!/bin/bash
# Save as .git/hooks/pre-commit

echo "Running migration tool tests..."
python test_migrate.py

if [ $? -ne 0 ]; then
    echo "Tests failed! Commit aborted."
    exit 1
fi

echo "All tests passed!"
```

## Test Data Management

### Mock Data Creation

```python
# Create mock Azure DevOps responses
def create_mock_work_items(count=10):
    return [
        {
            'id': i,
            'fields': {
                'System.Title': f'Test Work Item {i}',
                'System.Description': f'Description for item {i}',
                'System.WorkItemType': 'Task',
                'System.State': 'New'
            }
        }
        for i in range(1, count + 1)
    ]
```

### Test Repository Setup

```bash
# Create test repository with history
mkdir test-repo
cd test-repo
git init
echo "Initial commit" > README.md
git add . && git commit -m "Initial commit"

# Create branches and history
git checkout -b develop
echo "Feature work" > feature.txt
git add . && git commit -m "Add feature"

git checkout main
echo "Hotfix" >> README.md  
git add . && git commit -m "Hotfix"

git merge develop
```

## Troubleshooting Test Issues

### Common Test Failures

1. **Authentication Errors:**
   - Verify test credentials are valid
   - Check network connectivity
   - Ensure proper permissions

2. **Git Command Failures:**
   - Verify Git is installed and accessible
   - Check Git version compatibility
   - Ensure proper PATH configuration

3. **Mock Failures:**
   - Update mock responses to match current API versions
   - Verify mock setup in test methods
   - Check for changes in external dependencies

### Debug Test Execution

```bash
# Run single test with maximum verbosity
python -m unittest test_migrate.TestAzureDevOpsClient.test_get_projects_success -v

# Enable debug logging during tests
export LOG_LEVEL=DEBUG
python test_migrate.py

# Run tests with Python debugger
python -m pdb test_migrate.py
```

## Performance Benchmarks

### Expected Performance Metrics

| Repository Size | Migration Time | Memory Usage | Success Rate |
|----------------|----------------|--------------|--------------|
| < 10 MB | < 2 minutes | < 100 MB | 100% |
| 10-100 MB | < 10 minutes | < 200 MB | 99% |
| 100MB-1GB | < 30 minutes | < 500 MB | 95% |
| > 1 GB | Variable | Variable | 90% |

### Performance Test Commands

```bash
# Measure execution time and memory
/usr/bin/time -v python migrate.py \
  --project "PerfTest" \
  --repo "large-repo" \
  --dry-run 2>&1 | tee performance.log

# Extract metrics
grep "Maximum resident set size" performance.log
grep "Elapsed" performance.log
```

## Test Reporting

### Generate Test Report

```bash
# Run tests and generate detailed report
python test_migrate.py > test_results.txt 2>&1

# Create HTML report (with coverage)
coverage html
# Open htmlcov/index.html in browser
```

### Continuous Integration Reporting

Test results should be integrated into CI/CD pipelines with:
- Test pass/fail status
- Coverage percentage
- Performance regression detection
- Security scan results

This comprehensive testing approach ensures the migration tool is reliable, secure, and ready for production use.