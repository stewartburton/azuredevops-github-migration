# Configuration Guide

This guide provides comprehensive information about configuring the Azure DevOps to GitHub Migration Tool.

## Configuration Files

### Primary Configuration: `config.json`

The main configuration file uses JSON format and supports environment variable substitution using `${VARIABLE_NAME}` syntax.

```json
{
  "azure_devops": {
    "organization": "your-organization-name",
    "personal_access_token": "${AZURE_DEVOPS_PAT}",
    "project": "your-project-name",
    "base_url": "https://dev.azure.com/{organization}"
  },
  "github": {
    "token": "${GITHUB_TOKEN}",
    "organization": "your-github-org",
    "base_url": "https://api.github.com",
    "create_private_repos": true
  }
}
```

### Environment Variables: `.env`

Store sensitive credentials in environment variables:

```bash
AZURE_DEVOPS_PAT=your_azure_devops_personal_access_token
GITHUB_TOKEN=your_github_personal_access_token
```

## Configuration Sections

### Azure DevOps Configuration

| Field | Required | Description | Example |
|-------|----------|-------------|---------|
| `organization` | Yes | Azure DevOps organization name | `"contoso"` |
| `personal_access_token` | Yes | PAT with appropriate permissions | `"${AZURE_DEVOPS_PAT}"` |
| `project` | No | Default project name | `"MyProject"` |
| `base_url` | No | Custom Azure DevOps URL | `"https://dev.azure.com/{organization}"` |

#### Required Azure DevOps PAT Permissions

- **Code**: Read (for repositories)
- **Work Items**: Read (for work items)
- **Project and Team**: Read (for project information)

### GitHub Configuration

| Field | Required | Description | Example |
|-------|----------|-------------|---------|
| `token` | Yes | GitHub personal access token | `"${GITHUB_TOKEN}"` |
| `organization` | No | GitHub organization name | `"my-github-org"` |
| `base_url` | No | GitHub API base URL | `"https://api.github.com"` |
| `create_private_repos` | No | Create private repositories | `true` |

#### Required GitHub Token Permissions

- `repo`: Full control of private repositories
- `public_repo`: Access public repositories
- `admin:org`: Full control of orgs (if using organization)

### Migration Settings

```json
{
  "migration": {
    "repository_mapping": {
      "source-repo-1": "target-repo-1",
      "source-repo-2": "target-repo-2"
    },
    "migrate_work_items": true,
    "migrate_pull_requests": false,
    "batch_size": 100,
    "delay_between_requests": 0.5,
    "max_retries": 3,
    "include_closed_work_items": true
  }
}
```

| Field | Default | Description |
|-------|---------|-------------|
| `repository_mapping` | `{}` | Custom repository name mappings |
| `migrate_work_items` | `true` | Migrate work items to issues |
| `migrate_pull_requests` | `false` | Migrate pull request data |
| `batch_size` | `100` | Number of items to process per batch |
| `delay_between_requests` | `0.5` | Seconds to wait between API calls |
| `max_retries` | `3` | Maximum retry attempts |
| `include_closed_work_items` | `true` | Include closed/resolved work items |

### Work Item Mapping

Configure how Azure DevOps work items are converted to GitHub issues:

```json
{
  "work_item_mapping": {
    "type_mappings": {
      "User Story": "enhancement",
      "Bug": "bug",
      "Task": "task",
      "Feature": "feature",
      "Epic": "epic",
      "Issue": "question"
    },
    "state_mappings": {
      "New": "open",
      "Active": "open",
      "Resolved": "closed",
      "Closed": "closed",
      "Done": "closed",
      "Removed": "closed"
    },
    "priority_mappings": {
      "1": "priority-critical",
      "2": "priority-high", 
      "3": "priority-medium",
      "4": "priority-low"
    }
  }
}
```

#### Type Mappings

Map Azure DevOps work item types to GitHub labels:

| Azure DevOps Type | Recommended GitHub Label |
|-------------------|-------------------------|
| User Story | `enhancement` |
| Bug | `bug` |
| Task | `task` |
| Feature | `feature` |
| Epic | `epic` |
| Issue | `question` |

#### State Mappings

Map Azure DevOps states to GitHub issue states:

| Azure DevOps State | GitHub State |
|-------------------|--------------|
| New | `open` |
| Active | `open` |
| Resolved | `closed` |
| Closed | `closed` |
| Done | `closed` |

### Field Mappings

Configure which Azure DevOps fields to migrate:

```json
{
  "field_mappings": {
    "title_field": "System.Title",
    "description_field": "System.Description",
    "assigned_to_field": "System.AssignedTo",
    "created_date_field": "System.CreatedDate",
    "changed_date_field": "System.ChangedDate",
    "state_field": "System.State",
    "work_item_type_field": "System.WorkItemType",
    "priority_field": "Microsoft.VSTS.Common.Priority",
    "acceptance_criteria_field": "Microsoft.VSTS.Common.AcceptanceCriteria",
    "reproduction_steps_field": "Microsoft.VSTS.TCM.ReproSteps",
    "area_path_field": "System.AreaPath",
    "iteration_path_field": "System.IterationPath"
  }
}
```

### Repository Settings

Configure default settings for created GitHub repositories:

```json
{
  "repository_settings": {
    "default_branch": "main",
    "has_issues": true,
    "has_projects": true,
    "has_wiki": false,
    "auto_init": false,
    "gitignore_template": "",
    "license_template": ""
  }
}
```

