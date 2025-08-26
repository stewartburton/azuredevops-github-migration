"""
Azure DevOps to GitHub Migration Tool

A comprehensive production-ready tool for migrating repositories, work items, 
and pipelines from Azure DevOps to GitHub with full Git history preservation.
"""

__version__ = "2.1.0"
__author__ = "Stewart Burton"
__email__ = "stewart@example.com"
__license__ = "MIT"

from .migrate import AzureDevOpsClient, GitHubClient, GitMigrator
from .analyze import OrganizationAnalyzer  
from .batch_migrate import BatchMigrator
from .utils import *

__all__ = [
    "AzureDevOpsClient",
    "GitHubClient", 
    "GitMigrator",
    "OrganizationAnalyzer",
    "BatchMigrator",
    "__version__"
]