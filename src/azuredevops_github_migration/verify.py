"""Post-migration verification: compare ADO source vs GitHub target."""
import argparse
import subprocess
import sys
from typing import Any, Dict, List
from urllib.parse import quote, urlparse


def _authenticated_url(url: str, user: str, password: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.split("@")[-1]
    if user and password:
        auth = f"{quote(user)}:{quote(password)}"
    elif password:
        auth = f":{quote(password)}"
    else:
        return url
    return f"{parsed.scheme}://{auth}@{host}{parsed.path}"


def _ls_remote_branches(url: str) -> List[str]:
    """Get branch names from a remote via git ls-remote --heads."""
    result = subprocess.run(
        ["git", "ls-remote", "--heads", url],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git ls-remote failed: {result.stderr}")
    branches = []
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) == 2 and parts[1].startswith("refs/heads/"):
            branches.append(parts[1].replace("refs/heads/", ""))
    return sorted(branches)


def verify_repo_migration(
    ado_url: str,
    github_url: str,
    ado_pat: str,
    github_token: str,
) -> Dict[str, Any]:
    """Compare branches between ADO source and GitHub target."""
    ado_auth_url = _authenticated_url(ado_url, "", ado_pat)
    gh_auth_url = _authenticated_url(github_url, github_token, "")

    ado_branches = _ls_remote_branches(ado_auth_url)
    gh_branches = _ls_remote_branches(gh_auth_url)

    missing_on_github = sorted(set(ado_branches) - set(gh_branches))
    extra_on_github = sorted(set(gh_branches) - set(ado_branches))

    return {
        "ado_branches": len(ado_branches),
        "github_branches": len(gh_branches),
        "branch_match": not missing_on_github and not extra_on_github,
        "missing_on_github": missing_on_github,
        "extra_on_github": extra_on_github,
    }


def main(args=None):
    parser = argparse.ArgumentParser(description="Post-migration verification")
    parser.add_argument("--state-file", required=True, help="State file with completed repos")
    parser.add_argument("--config", default="config.json", help="Config file")
    parsed = parser.parse_args(args)
    # Implementation: iterate state file completed repos and verify each
    print("Verification requires --state-file with completed repos.")
    print("(Full implementation reads state + config and verifies each completed repo)")


if __name__ == "__main__":
    main()
