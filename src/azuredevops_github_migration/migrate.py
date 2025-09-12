#!/usr/bin/env python3
"""
Azure DevOps to GitHub Migration Tool

A comprehensive production-ready tool for migrating repositories, work items, 
and pipelines from Azure DevOps to GitHub with full Git history preservation.
"""

import os
import sys
import json
import logging
import asyncio
import subprocess
import tempfile
import shutil
import time
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, quote
import requests
from requests.auth import HTTPBasicAuth
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import yaml
import base64
from tqdm import tqdm


class AuthenticationError(Exception):
    """Authentication related errors."""
    pass

class MigrationError(Exception):
    """Base exception for migration errors."""
    pass

class RateLimitError(MigrationError):
    """Rate limiting errors."""
    pass

class GitOperationError(MigrationError):
    """Git operation errors."""
    pass


class AzureDevOpsClient:
    """Client for interacting with Azure DevOps REST API with retry logic and rate limiting."""
    
    def __init__(self, organization: str, personal_access_token: str, logger: logging.Logger = None):
        self.organization = organization
        self.pat = personal_access_token
        self.base_url = f"https://dev.azure.com/{organization}"
        self.logger = logger or logging.getLogger(__name__)
        
        # Setup session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Use base64 encoding for PAT (more secure)
        auth_string = base64.b64encode(f":{personal_access_token}".encode()).decode()
        self.session.headers.update({
            'Authorization': f'Basic {auth_string}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'AzureDevOps-GitHub-Migration-Tool/1.0'
        })
    
    def validate_credentials(self) -> bool:
        """Validate Azure DevOps credentials."""
        try:
            self.logger.info("Validating Azure DevOps credentials...")
            projects = self.get_projects()
            self.logger.info(f"[OK] Azure DevOps credentials valid. Found {len(projects)} projects.")
            return True
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise AuthenticationError("Invalid Azure DevOps PAT or insufficient permissions")
            elif e.response.status_code == 404:
                raise AuthenticationError(f"Organization '{self.organization}' not found or no access")
            raise
        except Exception as e:
            self.logger.error(f"Failed to validate Azure DevOps credentials: {str(e)}")
            return False
    
    def get_projects(self) -> List[Dict[str, Any]]:
        """Get all projects in the organization."""
        url = f"{self.base_url}/_apis/projects?api-version=7.0"
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.json().get('value', [])
        except requests.exceptions.Timeout:
            self.logger.error("Timeout getting projects from Azure DevOps")
            raise MigrationError("Azure DevOps API timeout")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error getting projects: {str(e)}")
            raise MigrationError(f"Failed to get projects: {str(e)}")
    
    def get_repositories(self, project_name: str) -> List[Dict[str, Any]]:
        """Get all repositories in a project."""
        # Use percent-encoding for path segment (quote_plus would use '+', which Azure DevOps rejects for project names)
        url = f"{self.base_url}/{quote(project_name, safe='')}/_apis/git/repositories?api-version=7.0"
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            repos = response.json().get('value', [])
            self.logger.debug(f"Found {len(repos)} repositories in project '{project_name}'")
            return repos
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error getting repositories for project '{project_name}': {str(e)}")
            raise MigrationError(f"Failed to get repositories: {str(e)}")
    
    def get_repository_size(self, project_name: str, repo_id: str) -> int:
        """Get repository size in bytes."""
        url = f"{self.base_url}/{quote(project_name, safe='')}/_apis/git/repositories/{repo_id}/stats/branches?api-version=7.0"
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            stats = response.json().get('value', [])
            total_commits = sum(branch.get('aheadCount', 0) + branch.get('behindCount', 0) for branch in stats)
            return total_commits * 1024  # Rough estimate
        except Exception:
            return 0
    
    def get_repository_branches(self, project_name: str, repo_id: str) -> List[Dict[str, Any]]:
        """Get all branches in a repository."""
        url = f"{self.base_url}/{quote(project_name, safe='')}/_apis/git/repositories/{repo_id}/refs?filter=heads&api-version=7.0"
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.json().get('value', [])
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Could not get branches for repository: {str(e)}")
            return []
    
    def get_pipelines(self, project_name: str) -> List[Dict[str, Any]]:
        """Get all build pipelines in a project."""
        url = f"{self.base_url}/{quote(project_name, safe='')}/_apis/build/definitions?api-version=7.0"
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            pipelines = response.json().get('value', [])
            self.logger.debug(f"Found {len(pipelines)} pipelines in project '{project_name}'")
            return pipelines
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Could not get pipelines for project '{project_name}': {str(e)}")
            return []

    def get_pipelines_for_repo(self, project_name: str, repo_id: str) -> List[Dict[str, Any]]:
        """Get build pipelines that reference a specific repository.

        Azure DevOps supports filtering build definitions by repositoryId and repositoryType.
        Note: Classic pipelines may not always return with this filter if they do not bind repo metadata.
        """
        url = (
            f"{self.base_url}/{quote(project_name, safe='')}/_apis/build/definitions"
            f"?repositoryId={repo_id}&repositoryType=TfsGit&api-version=7.0"
        )
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            pipelines = response.json().get('value', [])
            self.logger.debug(
                f"Found {len(pipelines)} pipelines in project '{project_name}' scoped to repo {repo_id}"
            )
            return pipelines
        except requests.exceptions.RequestException as e:
            self.logger.warning(
                f"Could not get repository-scoped pipelines for project '{project_name}', repo '{repo_id}': {str(e)}"
            )
            return []
    
    def get_work_items(self, project_name: str, wiql_query: str = None) -> List[Dict[str, Any]]:
        """Get work items using WIQL query."""
        if not wiql_query:
            wiql_query = f"SELECT [System.Id] FROM WorkItems WHERE [System.TeamProject] = '{project_name}'"
        url = f"{self.base_url}/{quote(project_name, safe='')}/_apis/wit/wiql?api-version=7.0"
        response = self.session.post(url, json={'query': wiql_query})
        response.raise_for_status()

        work_item_ids = [item['id'] for item in response.json().get('workItems', [])]
        if not work_item_ids:
            return []
        ids_str = ','.join(map(str, work_item_ids))
        detail_url = f"{self.base_url}/_apis/wit/workitems?ids={ids_str}&api-version=7.0&$expand=all"
        detail_response = self.session.get(detail_url)
        detail_response.raise_for_status()
        return detail_response.json().get('value', [])
    
    def get_pull_requests(self, project_name: str, repository_id: str) -> List[Dict[str, Any]]:
        """Get pull requests for a repository."""
        url = f"{self.base_url}/{project_name}/_apis/git/repositories/{repository_id}/pullrequests?api-version=7.0&searchCriteria.status=all"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json().get('value', [])
    
    def export_repository_data(self, project_name: str, repo_name: str, include_work_items: bool = True,
                               pipeline_scope: str = "project", exclude_disabled_pipelines: bool = False) -> Dict[str, Any]:
        """Export comprehensive repository data with enhanced metadata.

        include_work_items: if False, skips WIQL/work item calls (useful with --no-issues)
        pipeline_scope: 'project' (default) returns all project pipelines; 'repository' filters to pipelines referencing this repo
        exclude_disabled_pipelines: if True, filter out pipelines whose 'queueStatus' indicates disabled/paused
        """
        self.logger.info(f"Exporting data for repository '{repo_name}' in project '{project_name}'")
        
        repos = self.get_repositories(project_name)
        repo = next((r for r in repos if r['name'] == repo_name), None)
        
        if not repo:
            raise ValueError(f"Repository '{repo_name}' not found in project '{project_name}'")
        
        self.logger.debug("Gathering repository metadata...")
        
        # Get enhanced repository data
        work_items: List[Dict[str, Any]] = []
        if include_work_items:
            try:
                work_items = self.get_work_items(project_name)
            except Exception as e:
                self.logger.warning(f"Skipping work item retrieval due to error: {e}")
                work_items = []

        # Pipelines retrieval according to scope
        if pipeline_scope == 'repository':
            pipelines = self.get_pipelines_for_repo(project_name, repo['id'])
        else:
            pipelines = self.get_pipelines(project_name)

        if exclude_disabled_pipelines and pipelines:
            before = len(pipelines)
            pipelines = [p for p in pipelines if str(p.get('queueStatus', '')).lower() not in {'disabled', 'paused'}]
            self.logger.debug(f"Filtered disabled pipelines: {before} -> {len(pipelines)}")

        repo_data = {
            'repository': repo,
            'size': self.get_repository_size(project_name, repo['id']),
            'branches': self.get_repository_branches(project_name, repo['id']),
            'pull_requests': self.get_pull_requests(project_name, repo['id']),
            'work_items': work_items,
            'pipelines': pipelines
        }
        
        self.logger.info(f"Repository data exported: {len(repo_data['branches'])} branches, "
                        f"{len(repo_data['pull_requests'])} PRs, {len(repo_data['work_items'])} work items, "
                        f"{len(repo_data['pipelines'])} pipelines")
        
        return repo_data


