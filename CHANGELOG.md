# Changelog

All notable changes to the Azure DevOps to GitHub Migration Tool will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.0] - 2024-01-XX

### Added
- **PyPI Distribution**: Tool is now available as a PyPI package (`pip install azuredevops-github-migration`)
- **Modern CLI Interface**: New unified command-line interface with subcommands
  - `azuredevops-github-migration migrate` - Single repository migration
  - `azuredevops-github-migration analyze` - Organization analysis  
  - `azuredevops-github-migration batch` - Batch migration
- **GitHub Actions CI/CD**: Comprehensive testing and automated publishing pipeline
  - Multi-platform testing (Ubuntu, Windows, macOS)
  - Multi-version Python support (3.7-3.12)  
  - Security scanning with bandit and safety
  - Automated PyPI publishing on releases
- **Modern Python Packaging**: 
  - `pyproject.toml` configuration following PEP standards
  - Proper package structure with `src/azuredevops_github_migration/`
  - Entry points for all CLI commands
- **Package Quality Tools**:
  - Code formatting with Black
  - Import sorting with isort
  - Type checking with mypy
  - Security scanning integration

### Changed
- **Installation Methods**: PyPI installation is now the recommended method
- **Command Structure**: All commands updated to use new CLI interface
- **Documentation**: Updated all documentation to reflect PyPI installation and new CLI
- **Package Structure**: Reorganized code into proper Python package structure

### Enhanced
- **Developer Experience**: Improved development setup with modern tooling
- **CI/CD Pipeline**: Comprehensive testing and deployment automation
- **Documentation**: All guides updated with new installation methods
- **Package Metadata**: Enhanced package information for PyPI distribution

### Migration Notes for Existing Users
- **Old Command Format** (still works for development installations):
  ```bash
  python src/migrate.py --project "MyProject" --repo "my-repo"
  ```
- **New Command Format** (recommended):
  ```bash
  azuredevops-github-migration migrate --project "MyProject" --repo "my-repo"
  ```

## [2.0.0] - 2024-01-XX

### Added
- Complete Git repository migration with full history preservation
- Azure DevOps Pipelines to GitHub Actions conversion
- Work items to GitHub Issues migration (optional)
- Jira mode for organizations using external issue tracking
- Pipeline scope control (repository vs. project-wide)
- Remote branch verification with `--verify-remote`
- Comprehensive batch migration support
- Dry-run mode for safe testing
- Rate limiting and retry logic
- Detailed logging and reporting
- Organization analysis and migration planning
- Security-focused design with least privilege PAT requirements

### Security
- No credential exposure in logs or error messages
- Environment variable substitution for sensitive data
- Comprehensive authentication validation
- Fine-grained PAT scope guidance

### Documentation
- Complete step-by-step HOW_TO_GUIDE.md
- 100+ item PRE_MIGRATION_CHECKLIST.md
- Comprehensive TESTING.md with security and performance tests
- Technical documentation for configuration and troubleshooting

## [1.0.0] - Initial Release
- Basic migration functionality
- Initial documentation
- Core Azure DevOps and GitHub API integration