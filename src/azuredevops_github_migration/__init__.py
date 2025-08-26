"""
Azure DevOps to GitHub Migration Tool

A comprehensive production-ready tool for migrating repositories, work items, 
and pipelines from Azure DevOps to GitHub with full Git history preservation.
"""

__version__ = "2.1.0"
__author__ = "Stewart Burton"
__email__ = "stewart@example.com"
__license__ = "MIT"

# Import classes only when needed to avoid dependency issues during installation
__all__ = [
    "AzureDevOpsClient",
    "GitHubClient", 
    "GitMigrator",
    "MigrationOrchestrator",
    "AzureDevOpsAnalyzer",
    "RateLimiter",
    "__version__"
]

def __getattr__(name):
    """Lazy import for package components to avoid import errors during installation."""
    if name == "AzureDevOpsClient":
        from .migrate import AzureDevOpsClient
        return AzureDevOpsClient
    elif name == "GitHubClient":
        from .migrate import GitHubClient  
        return GitHubClient
    elif name == "GitMigrator":
        from .migrate import GitMigrator
        return GitMigrator
    elif name == "MigrationOrchestrator":
        from .migrate import MigrationOrchestrator
        return MigrationOrchestrator
    elif name == "AzureDevOpsAnalyzer":
        from .analyze import AzureDevOpsAnalyzer
        return AzureDevOpsAnalyzer
    elif name == "RateLimiter":
        from .utils import RateLimiter
        return RateLimiter
    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")