class GitHubClient:
    """Client for interacting with GitHub REST API with enhanced security and retry logic."""
    
    def __init__(self, token: str, organization: str = None, logger: logging.Logger = None):
        self.token = token
        self.organization = organization
        self.base_url = "https://api.github.com"
        self.logger = logger or logging.getLogger(__name__)
        
        # Setup session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        self.session.headers.update({
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json',
            'Content-Type': 'application/json',
            'User-Agent': 'AzureDevOps-GitHub-Migration-Tool/1.0'
        })
    
    def validate_credentials(self) -> bool:
        """Validate GitHub credentials and permissions."""
        try:
            self.logger.info("Validating GitHub credentials...")
            user = self.get_user()
            
            # Test repository creation permissions
            if self.organization:
                # Test org permissions
                url = f"{self.base_url}/orgs/{self.organization}"
                response = self.session.get(url, timeout=30)
                if response.status_code == 404:
                    raise AuthenticationError(f"Organization '{self.organization}' not found or no access")
                response.raise_for_status()
                
            self.logger.info(f"[OK] GitHub credentials valid for user: {user['login']}")
            return True
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise AuthenticationError("Invalid GitHub token or insufficient permissions")
            raise
        except Exception as e:
            self.logger.error(f"Failed to validate GitHub credentials: {str(e)}")
            return False
    
    def create_repository(self, name: str, description: str = "", private: bool = True, **kwargs) -> Dict[str, Any]:
        """Create a new repository with enhanced settings."""
        # Validate repository name
        if not self._validate_repo_name(name):
            raise ValueError(f"Invalid repository name: '{name}'. Must follow GitHub naming rules.")
        data = {
            'name': name,
            'description': description,
            'private': private,
            'has_issues': kwargs.get('has_issues', True),
            'has_projects': kwargs.get('has_projects', True),
            'has_wiki': kwargs.get('has_wiki', True),
            'auto_init': kwargs.get('auto_init', False)
        }

        if kwargs.get('gitignore_template'):
            data['gitignore_template'] = kwargs['gitignore_template']
        if kwargs.get('license_template'):
            data['license_template'] = kwargs['license_template']

        if self.organization:
            url = f"{self.base_url}/orgs/{self.organization}/repos"
        else:
            url = f"{self.base_url}/user/repos"

        try:
            response = self.session.post(url, json=data, timeout=30)
            if response.status_code == 403:
                # If repo already exists, reuse
                if self.repository_exists(name):
                    existing = self.get_repository(name)
                    if existing:
                        self.logger.warning(f"[WARN] 403 Forbidden on create, but repository '{name}' exists. Reusing existing repository.")
                        return existing
                raise MigrationError(
                    "GitHub 403 Forbidden creating repository. Causes: insufficient PAT scopes ('repo'), "
                    "missing org create permission, SAML SSO not authorized, or org policy blocking creation."
                )
            response.raise_for_status()
            repo = response.json()
            self.logger.info(f"Created GitHub repository: {repo['html_url']}")
            return repo
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 422:
                error_msg = e.response.json().get('message', 'Repository creation failed')
                if 'already exists' in error_msg.lower():
                    raise MigrationError(f"Repository '{name}' already exists")
                raise MigrationError(f"Repository creation failed: {error_msg}")
            if e.response.status_code == 403:
                raise MigrationError("Forbidden: insufficient permissions or SSO authorization required for repository creation") from e
            raise
    
    def _validate_repo_name(self, name: str) -> bool:
        """Validate GitHub repository name."""
        if not name or len(name) > 100:
            return False
        # GitHub repo name rules: alphanumeric, hyphens, underscores, periods
        return re.match(r'^[a-zA-Z0-9._-]+$', name) is not None
    
    def get_rate_limit(self) -> Dict[str, Any]:
        """Get current rate limit status."""
        url = f"{self.base_url}/rate_limit"
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    
    def create_issue(self, repo_name: str, title: str, body: str = "", labels: List[str] = None) -> Dict[str, Any]:
        """Create an issue in a repository."""
        owner = self.organization or self.get_user()['login']
        url = f"{self.base_url}/repos/{owner}/{repo_name}/issues"
        
        data = {
            'title': title,
            'body': body
        }
        
        if labels:
            data['labels'] = labels
        
        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json()
    
    def create_milestone(self, repo_name: str, title: str, description: str = "") -> Dict[str, Any]:
        """Create a milestone in a repository."""
        owner = self.organization or self.get_user()['login']
        url = f"{self.base_url}/repos/{owner}/{repo_name}/milestones"
        
        data = {
            'title': title,
            'description': description
        }
        
        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json()
    
    def get_user(self) -> Dict[str, Any]:
        """Get current user information."""
        url = f"{self.base_url}/user"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()
    
    def repository_exists(self, name: str) -> bool:
        """Check if repository exists."""
        try:
            owner = self.organization or self.get_user()['login']
            url = f"{self.base_url}/repos/{owner}/{name}"
            response = self.session.get(url, timeout=30)
            return response.status_code == 200
        except Exception as e:
            self.logger.warning(f"Could not check if repository exists: {str(e)}")
            return False
    
    def get_repository(self, name: str) -> Optional[Dict[str, Any]]:
        """Get repository details if it exists."""
        try:
            owner = self.organization or self.get_user()['login']
            url = f"{self.base_url}/repos/{owner}/{name}"
            response = self.session.get(url, timeout=30)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            self.logger.warning(f"Could not get repository details: {str(e)}")
            return None


