import pytest
from azuredevops_github_migration import naming

def test_workflow_normalization_basic():
    seen = set()
    stem = naming.normalize_workflow_stem('Build & Test', seen, {})
    assert stem == 'build-test'

def test_workflow_collision():
    seen = set()
    a = naming.normalize_workflow_stem('Deploy', seen, {})
    b = naming.normalize_workflow_stem('Deploy', seen, {})
    assert a == 'deploy'
    assert b.startswith('deploy-') and b != a

def test_workflow_long_truncation_and_suffix():
    seen = set()
    long_name = 'X' * 120
    stem1 = naming.normalize_workflow_stem(long_name, seen, {'naming': {'workflow': {'max_length': 10}}})
    stem2 = naming.normalize_workflow_stem(long_name, seen, {'naming': {'workflow': {'max_length': 10}}})
    assert len(stem1) <= 10
    assert stem2 != stem1

def test_repo_whitespace_default_underscore():
    name = naming.normalize_repo_name('My Repo Name')
    assert name == 'My_Repo_Name'

def test_repo_whitespace_dash():
    name = naming.normalize_repo_name('My Repo Name', {'naming': {'repository': {'whitespace_strategy': 'dash'}}})
    assert name == 'My-Repo-Name'

