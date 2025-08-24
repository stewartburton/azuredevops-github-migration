# API Documentation

This document describes the APIs, classes, and methods available in the Azure DevOps to GitHub Migration Tool.

## Table of Contents

1. [Core Classes](#core-classes)
2. [AzureDevOpsClient](#azuredevopsclient)
3. [GitHubClient](#githubclient)
4. [MigrationOrchestrator](#migrationorchestrator)
5. [Utility Functions](#utility-functions)
6. [Configuration Schema](#configuration-schema)
7. [Data Models](#data-models)
8. [Error Handling](#error-handling)

## Core Classes

### Class Hierarchy

```
MigrationOrchestrator
├── AzureDevOpsClient
├── GitHubClient
└── Utility Functions
```

## AzureDevOpsClient

The `AzureDevOpsClient` class handles all interactions with Azure DevOps REST APIs.

### Constructor

```python
AzureDevOpsClient(organization: str, personal_access_token: str)
```

**Parameters:**
- `organization` (str): Azure DevOps organization name
- `personal_access_token` (str): Personal Access Token with required permissions

**Example:**
```python
client = AzureDevOpsClient("myorg", "pat_token_here")
```

### Methods

#### get_projects()

Retrieves all projects in the organization.

```python
def get_projects() -> List[Dict[str, Any]]
```

**Returns:** List of project dictionaries

**Example:**
```python
projects = client.get_projects()
for project in projects:
    print(f"Project: {project['name']} (ID: {project['id']})")
```

**Response Schema:**
```json
[
  {
    "id": "project-uuid",
    "name": "Project Name",
    "description": "Project description",
    "url": "https://dev.azure.com/org/_apis/projects/project-uuid",
    "state": "wellFormed",
    "visibility": "private"
  }
]
```

#### get_repositories(project_name: str)

Retrieves all Git repositories in a project.

```python
def get_repositories(project_name: str) -> List[Dict[str, Any]]
```

**Parameters:**
- `project_name` (str): Name of the Azure DevOps project

**Returns:** List of repository dictionaries

**Example:**
```python
repos = client.get_repositories("MyProject")
for repo in repos:
    print(f"Repository: {repo['name']} (Size: {repo.get('size', 0)} bytes)")
```

#### get_work_items(project_name: str, wiql_query: str = None)

Retrieves work items using WIQL (Work Item Query Language).

```python
def get_work_items(project_name: str, wiql_query: str = None) -> List[Dict[str, Any]]
```

**Parameters:**
- `project_name` (str): Name of the Azure DevOps project
- `wiql_query` (str, optional): Custom WIQL query. If not provided, gets all work items.

**Returns:** List of work item dictionaries with full field data

**Example:**
```python
# Get all work items
work_items = client.get_work_items("MyProject")

# Custom query
query = "SELECT [System.Id] FROM WorkItems WHERE [System.WorkItemType] = 'Bug'"
bugs = client.get_work_items("MyProject", query)
```

#### get_pull_requests(project_name: str, repository_id: str)

Retrieves pull requests for a repository.

```python
def get_pull_requests(project_name: str, repository_id: str) -> List[Dict[str, Any]]
```

**Parameters:**
- `project_name` (str): Name of the Azure DevOps project
- `repository_id` (str): Repository ID

**Returns:** List of pull request dictionaries

#### export_repository_data(project_name: str, repo_name: str)

Exports comprehensive data for a repository including work items and pull requests.

```python
def export_repository_data(project_name: str, repo_name: str) -> Dict[str, Any]
```

**Parameters:**
- `project_name` (str): Name of the Azure DevOps project
- `repo_name` (str): Name of the repository

**Returns:** Dictionary containing repository, work items, and pull request data

**Example:**
```python
data = client.export_repository_data("MyProject", "my-repo")
print(f"Repository: {data['repository']['name']}")
print(f"Work Items: {len(data['work_items'])}")
print(f"Pull Requests: {len(data['pull_requests'])}")
```

## GitHubClient

The `GitHubClient` class handles all interactions with GitHub REST APIs.

### Constructor

```python
GitHubClient(token: str, organization: str = None)
```

**Parameters:**
- `token` (str): GitHub Personal Access Token
- `organization` (str, optional): GitHub organization name. If not provided, uses personal account.

### Methods

#### create_repository(name: str, description: str = "", private: bool = True)

Creates a new repository on GitHub.

```python
def create_repository(name: str, description: str = "", private: bool = True) -> Dict[str, Any]
```

**Parameters:**
- `name` (str): Repository name
- `description` (str, optional): Repository description
- `private` (bool, optional): Whether to create a private repository (default: True)

**Returns:** Created repository dictionary

**Example:**
```python
repo = client.create_repository(
    name="migrated-repo",
    description="Migrated from Azure DevOps",
    private=True
)
print(f"Created repository: {repo['html_url']}")
```

#### create_issue(repo_name: str, title: str, body: str = "", labels: List[str] = None)

Creates an issue in a GitHub repository.

```python
def create_issue(repo_name: str, title: str, body: str = "", labels: List[str] = None) -> Dict[str, Any]
```

**Parameters:**
- `repo_name` (str): Repository name
- `title` (str): Issue title
- `body` (str, optional): Issue body/description
- `labels` (List[str], optional): List of label names to apply

**Returns:** Created issue dictionary

**Example:**
```python
issue = client.create_issue(
    repo_name="my-repo",
    title="Migrated Work Item",
    body="This issue was migrated from Azure DevOps",
    labels=["migrated", "bug"]
)
print(f"Created issue #{issue['number']}: {issue['title']}")
```

#### create_milestone(repo_name: str, title: str, description: str = "")

Creates a milestone in a GitHub repository.

```python
def create_milestone(repo_name: str, title: str, description: str = "") -> Dict[str, Any]
```

#### get_user()

Gets information about the authenticated user.

```python
def get_user() -> Dict[str, Any]
```

#### repository_exists(name: str)

Checks if a repository already exists.

```python
def repository_exists(name: str) -> bool
```

## MigrationOrchestrator

The main orchestration class that coordinates the migration process.

### Constructor

```python
MigrationOrchestrator(config_file: str = "migration_config.yaml")
```

**Parameters:**
- `config_file` (str): Path to configuration file

### Methods

#### migrate_repository(project_name: str, repo_name: str, github_repo_name: str = None, migrate_issues: bool = True)

Migrates a single repository from Azure DevOps to GitHub.

```python
def migrate_repository(
    project_name: str, 
    repo_name: str, 
    github_repo_name: str = None, 
    migrate_issues: bool = True
) -> bool
```

**Parameters:**
- `project_name` (str): Azure DevOps project name
- `repo_name` (str): Azure DevOps repository name
- `github_repo_name` (str, optional): Target GitHub repository name
- `migrate_issues` (bool): Whether to migrate work items as issues

**Returns:** Boolean indicating success/failure

#### migrate_multiple_repositories(migrations: List[Dict[str, str]])

Migrates multiple repositories using a migration plan.

```python
def migrate_multiple_repositories(migrations: List[Dict[str, str]]) -> Dict[str, bool]
```

**Parameters:**
- `migrations` (List[Dict]): List of migration configurations

**Returns:** Dictionary mapping repository names to success/failure status

#### migrate_work_items_to_issues(work_items: List[Dict[str, Any]], github_repo_name: str)

Migrates Azure DevOps work items to GitHub issues.

```python
def migrate_work_items_to_issues(work_items: List[Dict[str, Any]], github_repo_name: str)
```

## Utility Functions

Located in `utils.py`, these functions provide supporting functionality.

### sanitize_github_name(name: str)

Sanitizes repository names for GitHub compatibility.

```python
def sanitize_github_name(name: str) -> str
```

**Example:**
```python
clean_name = sanitize_github_name("My Repo With Spaces!")
# Returns: "my-repo-with-spaces"
```

### convert_html_to_markdown(html_content: str)

Converts HTML content to Markdown format.

```python
def convert_html_to_markdown(html_content: str) -> str
```

### format_work_item_body(work_item: Dict[str, Any])

Formats an Azure DevOps work item as a GitHub issue body.

```python
def format_work_item_body(work_item: Dict[str, Any]) -> str
```

### generate_labels_for_work_item(work_item: Dict[str, Any], work_item_mapping: Dict[str, str] = None, state_mapping: Dict[str, str] = None)

Generates appropriate GitHub labels for a work item.

```python
def generate_labels_for_work_item(
    work_item: Dict[str, Any], 
    work_item_mapping: Dict[str, str] = None,
    state_mapping: Dict[str, str] = None
) -> List[str]
```

### retry_on_failure(func, max_retries: int = 3, delay: float = 1.0, backoff_factor: float = 2.0)

Decorator for retrying API calls on failure.

```python
@retry_on_failure(max_retries=3)
def api_call():
    # API call logic here
    pass
```

### RateLimiter Class

Simple rate limiter for API calls.

```python
class RateLimiter:
    def __init__(self, max_calls_per_second: float = 10.0)
    def wait_if_needed(self)
```

**Example:**
```python
limiter = RateLimiter(max_calls_per_second=10)
limiter.wait_if_needed()  # Waits if necessary
```

## Configuration Schema

### Main Configuration Structure

```json
{
  "azure_devops": {
    "organization": "string",
    "personal_access_token": "string",
    "project": "string (optional)",
    "base_url": "string (optional)"
  },
  "github": {
    "token": "string",
    "organization": "string (optional)",
    "base_url": "string (optional)",
    "create_private_repos": "boolean (optional)"
  },
  "migration": {
    "repository_mapping": "object (optional)",
    "migrate_work_items": "boolean (optional)",
    "batch_size": "integer (optional)",
    "delay_between_requests": "number (optional)",
    "max_retries": "integer (optional)"
  }
}
```

### Work Item Mapping Schema

```json
{
  "work_item_mapping": {
    "type_mappings": {
      "User Story": "enhancement",
      "Bug": "bug",
      "Task": "task"
    },
    "state_mappings": {
      "New": "open",
      "Resolved": "closed"
    },
    "priority_mappings": {
      "1": "priority-critical",
      "2": "priority-high"
    }
  }
}
```

## Data Models

### Azure DevOps Work Item Model

```python
{
    "id": 123,
    "fields": {
        "System.Title": "Work item title",
        "System.Description": "<p>HTML description</p>",
        "System.WorkItemType": "User Story",
        "System.State": "Active",
        "System.AssignedTo": {
            "displayName": "John Doe",
            "uniqueName": "john@company.com"
        },
        "System.CreatedDate": "2023-01-01T12:00:00Z",
        "Microsoft.VSTS.Common.Priority": 2
    },
    "url": "https://dev.azure.com/org/project/_apis/wit/workItems/123"
}
```

### GitHub Issue Model

```python
{
    "id": 456789,
    "number": 1,
    "title": "Issue title",
    "body": "Markdown formatted body",
    "state": "open",
    "labels": [
        {"name": "enhancement", "color": "84b6eb"},
        {"name": "migrated", "color": "d4edda"}
    ],
    "created_at": "2023-01-01T12:00:00Z",
    "html_url": "https://github.com/owner/repo/issues/1"
}
```

### Migration Report Model

```python
{
    "migration_date": "2023-01-01T12:00:00Z",
    "source": {
        "organization": "azure-org",
        "project": "MyProject", 
        "repository": "my-repo"
    },
    "target": {
        "organization": "github-org",
        "repository": "migrated-repo"
    },
    "statistics": {
        "work_items_count": 50,
        "pull_requests_count": 25,
        "issues_created": 50,
        "migration_duration": "00:05:30"
    }
}
```

## Error Handling

### Custom Exception Classes

```python
class MigrationError(Exception):
    """Base exception for migration errors"""
    pass

class AuthenticationError(MigrationError):
    """Authentication related errors"""
    pass

class RateLimitError(MigrationError):
    """Rate limiting errors"""
    pass

class ConfigurationError(MigrationError):
    """Configuration related errors"""
    pass
```

### Error Response Format

```python
{
    "error": True,
    "message": "Error description",
    "code": "ERROR_CODE",
    "details": {
        "request_id": "12345",
        "timestamp": "2023-01-01T12:00:00Z",
        "context": {}
    }
}
```

## API Usage Examples

### Complete Migration Example

```python
from migrate import MigrationOrchestrator

# Initialize orchestrator
orchestrator = MigrationOrchestrator("config.json")

# Migrate single repository
success = orchestrator.migrate_repository(
    project_name="MyProject",
    repo_name="legacy-app", 
    github_repo_name="modern-app",
    migrate_issues=True
)

if success:
    print("Migration completed successfully!")
else:
    print("Migration failed - check logs for details")
```

### Batch Migration Example

```python
# Define migration plan
migrations = [
    {
        "project_name": "Project1",
        "repo_name": "repo1",
        "github_repo_name": "migrated-repo1",
        "migrate_issues": True
    },
    {
        "project_name": "Project1", 
        "repo_name": "repo2",
        "github_repo_name": "migrated-repo2",
        "migrate_issues": False
    }
]

# Execute batch migration
results = orchestrator.migrate_multiple_repositories(migrations)

# Check results
for repo, success in results.items():
    status = "✅" if success else "❌"
    print(f"{status} {repo}")
```

### Custom Work Item Processing

```python
from migrate import AzureDevOpsClient
from utils import format_work_item_body, generate_labels_for_work_item

client = AzureDevOpsClient("org", "pat")
work_items = client.get_work_items("MyProject")

for work_item in work_items:
    # Custom processing
    title = work_item['fields']['System.Title']
    body = format_work_item_body(work_item)
    labels = generate_labels_for_work_item(work_item)
    
    print(f"Processing: {title}")
    print(f"Labels: {labels}")
```

This API documentation provides a complete reference for using the Azure DevOps to GitHub Migration Tool programmatically. For additional examples and usage patterns, refer to the source code and test files.