class GitMigrator:
    """Handles Git repository cloning, mirroring, and pushing operations."""
    
    def __init__(self, azure_client: AzureDevOpsClient, github_client: GitHubClient, logger: logging.Logger):
        self.azure_client = azure_client
        self.github_client = github_client
        self.logger = logger
        self.temp_dirs = []  # Track temporary directories for cleanup
    
    def migrate_repository_git_history(self, project_name: str, repo_name: str,
                                       github_repo_name: str, dry_run: bool = False,
                                       verify_remote: bool = False) -> bool:
        """Migrate complete Git history from Azure DevOps to GitHub.

        verify_remote: if True, after push perform remote branch enumeration and compare to local.
        Results stored in self.last_remote_verification.
        """
        temp_dir = None
        try:
            # Get Azure DevOps repository info
            repos = self.azure_client.get_repositories(project_name)
            repo = next((r for r in repos if r['name'] == repo_name), None)
            if not repo:
                raise ValueError(f"Repository '{repo_name}' not found")
            
            clone_url = repo.get('remoteUrl', '')
            if not clone_url:
                raise GitOperationError(f"No clone URL found for repository '{repo_name}'")

            # Sanitize clone URL (remove any embedded userinfo)
            clone_url = self.sanitize_clone_url(clone_url)
            
            # Provide clearer destination context (org/repo + expected URL)
            gh_org = self.github_client.organization or self.github_client.get_user().get('login','unknown')
            dest_url_preview = f"https://github.com/{gh_org}/{github_repo_name}.git"
            self.logger.info(
                f"Starting Git migration: {clone_url} -> GitHub:{gh_org}/{github_repo_name} ({dest_url_preview})"
            )
            
            if dry_run:
                self.logger.info("[DRY RUN] Would clone and push repository")
                return True
            
            # Create temporary directory
            temp_dir = tempfile.mkdtemp(prefix='git_migration_')
            self.temp_dirs.append(temp_dir)
            
            # Step 1: Clone with authentication
            authenticated_url = self._add_auth_to_url(clone_url, '', self.azure_client.pat)
            self.logger.info("Cloning Azure DevOps repository...")
            
            clone_result = subprocess.run([
                'git', 'clone', '--mirror', authenticated_url, temp_dir
            ], capture_output=True, text=True, timeout=1800)  # 30 minute timeout
            
            if clone_result.returncode != 0:
                raise GitOperationError(f"Git clone failed: {clone_result.stderr}")
            
            self.logger.info("[OK] Repository cloned successfully")
            
            # Step 2: Get GitHub repository info
            github_repo = self.github_client.get_repository(github_repo_name)
            if not github_repo:
                raise MigrationError(f"GitHub repository '{github_repo_name}' not found")
            
            github_clone_url = github_repo['clone_url']
            authenticated_github_url = self._add_auth_to_url(github_clone_url, self.github_client.token, '')
            
            # Step 3: Push to GitHub
            self.logger.info("Pushing to GitHub repository...")
            
            push_result = subprocess.run([
                'git', 'push', '--mirror', authenticated_github_url
            ], cwd=temp_dir, capture_output=True, text=True, timeout=1800)
            
            if push_result.returncode != 0:
                raise GitOperationError(f"Git push failed: {push_result.stderr}")
            
            self.logger.info("[OK] Repository pushed to GitHub successfully")
            
            # Verify migration
            self._verify_migration(temp_dir, authenticated_github_url if verify_remote else None, verify_remote)
            
            return True
            
        except subprocess.TimeoutExpired:
            raise GitOperationError("Git operation timed out. Repository may be too large.")
        except Exception as e:
            self.logger.error(f"Git migration failed: {str(e)}")
            raise
        finally:
            if temp_dir and os.path.exists(temp_dir):
                self._safe_rmtree(temp_dir)
                if temp_dir in self.temp_dirs:
                    self.temp_dirs.remove(temp_dir)
    
    def _add_auth_to_url(self, url: str, username: str, password: str) -> str:
        """Add authentication to Git URL."""
        if not url:
            return url
            
        parsed = urlparse(url)
        # Strip existing userinfo if present
        host = parsed.netloc.split('@')[-1]
        if username and password:
            auth = f"{quote(username)}:{quote(password)}"
        elif password:  # PAT case
            auth = f":{quote(password)}"
        else:
            return url
        return f"{parsed.scheme}://{auth}@{host}{parsed.path}"
    
    def _verify_migration(self, local_repo_path: str, github_url: Optional[str], verify_remote: bool):
        """Verify local migration and optionally compare remote branches."""
        self.last_remote_verification = {}
        try:
            # Local branches
            local_branches_cmd = subprocess.run(
                ['git', 'for-each-ref', 'refs/heads', '--format=%(refname:short)'],
                cwd=local_repo_path,
                capture_output=True,
                text=True
            )
            local_branches_list = [b.strip() for b in local_branches_cmd.stdout.split('\n') if b.strip()]
            local_branches = len(local_branches_list)

            # Commit count
            commit_result = subprocess.run(
                ['git', 'rev-list', '--all', '--count'],
                cwd=local_repo_path,
                capture_output=True,
                text=True
            )
            commit_count = int(commit_result.stdout.strip()) if commit_result.stdout.strip().isdigit() else 0

            msg = f"Migration verified (local): {local_branches} branches, {commit_count} commits"
            self.logger.info(msg)

            remote_details = None
            if verify_remote and github_url:
                # Sanitize URL for logging (remove credentials)
                display_url = github_url
                if '://' in display_url and '@' in display_url.split('://', 1)[1].split('/', 1)[0]:
                    # Remove userinfo
                    scheme, rest = display_url.split('://', 1)
                    host_part = rest.split('@', 1)[1]
                    display_url = f"{scheme}://{host_part}"
                try:
                    remote_heads = subprocess.run(
                        ['git', 'ls-remote', '--heads', github_url],
                        cwd=local_repo_path,
                        capture_output=True,
                        text=True,
                        timeout=120
                    )
                    if remote_heads.returncode != 0:
                        raise RuntimeError(remote_heads.stderr)
                    remote_branch_lines = [ln for ln in remote_heads.stdout.split('\n') if ln.strip()]
                    remote_branches_list = [ln.split('\t')[1].replace('refs/heads/', '') for ln in remote_branch_lines if '\trefs/heads/' in ln]
                    remote_branches = len(remote_branches_list)
                    missing_remote = sorted(set(local_branches_list) - set(remote_branches_list))
                    missing_local = sorted(set(remote_branches_list) - set(local_branches_list))
                    branch_match = not missing_remote and not missing_local and (local_branches == remote_branches)
                    self.logger.info(
                        f"Remote verification against {display_url}: {remote_branches} remote branches; match={branch_match}"
                    )
                    if missing_remote:
                        self.logger.warning(f"Branches missing on remote: {missing_remote}")
                    if missing_local:
                        self.logger.warning(f"Extra branches on remote: {missing_local}")
                    remote_details = {
                        'remote_branches': remote_branches,
                        'remote_branch_names': remote_branches_list,
                        'branch_match': branch_match,
                        'missing_remote': missing_remote,
                        'missing_local': missing_local
                    }
                except Exception as re:
                    self.logger.warning(f"Remote branch verification failed: {re}")
                    remote_details = {'error': str(re)}

            self.last_remote_verification = {
                'local_branches': local_branches,
                'local_branch_names': local_branches_list,
                'commit_count': commit_count,
                'remote': remote_details
            }
        except Exception as e:
            self.logger.warning(f"Verification step failed: {e}")
            self.last_remote_verification = {'error': str(e)}
    
    def cleanup(self):
        """Clean up any temporary directories."""
        for temp_dir in self.temp_dirs:
            try:
                if os.path.exists(temp_dir):
                    self._safe_rmtree(temp_dir)
            except Exception as e:
                self.logger.warning(f"Failed to cleanup temp directory {temp_dir}: {str(e)}")
        self.temp_dirs.clear()

    def sanitize_clone_url(self, url: str) -> str:
        """Remove embedded userinfo from clone URL to avoid double credential injection."""
        try:
            parsed = urlparse(url)
            netloc = parsed.netloc
            if '@' in netloc:
                host = netloc.split('@')[-1]
                return f"{parsed.scheme}://{host}{parsed.path}"
            return url
        except Exception:
            return url

    def _safe_rmtree(self, path: str, retries: int = 3):
        import stat
        def onerror(func, p, exc_info):
            try:
                if os.path.exists(p):
                    os.chmod(p, stat.S_IWRITE)
                    func(p)
            except Exception:
                pass
        for attempt in range(1, retries + 1):
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path, onerror=onerror)
                return
            except Exception as e:
                if attempt == retries:
                    self.logger.warning(f"Failed to cleanup temp directory {path}: {e}")
                else:
                    time.sleep(0.2 * attempt)


