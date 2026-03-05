"""ADO repository freeze/unfreeze via Security REST API.

Freezes a repo by denying GenericContribute permission for the
project's Contributors group. Saves original ACLs for restore.
"""
import base64
import logging
from typing import Any, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class AdoRepoFreezer:
    """Freeze and unfreeze Azure DevOps repositories."""

    # Git Repositories security namespace
    GIT_SECURITY_NAMESPACE = "2e9eb7ed-3c0a-47d4-87c1-0ffdd275fd87"
    # GenericContribute permission bit
    GENERIC_CONTRIBUTE_BIT = 4

    def __init__(self, organization: str, pat: str, logger: logging.Logger = None):
        self.organization = organization
        self.pat = pat
        self.logger = logger or logging.getLogger(__name__)
        self.base_url = f"https://dev.azure.com/{organization}"

        self.session = requests.Session()
        retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503])
        self.session.mount("https://", HTTPAdapter(max_retries=retry))
        encoded = base64.b64encode(f":{pat}".encode()).decode()
        self.session.headers.update({
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/json",
        })

    def resolve_repo_id(self, project: str, repo_name: str) -> str:
        """Look up repo UUID from project + name."""
        url = f"{self.base_url}/{project}/_apis/git/repositories?api-version=7.0"
        resp = self.session.get(url, timeout=30)
        resp.raise_for_status()
        for repo in resp.json().get("value", []):
            if repo["name"] == repo_name:
                return repo["id"]
        raise ValueError(f"Repository '{repo_name}' not found in project '{project}'")

    def _security_token(self, project_id: str, repo_id: str) -> str:
        """Build security token for a repo."""
        return f"repoV2/{project_id}/{repo_id}"

    def _get_project_id(self, project: str) -> str:
        url = f"{self.base_url}/_apis/projects/{project}?api-version=7.0"
        resp = self.session.get(url, timeout=30)
        resp.raise_for_status()
        return resp.json()["id"]

    def freeze_repo(self, project: str, repo_id: str) -> Dict[str, Any]:
        """Deny push permissions. Returns original ACLs for later restore."""
        try:
            project_id = self._get_project_id(project)
            token = self._security_token(project_id, repo_id)

            # Step 1: Get current ACLs
            acl_url = (
                f"{self.base_url}/_apis/accesscontrollists/"
                f"{self.GIT_SECURITY_NAMESPACE}?token={token}&api-version=7.0"
            )
            acl_resp = self.session.get(acl_url, timeout=30)
            acl_resp.raise_for_status()
            original_acls = acl_resp.json()

            # Step 2: For each ACE, add GenericContribute to deny bits
            for acl in original_acls.get("value", []):
                for descriptor, ace in acl.get("acesDictionary", {}).items():
                    entry_url = (
                        f"{self.base_url}/_apis/accesscontrolentries/"
                        f"{self.GIT_SECURITY_NAMESPACE}?api-version=7.0"
                    )
                    body = {
                        "token": token,
                        "merge": True,
                        "accessControlEntries": [
                            {
                                "descriptor": descriptor,
                                "allow": ace.get("allow", 0),
                                "deny": ace.get("deny", 0) | self.GENERIC_CONTRIBUTE_BIT,
                                "extendedInfo": {},
                            }
                        ],
                    }
                    post_resp = self.session.post(entry_url, json=body, timeout=30)
                    post_resp.raise_for_status()

            self.logger.info(f"[FREEZE] Push denied for repo {repo_id}")
            return {"success": True, "original_acls": original_acls}

        except Exception as e:
            self.logger.error(f"[FREEZE] Failed for repo {repo_id}: {e}")
            return {"success": False, "error": str(e)}

    def unfreeze_repo(self, project: str, repo_id: str, original_acls: Dict) -> Dict[str, Any]:
        """Restore original permissions from saved ACLs."""
        try:
            project_id = self._get_project_id(project)
            token = self._security_token(project_id, repo_id)

            for acl in original_acls.get("value", []):
                for descriptor, ace in acl.get("acesDictionary", {}).items():
                    entry_url = (
                        f"{self.base_url}/_apis/accesscontrolentries/"
                        f"{self.GIT_SECURITY_NAMESPACE}?api-version=7.0"
                    )
                    body = {
                        "token": token,
                        "merge": False,  # Replace, don't merge
                        "accessControlEntries": [
                            {
                                "descriptor": descriptor,
                                "allow": ace.get("allow", 0),
                                "deny": ace.get("deny", 0),
                                "extendedInfo": {},
                            }
                        ],
                    }
                    post_resp = self.session.post(entry_url, json=body, timeout=30)
                    post_resp.raise_for_status()

            self.logger.info(f"[UNFREEZE] Permissions restored for repo {repo_id}")
            return {"success": True}

        except Exception as e:
            self.logger.error(f"[UNFREEZE] Failed for repo {repo_id}: {e}")
            return {"success": False, "error": str(e)}
