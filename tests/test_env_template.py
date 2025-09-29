import re

from azuredevops_github_migration.init import create_env_template


def test_env_template_contains_required_keys():
    content = create_env_template()
    required = [
        "AZURE_DEVOPS_PAT=",
        "GITHUB_TOKEN=",
        "AZURE_DEVOPS_ORGANIZATION=",
        "GITHUB_ORGANIZATION=",
    ]
    for key in required:
        assert key in content, f"Missing expected placeholder line for {key}"