class PipelineConverter:
    """Converts Azure DevOps pipelines to GitHub Actions workflows."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def convert_pipelines_to_actions(self, pipelines: List[Dict[str, Any]], 
                                   output_dir: str, dry_run: bool = False) -> List[str]:
        """Convert Azure DevOps pipelines to GitHub Actions workflows."""
        converted_files = []
        
        if not pipelines:
            self.logger.info("No pipelines to convert")
            return converted_files
        
        self.logger.info(f"Converting {len(pipelines)} pipelines to GitHub Actions")
        
        if dry_run:
            self.logger.info("[DRY RUN] Would convert pipelines to GitHub Actions")
            return [f"workflow-{i}.yml" for i in range(len(pipelines))]
        
        os.makedirs(output_dir, exist_ok=True)
        
        for i, pipeline in enumerate(pipelines):
            try:
                workflow_name = self._sanitize_filename(pipeline.get('name', f'workflow-{i}'))
                workflow_file = f"{workflow_name}.yml"
                workflow_path = os.path.join(output_dir, workflow_file)
                
                workflow_content = self._convert_pipeline_to_workflow(pipeline)
                
                with open(workflow_path, 'w', encoding='utf-8') as f:
                    f.write(workflow_content)
                
                converted_files.append(workflow_file)
                self.logger.info(f"Converted pipeline '{pipeline.get('name')}' to '{workflow_file}'")
                
            except Exception as e:
                self.logger.error(f"Failed to convert pipeline '{pipeline.get('name')}': {str(e)}")
        
        return converted_files
    
    def _convert_pipeline_to_workflow(self, pipeline: Dict[str, Any]) -> str:
        """Convert a single Azure DevOps pipeline to GitHub Actions workflow."""
        name = pipeline.get('name', 'Converted Workflow')
        
        # Basic conversion - this could be much more sophisticated
        workflow = f"""# Converted from Azure DevOps Pipeline: {name}
# Original ID: {pipeline.get('id', 'unknown')}

name: {name}

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    # TODO: Convert specific Azure DevOps tasks to GitHub Actions
    # Original pipeline had {len(pipeline.get('process', {}).get('phases', []))} phases
    
    - name: Converted Build Step
      run: |
        echo "This workflow was converted from Azure DevOps"
        echo "Please review and update the steps as needed"
        echo "Original pipeline: {pipeline.get('name', 'unknown')}"
