#!/usr/bin/env python3
"""
Setup script for Azure DevOps to GitHub Migration Tool
"""

from setuptools import setup, find_packages
import os

# Read README for long description
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read requirements
with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="azuredevops-github-migration",
    version="2.0.0",
    author="Stewart Burton",
    author_email="", 
    description="Production-ready tool for migrating repositories from Azure DevOps to GitHub",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/stewartburton/azuredevops-github-migration",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators", 
        "Topic :: Software Development :: Version Control :: Git",
        "Topic :: System :: Archiving :: Mirroring",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": ["pytest>=7.0.0", "black>=22.0.0", "flake8>=4.0.0"],
        "test": ["pytest>=7.0.0", "pytest-cov>=3.0.0"],
    },
    entry_points={
        "console_scripts": [
            "azdo-migrate=src.migrate:main",
            "azdo-analyze=src.analyze:main", 
            "azdo-batch=src.batch_migrate:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["config/*.json", "examples/*.json"],
    },
    project_urls={
        "Bug Reports": "https://github.com/stewartburton/azuredevops-github-migration/issues",
        "Source": "https://github.com/stewartburton/azuredevops-github-migration",
        "Documentation": "https://github.com/stewartburton/azuredevops-github-migration/tree/main/docs",
    },
)