### Logging Configuration

Configure logging behavior:

```json
{
  "logging": {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": "migration.log",
    "console": true,
    "max_file_size": 10485760,
    "backup_count": 5
  }
}
```

| Level | Description |
|-------|-------------|
| `DEBUG` | Detailed diagnostic information |
| `INFO` | General information messages |
| `WARNING` | Warning messages |
| `ERROR` | Error messages |
| `CRITICAL` | Critical error messages |

### Rate Limiting

Configure API rate limiting:

```json
{
  "rate_limiting": {
    "azure_devops_requests_per_second": 10,
    "github_requests_per_second": 30,
    "enable_backoff": true,
    "backoff_factor": 2.0
  }
}
```

### Filtering Options

Configure what to include/exclude from migration:

```json
{
  "filters": {
    "exclude_repositories": ["temp-repo", "test-repo"],
    "include_repositories": [],
    "exclude_work_item_types": ["Test Case", "Shared Steps"],
    "date_range": {
      "start_date": "2023-01-01",
      "end_date": "2023-12-31"
    },
    "work_item_states": ["New", "Active", "Resolved"]
  }
}
```

### Output Configuration

Configure migration output and reports:

```json
{
  "output": {
    "generate_reports": true,
    "report_format": "json",
    "output_directory": "./migration_reports",
    "include_statistics": true,
    "save_raw_data": false
  }
}
```

## Environment-Specific Configurations

### Development Environment

```json
{
  "logging": {
    "level": "DEBUG"
  },
  "rate_limiting": {
    "azure_devops_requests_per_second": 5,
    "github_requests_per_second": 10
  },
  "output": {
    "save_raw_data": true
  }
}
```

### Production Environment

```json
{
  "logging": {
    "level": "INFO"
  },
  "rate_limiting": {
    "azure_devops_requests_per_second": 15,
    "github_requests_per_second": 50
  },
  "migration": {
    "max_retries": 5,
    "delay_between_requests": 0.2
  }
}
```

## Validation

The tool validates your configuration on startup. Common validation errors:

### Missing Required Fields

```
Error: Azure DevOps organization is required
```

**Solution**: Add the `organization` field to your Azure DevOps configuration.

### Invalid Credentials

```
Error: GitHub token is invalid or expired
```

**Solution**: Check your GitHub token permissions and expiration date.

### Invalid Mappings

```
Error: work_item_mapping must be a dictionary
```

**Solution**: Ensure your work item mappings are properly formatted as JSON objects.

## Configuration Examples

### Basic Single Project Migration

```json
{
  "azure_devops": {
    "organization": "mycompany",
    "personal_access_token": "${AZURE_DEVOPS_PAT}",
    "project": "MainProject"
  },
  "github": {
    "token": "${GITHUB_TOKEN}",
    "organization": "mycompany-github"
  },
  "migration": {
    "migrate_work_items": true
  }
}
```

### Enterprise Multi-Project Migration

```json
{
  "azure_devops": {
    "organization": "enterprise",
    "personal_access_token": "${AZURE_DEVOPS_PAT}"
  },
  "github": {
    "token": "${GITHUB_TOKEN}",
    "organization": "enterprise-github",
    "create_private_repos": true
  },
  "migration": {
    "batch_size": 50,
    "delay_between_requests": 1.0,
    "max_retries": 5
  },
  "rate_limiting": {
    "azure_devops_requests_per_second": 8,
    "github_requests_per_second": 25,
    "enable_backoff": true
  },
  "filters": {
    "exclude_work_item_types": ["Test Case", "Shared Steps", "Test Suite"]
  }
}
```

### Personal Migration

```json
{
  "azure_devops": {
    "organization": "myusername",
    "personal_access_token": "${AZURE_DEVOPS_PAT}"
  },
  "github": {
    "token": "${GITHUB_TOKEN}",
    "create_private_repos": false
  },
  "migration": {
    "migrate_work_items": true,
    "include_closed_work_items": false
  }
}
```

## Configuration Best Practices

1. **Use Environment Variables**: Never hardcode credentials in configuration files
2. **Start Conservative**: Use lower rate limits initially and increase as needed
3. **Test First**: Validate configuration with a small test project
4. **Backup Configuration**: Keep copies of working configurations
5. **Document Changes**: Note any customizations made to mappings
6. **Version Control**: Keep configuration templates in version control (excluding credentials)

## Configuration Validation

Use the built-in validation:

```bash
python migrate.py --validate-config
```

This will check:
- Required fields are present
- Credentials are valid
- API connections work
- Mappings are properly formatted

## Troubleshooting Configuration

### Common Issues

**Issue**: Configuration file not found
```bash
FileNotFoundError: Configuration file 'config.json' not found
```
**Solution**: Copy `config.template.json` to `config.json`

**Issue**: Environment variable not found
```bash
Error: Environment variable 'AZURE_DEVOPS_PAT' not set
```
**Solution**: Set the environment variable or update your `.env` file

**Issue**: Invalid JSON format
```bash
JSONDecodeError: Expecting ',' delimiter
```
**Solution**: Validate your JSON syntax using a JSON validator

### Debug Configuration Loading

Enable debug logging to see how configuration is loaded:

```json
{
  "logging": {
    "level": "DEBUG"
  }
}
```

This will show:
- Configuration file loading
- Environment variable substitution
- Validation results
- API connection tests