"""
        return workflow
    
    def _sanitize_filename(self, name: str) -> str:
        """Sanitize pipeline name for use as filename."""
        # Replace invalid characters with hyphens
        sanitized = re.sub(r'[^a-zA-Z0-9._-]', '-', name)
        sanitized = re.sub(r'-+', '-', sanitized)
        return sanitized.strip('-').lower()[:50]  # Limit length


class MigrationOrchestrator:
    """Orchestrates the complete migration process from Azure DevOps to GitHub."""
    
    def __init__(self, config_file: str = "migration_config.yaml"):
        self.config = self.load_config(config_file)
        self.setup_logging()
        
        self.azure_client = AzureDevOpsClient(
            self.config['azure_devops']['organization'],
            self.config['azure_devops']['personal_access_token'],
            self.logger
        )
        self.github_client = GitHubClient(
            self.config['github']['token'],
            self.config['github'].get('organization'),
            self.logger
        )
        self.git_migrator = GitMigrator(self.azure_client, self.github_client, self.logger)
        self.pipeline_converter = PipelineConverter(self.logger)
        
        # Migration state tracking
        self.migration_state = {
            'start_time': None,
            'current_step': None,
            'completed_steps': [],
            'failed_steps': [],
            'resumable': False
        }
    
    def load_config(self, config_file: str) -> Dict[str, Any]:
        """Load configuration from YAML or JSON file with environment variable substitution."""
        try:
            # Load .env file early so environment variables are available for substitution
            self._load_env_file()
            with open(config_file, 'r') as f:
                if config_file.endswith('.json'):
                    config = json.load(f)
                else:
                    config = yaml.safe_load(f)
            
            # Substitute environment variables
            config = self._substitute_env_vars(config)

            # Detect obvious template placeholders left unchanged
            missing = self._detect_unresolved(config)
            if missing:
                raise ValueError("Unresolved configuration placeholders: " + ", ".join(sorted(missing)))

            # Warn if common template defaults still present
            az_org = config.get('azure_devops', {}).get('organization', '')
            if az_org in ('your-organization-name', 'ORG_NAME_PLACEHOLDER'):
                raise ValueError("Azure DevOps organization not set. Update 'azure_devops.organization' in config.json or provide AZURE_DEVOPS_ORGANIZATION in .env and reference it as ${AZURE_DEVOPS_ORGANIZATION}.")
            
            # Validate required configuration
            self._validate_config(config)
            
            return config
            
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file '{config_file}' not found")
        except (yaml.YAMLError, json.JSONDecodeError) as e:
            raise ValueError(f"Invalid configuration file format: {str(e)}")
    
    def _substitute_env_vars(self, obj):
        """Recursively substitute environment variables in configuration."""
        if isinstance(obj, dict):
            return {k: self._substitute_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._substitute_env_vars(item) for item in obj]
        elif isinstance(obj, str) and obj.startswith('${') and obj.endswith('}'):
            env_var = obj[2:-1]
            value = os.getenv(env_var)
            if value is None:
                # For validation-only mode, return placeholder
                return f"[PLACEHOLDER_{env_var}]"
            return value
        else:
            return obj

    def _detect_unresolved(self, obj) -> set:
        """Return a set of unresolved placeholder markers still in config."""
        unresolved = set()
        if isinstance(obj, dict):
            for v in obj.values():
                unresolved.update(self._detect_unresolved(v))
        elif isinstance(obj, list):
            for v in obj:
                unresolved.update(self._detect_unresolved(v))
        elif isinstance(obj, str) and obj.startswith('[PLACEHOLDER_') and obj.endswith(']'):
            unresolved.add(obj[12:-1])  # Extract VAR name
        return unresolved

    def _load_env_file(self, filename: str = '.env'):
        """Lightweight .env loader (avoids extra dependency)."""
        try:
            if not os.path.exists(filename):
                return
            with open(filename, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '=' not in line:
                        continue
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key and key not in os.environ:
                        os.environ[key] = value
        except Exception as e:
            # Don't fail hard on env file issues; just log if logger available later
            print(f"[WARN] Failed to load .env file: {e}")
    
    def _validate_config(self, config: Dict[str, Any]):
        """Validate configuration has all required fields."""
        required_fields = [
            ('azure_devops', 'organization'),
            ('azure_devops', 'personal_access_token'),
            ('github', 'token')
        ]
        
        for section, field in required_fields:
            if section not in config:
                raise ValueError(f"Missing required configuration section: {section}")
            if field not in config[section] or not config[section][field]:
                raise ValueError(f"Missing required configuration: {section}.{field}")
    
    def validate_credentials(self) -> bool:
        """Validate all credentials before migration."""
        try:
            azure_valid = self.azure_client.validate_credentials()
            github_valid = self.github_client.validate_credentials()
            return azure_valid and github_valid
        except Exception as e:
            self.logger.error(f"Credential validation failed: {str(e)}")
            return False
    
    def setup_logging(self):
        """Setup comprehensive logging configuration."""
        log_config = self.config.get('logging', {})
        log_level = log_config.get('level', 'INFO')
        log_format = log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        log_file = log_config.get('file', 'migration.log')
        
        # Clear any existing handlers
        logging.getLogger().handlers.clear()
        
        handlers = []
        
        # File handler with rotation
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=log_config.get('max_file_size', 10485760),  # 10MB
            backupCount=log_config.get('backup_count', 5)
        )
        file_handler.setFormatter(logging.Formatter(log_format))
        handlers.append(file_handler)
        
        # Console handler if enabled
        if log_config.get('console', True):
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter(log_format))
            handlers.append(console_handler)
        
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format=log_format,
            handlers=handlers,
            force=True
        )
        
        self.logger = logging.getLogger(__name__)
        
        # Suppress noisy loggers
        logging.getLogger('requests').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    def migrate_repository(self, project_name: str, repo_name: str, 
                          github_repo_name: str = None, migrate_issues: bool = True,
                          migrate_pipelines: bool = True, dry_run: bool = False) -> bool:
        """Migrate a complete repository from Azure DevOps to GitHub."""
        start_time = datetime.now()
        self.migration_state['start_time'] = start_time
        
        try:
            self.logger.info(f"{'[DRY RUN] ' if dry_run else ''}Starting migration of repository '{repo_name}' from project '{project_name}'")
            
            github_repo_name = github_repo_name or repo_name
            
            # Step 1: Validate repository size and prerequisites
            self._update_migration_state("Validating prerequisites")
            if not self._validate_repository_prerequisites(project_name, repo_name, dry_run):
                return False
            
            # Step 2: Export data from Azure DevOps
            self._update_migration_state("Exporting Azure DevOps data")
            azure_data = self.azure_client.export_repository_data(
                project_name,
                repo_name,
                include_work_items=migrate_issues,
                pipeline_scope=self.config.get('pipelines', {}).get('scope', getattr(self.args, 'pipelines_scope', 'project')) if hasattr(self, 'args') else 'project',
                exclude_disabled_pipelines=(self.config.get('pipelines', {}).get('exclude_disabled', False) or getattr(self.args, 'exclude_disabled_pipelines', False) if hasattr(self, 'args') else False)
            )
            
            # Step 3: Create/validate GitHub repository
            self._update_migration_state("Setting up GitHub repository")
            github_repo = self._setup_github_repository(azure_data, github_repo_name, dry_run)
            
            if not github_repo and not dry_run:
                return False
            
            # Step 4: Migrate Git history (unless disabled)
            skip_git = False
            if hasattr(self, 'args') and getattr(self.args, 'no_git', False):
                skip_git = True
                self.logger.info("[SKIP] Git history migration skipped due to --no-git flag")
            if not skip_git:
                self._update_migration_state("Migrating Git history")
                if not self._migrate_git_repository(project_name, repo_name, github_repo_name, dry_run):
                    return False
            else:
                # Still register a completed step for consistency
                self.migration_state['completed_steps'].append("Skipped Git history (no-git)")
            
            # Step 5: Convert and migrate pipelines
            if migrate_pipelines and azure_data.get('pipelines'):
                self._update_migration_state("Converting pipelines")
                self._migrate_pipelines(azure_data['pipelines'], github_repo_name, dry_run)
            
            # Step 6: Migrate work items as issues
            if migrate_issues and azure_data.get('work_items'):
                self._update_migration_state("Migrating work items")
                self._migrate_work_items_to_issues(azure_data['work_items'], github_repo_name, dry_run)
            
            # Step 7: Generate migration report
            self._update_migration_state("Generating migration report")
            self._save_enhanced_migration_report(project_name, repo_name, azure_data, start_time, dry_run)
            
            duration = datetime.now() - start_time
            self.logger.info(f"[OK] {'[DRY RUN] ' if dry_run else ''}Successfully completed migration of '{repo_name}' in {duration}")
            
            return True
            
        except Exception as e:
            duration = datetime.now() - start_time
            self.logger.error(f"[ERROR] Failed to migrate repository '{repo_name}' after {duration}: {str(e)}")
            self.migration_state['failed_steps'].append(self.migration_state['current_step'])
            return False
        finally:
            # Cleanup temporary resources
            self.git_migrator.cleanup()
    
    def _validate_repository_prerequisites(self, project_name: str, repo_name: str, dry_run: bool) -> bool:
        """Validate that repository can be migrated."""
        try:
            repos = self.azure_client.get_repositories(project_name)
            repo = next((r for r in repos if r['name'] == repo_name), None)
            
            if not repo:
                self.logger.error(f"Repository '{repo_name}' not found in project '{project_name}'")
                return False
            
            # Check repository size
            repo_size = self.azure_client.get_repository_size(project_name, repo['id'])
            if repo_size > 5 * 1024 * 1024 * 1024:  # 5GB warning
                self.logger.warning(f"Repository is large ({repo_size / 1024 / 1024:.1f}MB). Migration may take significant time.")
            
            # Check Git availability
            if not dry_run:
                git_check = subprocess.run(['git', '--version'], capture_output=True, text=True)
                if git_check.returncode != 0:
                    self.logger.error("Git is not installed or not accessible")
                    return False
            
            self.logger.info("[OK] Repository prerequisites validated")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to validate prerequisites: {str(e)}")
            return False
    
    def _setup_github_repository(self, azure_data: Dict[str, Any], github_repo_name: str, dry_run: bool) -> Optional[Dict[str, Any]]:
        """Create or validate GitHub repository."""
        try:
            repo_exists = self.github_client.repository_exists(github_repo_name)
            
            if repo_exists:
                self.logger.info(f"GitHub repository '{github_repo_name}' already exists")
                if dry_run:
                    return {'name': github_repo_name, 'html_url': f'https://github.com/{github_repo_name}'}
                return self.github_client.get_repository(github_repo_name)
            
            if dry_run:
                self.logger.info(f"[DRY RUN] Would create GitHub repository: {github_repo_name}")
                return {'name': github_repo_name, 'html_url': f'https://github.com/{github_repo_name}'}
            
            # Create new repository
            repo_config = self.config.get('repository_settings', {})
            repo_description = azure_data['repository'].get('description', '')
            
            github_repo = self.github_client.create_repository(
                github_repo_name,
                repo_description,
                private=self.config['github'].get('create_private_repos', True),
                **repo_config
            )
            
            self.logger.info(f"[OK] Created GitHub repository: {github_repo['html_url']}")
            return github_repo
            
        except Exception as e:
            self.logger.error(f"Failed to setup GitHub repository: {str(e)}")
            return None
    
    def _migrate_git_repository(self, project_name: str, repo_name: str, github_repo_name: str, dry_run: bool) -> bool:
        """Migrate Git history from Azure DevOps to GitHub."""
        try:
            verify_remote = False
            if hasattr(self, 'args'):
                verify_remote = getattr(self.args, 'verify_remote', False)
            return self.git_migrator.migrate_repository_git_history(
                project_name, repo_name, github_repo_name, dry_run, verify_remote=verify_remote
            )
        except Exception as e:
            self.logger.error(f"Git repository migration failed: {str(e)}")
            return False
    
    def _migrate_pipelines(self, pipelines: List[Dict[str, Any]], github_repo_name: str, dry_run: bool):
        """Convert and migrate Azure DevOps pipelines to GitHub Actions."""
        try:
            # Guardrail: prevent accidental writing of workflow files into the tool repo unless explicitly allowed
            try:
                allow_local = getattr(self, 'args', None) and getattr(self.args, 'allow_local_workflows', False)
            except Exception:
                allow_local = False
            cwd = os.getcwd()
            # Heuristic: if this looks like the tool source repo (contains pyproject.toml & src/azuredevops_github_migration) and override not set
            is_tool_repo = os.path.exists(os.path.join(cwd, 'pyproject.toml')) and os.path.isdir(os.path.join(cwd, 'src', 'azuredevops_github_migration'))
            if is_tool_repo and not allow_local:
                self.logger.info("[GUARDRAIL] Skipping local workflow file emission (use --allow-local-workflows to override). Workflows will only be pushed to target repository.")
            # Generate workflows in an isolated temp directory to avoid polluting the tool's repository
            temp_gen_dir = tempfile.mkdtemp(prefix='workflow_gen_')
            workflows_dir = os.path.join(temp_gen_dir, '.github', 'workflows')
            os.makedirs(workflows_dir, exist_ok=True)

            converted_files = self.pipeline_converter.convert_pipelines_to_actions(pipelines, workflows_dir, dry_run)

            if converted_files:
                self.logger.info(f"[OK] Converted {len(converted_files)} pipelines to GitHub Actions (isolated)")
                if not dry_run:
                    try:
                        gh_org = self.github_client.organization or self.github_client.get_user().get('login', 'unknown')
                        repo_url = f"https://github.com/{gh_org}/{github_repo_name}.git"
                        self.logger.info(f"Preparing to commit workflows to {repo_url} from isolated directory")
                        temp_clone_dir = tempfile.mkdtemp(prefix='workflow_commit_')
                        clone_result = subprocess.run(['git', 'clone', repo_url, temp_clone_dir], capture_output=True, text=True, timeout=600)
                        if clone_result.returncode != 0:
                            self.logger.warning(f"Could not clone repo to add workflows: {clone_result.stderr.strip()}")
                        else:
                            dest_wf_dir = os.path.join(temp_clone_dir, '.github', 'workflows')
                            os.makedirs(dest_wf_dir, exist_ok=True)
                            changes = False
                            for wf in converted_files:
                                src_path = os.path.join(workflows_dir, wf)
                                dst_path = os.path.join(dest_wf_dir, wf)
                                if os.path.exists(dst_path):
                                    base, ext = os.path.splitext(wf)
                                    dst_path = os.path.join(dest_wf_dir, f"{base}-migrated{ext}")
                                    self.logger.warning(f"Workflow {wf} already exists in target repo – saving as {os.path.basename(dst_path)}")
                                shutil.copy2(src_path, dst_path)
                                changes = True
                            if changes:
                                # Ensure git user identity
                                if subprocess.run(['git', '-C', temp_clone_dir, 'config', '--get', 'user.email'], capture_output=True).returncode != 0:
                                    subprocess.run(['git', '-C', temp_clone_dir, 'config', 'user.email', 'migration-tool@local'], capture_output=True)
                                    subprocess.run(['git', '-C', temp_clone_dir, 'config', 'user.name', 'ADO-GH Migration Tool'], capture_output=True)
                                add_res = subprocess.run(['git', '-C', temp_clone_dir, 'add', '.github/workflows'], capture_output=True, text=True)
                                if add_res.returncode != 0:
                                    self.logger.warning(f"Failed to stage workflows: {add_res.stderr.strip()}")
                                else:
                                    commit_res = subprocess.run(['git', '-C', temp_clone_dir, 'commit', '-m', 'Add converted Azure DevOps pipelines as GitHub Actions workflows'], capture_output=True, text=True)
                                    if commit_res.returncode == 0:
                                        push_res = subprocess.run(['git', '-C', temp_clone_dir, 'push'], capture_output=True, text=True)
                                        if push_res.returncode == 0:
                                            self.logger.info("[OK] Workflow files committed and pushed to GitHub")
                                        else:
                                            self.logger.warning(f"Failed to push workflows: {push_res.stderr.strip()}")
                                    else:
                                        combined = (commit_res.stdout + commit_res.stderr).lower()
                                        if 'nothing to commit' in combined:
                                            self.logger.info("No workflow changes to commit (already present)")
                                        else:
                                            self.logger.warning(f"Failed to commit workflows: {commit_res.stderr.strip()}")
                    except Exception as wf_err:
                        self.logger.warning(f"Could not auto-commit workflows: {wf_err}")
            # No files are left behind in the tool repo.
            
        except Exception as e:
            self.logger.error(f"Pipeline migration failed: {str(e)}")
    
    def _update_migration_state(self, step: str):
        """Update current migration step for tracking."""
        if self.migration_state['current_step']:
            self.migration_state['completed_steps'].append(self.migration_state['current_step'])
        self.migration_state['current_step'] = step
        self.logger.info(f"Migration step: {step}")
    
    def _migrate_work_items_to_issues(self, work_items: List[Dict[str, Any]], github_repo_name: str, dry_run: bool = False):
        """Migrate Azure DevOps work items to GitHub issues with progress tracking."""
        if not work_items:
            return
            
        self.logger.info(f"{'[DRY RUN] ' if dry_run else ''}Migrating {len(work_items)} work items to GitHub issues")
        
        if dry_run:
            self.logger.info(f"[DRY RUN] Would create {len(work_items)} issues")
            return
        
        # Use progress bar for work items
        with tqdm(total=len(work_items), desc="Migrating work items", unit="item") as pbar:
            for work_item in work_items:
                try:
                    fields = work_item.get('fields', {})
                    title = fields.get('System.Title', 'Migrated Work Item')
                    description = fields.get('System.Description', '')
                    work_item_type = fields.get('System.WorkItemType', 'Task')
                    state = fields.get('System.State', 'New')
                    
                    # Create issue body with metadata
                    body = f"**Migrated from Azure DevOps Work Item #{work_item['id']}**\n\n"
                    body += f"**Original Type:** {work_item_type}\n"
                    body += f"**Original State:** {state}\n\n"
                    if description:
                        body += f"**Description:**\n{description}"
                    
                    # Create labels based on work item type and state
                    labels = [f"migrated", f"type:{work_item_type.lower()}", f"state:{state.lower()}"]
                    
                    issue = self.github_client.create_issue(
                        github_repo_name,
                        title,
                        body,
                        labels
                    )
                    
                    self.logger.debug(f"Created issue #{issue['number']} for work item #{work_item['id']}")
                    pbar.update(1)
                    
                except Exception as e:
                    self.logger.error(f"Failed to migrate work item #{work_item['id']}: {str(e)}")
                    pbar.update(1)
    
    # Keep the old method name for backward compatibility
    def migrate_work_items_to_issues(self, work_items: List[Dict[str, Any]], github_repo_name: str):
        """Legacy method - use _migrate_work_items_to_issues instead."""
        return self._migrate_work_items_to_issues(work_items, github_repo_name, False)
    
    def _save_enhanced_migration_report(self, project_name: str, repo_name: str, 
                                      azure_data: Dict[str, Any], start_time: datetime, dry_run: bool = False):
        """Save a comprehensive migration report."""
        end_time = datetime.now()
        duration = end_time - start_time
        
        # Include remote verification if performed
        remote_verification = None
        if hasattr(self, 'git_migrator') and getattr(self.git_migrator, 'last_remote_verification', None):
            remote_verification = self.git_migrator.last_remote_verification

        report = {
            'migration_metadata': {
                'tool_version': '2.0.0',
                'migration_date': end_time.isoformat(),
                'duration_seconds': duration.total_seconds(),
                'dry_run': dry_run,
                'completed_steps': self.migration_state['completed_steps'],
                'failed_steps': self.migration_state['failed_steps']
            },
            'source': {
                'platform': 'Azure DevOps',
                'organization': self.config['azure_devops']['organization'],
                'project': project_name,
                'repository': repo_name
            },
            'target': {
                'platform': 'GitHub',
                'organization': self.config['github'].get('organization', 'personal'),
                'repository': repo_name
            },
            'migration_statistics': {
                'repository_size_bytes': azure_data.get('size', 0),
                'branches_count': len(azure_data.get('branches', [])),
                'work_items_count': len(azure_data.get('work_items', [])),
                'pull_requests_count': len(azure_data.get('pull_requests', [])),
                'pipelines_count': len(azure_data.get('pipelines', [])),
                'git_history_migrated': (not dry_run) and not (hasattr(self, 'args') and getattr(self.args, 'no_git', False)),
                'pipelines_converted': len(azure_data.get('pipelines', [])) > 0
            },
            'verification': remote_verification,
            'detailed_data': azure_data if self.config.get('output', {}).get('save_raw_data', False) else None
        }
        
        # Ensure output directory exists
        output_dir = self.config.get('output', {}).get('output_directory', './migration_reports')
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = os.path.join(output_dir, f"migration_report_{project_name}_{repo_name}_{timestamp}.json")
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str, ensure_ascii=False)
        
        self.logger.info(f"[OK] Migration report saved to: {report_file}")
        
        # Also create a summary report
        self._create_summary_report(report, output_dir, timestamp)
    
    def _create_summary_report(self, full_report: Dict[str, Any], output_dir: str, timestamp: str):
        """Create a human-readable summary report."""
        try:
            summary_file = os.path.join(output_dir, f"migration_summary_{timestamp}.txt")
            
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write("AZURE DEVOPS TO GITHUB MIGRATION SUMMARY\n")
                f.write("=" * 50 + "\n\n")
                
                meta = full_report['migration_metadata']
                source = full_report['source']
                target = full_report['target']
                stats = full_report['migration_statistics']
                
                f.write(f"Migration Date: {meta['migration_date']}\n")
                f.write(f"Duration: {meta['duration_seconds']:.2f} seconds\n")
                f.write(f"Dry Run: {'Yes' if meta['dry_run'] else 'No'}\n\n")
                
                f.write(f"Source: {source['organization']}/{source['project']}/{source['repository']}\n")
                f.write(f"Target: {target['organization']}/{target['repository']}\n\n")
                
                f.write("MIGRATION STATISTICS:\n")
                f.write("-" * 20 + "\n")
                f.write(f"Repository Size: {stats['repository_size_bytes'] / 1024 / 1024:.1f} MB\n")
                f.write(f"Branches: {stats['branches_count']}\n")
                f.write(f"Work Items: {stats['work_items_count']}\n")
                f.write(f"Pull Requests: {stats['pull_requests_count']}\n")
                f.write(f"Pipelines: {stats['pipelines_count']}\n")
                f.write(f"Git History Migrated: {'Yes' if stats['git_history_migrated'] else 'No'}\n")
                f.write(f"Pipelines Converted: {'Yes' if stats['pipelines_converted'] else 'No'}\n\n")
                
                f.write(f"Completed Steps: {len(meta['completed_steps'])}\n")
                f.write(f"Failed Steps: {len(meta['failed_steps'])}\n")
                
                if meta['failed_steps']:
                    f.write("\nFAILED STEPS:\n")
                    for step in meta['failed_steps']:
                        f.write(f"- {step}\n")
        
        except Exception as e:
            self.logger.warning(f"Could not create summary report: {str(e)}")
    
    # Keep the old method name for backward compatibility
    def save_migration_report(self, project_name: str, repo_name: str, azure_data: Dict[str, Any]):
        """Legacy method - use _save_enhanced_migration_report instead."""
        return self._save_enhanced_migration_report(project_name, repo_name, azure_data, datetime.now(), False)
    
    def migrate_multiple_repositories(self, migrations: List[Dict[str, str]]) -> Dict[str, bool]:
        """Migrate multiple repositories."""
        results = {}
        
        for migration in migrations:
            project_name = migration['project_name']
            repo_name = migration['repo_name']
            github_repo_name = migration.get('github_repo_name', repo_name)
            migrate_issues = migration.get('migrate_issues', True)
            
            success = self.migrate_repository(
                project_name, 
                repo_name, 
                github_repo_name,
                migrate_issues
            )
            results[f"{project_name}/{repo_name}"] = success
        
        return results


def main(argv=None):
    """Main entry point for the production-ready migration tool.

    Accepts an optional argv list so the top-level cli wrapper can call
    migrate.main(args[1:]) without Python injecting those arguments as a
    positional parameter, fixing the error: main() takes 0 positional
    arguments but 1 was given.
    """
    import argparse

    if argv is None:
        import sys
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description='Azure DevOps to GitHub Migration Tool - Production Ready',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  # Validate credentials and configuration
  python migrate.py --validate-only --config config.json
  
  # Dry run migration (no actual changes)
  python migrate.py --project "MyProject" --repo "my-repo" --dry-run
  
  # Full migration with custom GitHub repo name
  python migrate.py --project "MyProject" --repo "old-name" --github-repo "new-name"
  
  # Migration without work items or pipelines
  python migrate.py --project "MyProject" --repo "my-repo" --no-issues --no-pipelines
        """
    )
    
    # Configuration options
    parser.add_argument('--config', default='config.json', 
                       help='Configuration file path (JSON or YAML)')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug logging')
    
    # Migration targets
    parser.add_argument('--project', 
                       help='Azure DevOps project name')
    parser.add_argument('--repo', 
                       help='Repository name to migrate')
    parser.add_argument('--github-repo', 
                       help='GitHub repository name (defaults to source repo name)')
    
    # Migration options
    parser.add_argument('--dry-run', action='store_true',
                       help='Perform a dry run without making actual changes')
    parser.add_argument('--no-issues', action='store_true',
                       help='Skip migrating work items as issues')
    parser.add_argument('--no-pipelines', action='store_true',
                       help='Skip converting pipelines to GitHub Actions')
    parser.add_argument('--no-git', action='store_true',
                       help='Skip Git history migration (only create repository)')
    parser.add_argument('--pipelines-scope', choices=['project', 'repository'], default='project',
                       help='Scope of pipelines to migrate: project (all project pipelines) or repository (only those bound to the repo)')
    parser.add_argument('--exclude-disabled-pipelines', action='store_true',
                       help='Exclude pipelines whose queueStatus is disabled/paused')
    parser.add_argument('--verify-remote', action='store_true',
                       help='After pushing git history, verify remote branches match local')
    parser.add_argument('--allow-local-workflows', action='store_true',
                       help='(Guardrail override) Allow writing workflow YAMLs into current working directory .github/workflows (not recommended)')
    
    # Validation options
    parser.add_argument('--validate-only', action='store_true',
                       help='Only validate credentials and configuration')
    parser.add_argument('--test-connections', action='store_true',
                       help='Test API connections without migration')
    
    # Utility options
    parser.add_argument('--list-projects', action='store_true',
                       help='List available Azure DevOps projects')
    parser.add_argument('--list-repos', 
                       help='List repositories in specified project')
    parser.add_argument('--list-pipelines', 
                       help='List all pipelines in specified project (pass project name)')
    parser.add_argument('--list-pipelines-repo', nargs=2, metavar=('PROJECT','REPO'),
                       help='List pipelines referencing a specific repository (provide PROJECT REPO)')
    
    args = parser.parse_args(argv)
    
    try:
        # Handle utility commands first
        if args.list_projects or args.list_repos or args.list_pipelines or args.list_pipelines_repo:
            return handle_list_commands(args)

        # Initialize orchestrator
        orchestrator = MigrationOrchestrator(args.config)
        # Attach args for downstream methods needing CLI context (non-breaking optional attribute)
        setattr(orchestrator, 'args', args)

        # Override debug logging if requested
        if args.debug:
            logging.getLogger().setLevel(logging.DEBUG)
            orchestrator.logger.setLevel(logging.DEBUG)

        # Handle validation-only commands
        if args.validate_only or args.test_connections:
            return handle_validation_commands(orchestrator, args)

        # Require project and repo for actual migration
        if not args.project or not args.repo:
            print("[ERROR] Error: --project and --repo are required for migration")
            parser.print_help()
            exit(1)

        print(f"[STARTING] Starting migration: {args.project}/{args.repo} -> GitHub")
        if args.dry_run:
            print("[INFO]  DRY RUN MODE - No actual changes will be made")

        # Validate credentials before migration
        print("[AUTH] Validating credentials...")
        if not orchestrator.validate_credentials():
            print("[ERROR] Credential validation failed. Please check your configuration.")
            exit(1)

        # Perform migration
        # Determine whether to migrate issues:
        migrate_issues_flag = not args.no_issues
        # Respect configuration default (e.g. Jira users) if user didn't explicitly disable via CLI
        try:
            if migrate_issues_flag and orchestrator.config.get('migration', {}).get('migrate_work_items') is False:
                migrate_issues_flag = False
        except Exception:
            pass

        success = orchestrator.migrate_repository(
            args.project,
            args.repo,
            args.github_repo,
            migrate_issues=migrate_issues_flag,
            migrate_pipelines=not args.no_pipelines,
            dry_run=args.dry_run
        )

        if success:
            print(f"[OK] {'[DRY RUN] ' if args.dry_run else ''}Migration completed successfully!")
            if args.dry_run:
                print("[INFO]  Run without --dry-run to perform actual migration")
        else:
            print("[ERROR] Migration failed. Check the logs for details.")
            exit(1)

    except KeyboardInterrupt:
        print("\n[WARNING]  Migration interrupted by user")
        exit(1)
    except Exception as e:
        print(f"[ERROR] Error: {str(e)}")
        if args.debug:
            import traceback
            traceback.print_exc()
        exit(1)


def handle_list_commands(args) -> int:
    """Handle --list-projects and --list-repos commands."""
    try:
        orchestrator = MigrationOrchestrator(args.config)
        
        if args.list_projects:
            projects = orchestrator.azure_client.get_projects()
            print(f"\nFound {len(projects)} projects in Azure DevOps:")
            print("-" * 50)
            for project in projects:
                visibility = project.get('visibility', 'unknown')
                state = project.get('state', 'unknown')
                print(f"• {project['name']} ({visibility}, {state})")
                if project.get('description'):
                    print(f"  Description: {project['description']}")
            return 0
        
        if args.list_repos:
            repos = orchestrator.azure_client.get_repositories(args.list_repos)
            print(f"\nFound {len(repos)} repositories in project '{args.list_repos}':")
            print("-" * 50)
            for repo in repos:
                size = orchestrator.azure_client.get_repository_size(args.list_repos, repo['id'])
                size_mb = size / 1024 / 1024 if size > 0 else 0
                print(f"• {repo['name']} ({size_mb:.1f} MB)")
                if repo.get('defaultBranch'):
                    print(f"  Default branch: {repo['defaultBranch']}")
            return 0

        if args.list_pipelines:
            project = args.list_pipelines
            pipelines = orchestrator.azure_client.get_pipelines(project)
            print(f"\nFound {len(pipelines)} pipelines in project '{project}':")
            print("-" * 50)
            for p in pipelines:
                name = p.get('name','<unnamed>')
                pid = p.get('id')
                qs = str(p.get('queueStatus',''))
                disabled = qs.lower() in {'disabled','paused'}
                print(f"• {name} (id={pid}) queueStatus={qs}{' [DISABLED]' if disabled else ''}")
            return 0

        if args.list_pipelines_repo:
            project, repo_name = args.list_pipelines_repo
            repos = orchestrator.azure_client.get_repositories(project)
            repo = next((r for r in repos if r['name'] == repo_name), None)
            if not repo:
                print(f"[ERROR] Repository '{repo_name}' not found in project '{project}'")
                return 1
            pipelines = orchestrator.azure_client.get_pipelines_for_repo(project, repo['id'])
            print(f"\nFound {len(pipelines)} pipelines in project '{project}' referencing repo '{repo_name}':")
            print("-" * 50)
            for p in pipelines:
                name = p.get('name','<unnamed>')
                pid = p.get('id')
                qs = str(p.get('queueStatus',''))
                disabled = qs.lower() in {'disabled','paused'}
                print(f"• {name} (id={pid}) queueStatus={qs}{' [DISABLED]' if disabled else ''}")
            return 0
            
    except Exception as e:
        print(f"[ERROR] Error listing resources: {str(e)}")
        return 1


def handle_validation_commands(orchestrator: MigrationOrchestrator, args) -> int:
    """Handle --validate-only and --test-connections commands."""
    try:
        print("[AUTH] Validating configuration and credentials...")
        
        # Test Azure DevOps connection
        try:
            azure_valid = orchestrator.azure_client.validate_credentials()
            if azure_valid:
                projects = orchestrator.azure_client.get_projects()
                print(f"[OK] Azure DevOps: Connected successfully ({len(projects)} projects accessible)")
            else:
                print("[ERROR] Azure DevOps: Connection failed")
        except Exception as e:
            print(f"[ERROR] Azure DevOps: {str(e)}")
            azure_valid = False
        
        # Test GitHub connection
        try:
            github_valid = orchestrator.github_client.validate_credentials()
            if github_valid:
                user = orchestrator.github_client.get_user()
                rate_limit = orchestrator.github_client.get_rate_limit()
                remaining = rate_limit['rate']['remaining']
                print(f"[OK] GitHub: Connected as {user['login']} ({remaining} API calls remaining)")
            else:
                print("[ERROR] GitHub: Connection failed")
        except Exception as e:
            print(f"[ERROR] GitHub: {str(e)}")
            github_valid = False
        
        if azure_valid and github_valid:
            print("\n[SUCCESS] All validations passed! Ready for migration.")
            return 0
        else:
            print("\n[ERROR] Validation failed. Please check your configuration.")
            return 1
            
    except Exception as e:
        print(f"[ERROR] Validation error: {str(e)}")
        return 1


if __name__ == "__main__":
    main()