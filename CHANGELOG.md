# Changelog

All notable changes to the Azure DevOps to GitHub Migration Tool will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.0] - 2024-01-XX

## [Unreleased]
### Removed
- Secret management / required secrets logic from `scripts/verify-migration.ps1` and associated GitHub Actions workflow inputs (`required_secrets`, `fail_on_missing_secrets`).
- Converted/migrated pipeline workflow artifacts (e.g. `rick.yml`) from the tool repository to avoid bundling target migration outputs.
- Active verification workflow from `.github/workflows/verify-migration.yml` (moved to `examples/verify-migration-workflow.yml`).

### Added
- `-Json` flag for `verify-migration.ps1` to produce machine-readable summary (used by workflow PR comments & artifacts).
- `exit_code` field embedded in JSON summary for direct consumption by CI systems.
- `--allow-local-workflows` override flag to intentionally permit local workflow YAML emission (guardrail defaults to blocking local writes).

### Changed
- Exit code semantics clarified: `0` success, `2` warnings (non-fatal), `3` fatal (repository inaccessible or configured fail conditions).
- Centralized exit evaluation logic and removed duplicate code paths in verification script.
- Simplified GitHub Actions workflow to only require `org` and `repo` inputs.
- Pipeline conversion now generates workflows in isolated temp directories only; no `.github/workflows` files are written to the migration tool repository.

### Fixed
- Eliminated brittle direct `.Count` usage by introducing `SafeCount` helper, resolving intermittent `property 'Count' cannot be found` runtime errors.
- Ensured repository inaccessibility is treated as a fatal condition (adds `repository_inaccessible` failure reason internally).

### Documentation
- Updated README to remove obsolete secret parameter references and reflect new JSON mode & exit code behavior.
- Clarified branch protection and lint optional flags usage without secret complexity.
- Documented relocation of verification workflow; users now copy from `examples/verify-migration-workflow.yml` into their migrated repositories if desired.
- Added explicit warning that the tool repository no longer stores any converted workflow YAML; all previously committed migrated workflows were purged.

### Notes
- Further doc polish (HOW_TO_GUIDE, TESTING) validated to have no lingering secret parameter references.


### Added
  - `azuredevops-github-migration migrate` - Single repository migration
  - `azuredevops-github-migration analyze` - Organization analysis  
  - `azuredevops-github-migration batch` - Batch migration
  - Multi-platform testing (Ubuntu, Windows, macOS)
  - Multi-version Python support (3.7-3.12)  
  - Security scanning with bandit and safety
  - Automated PyPI publishing on releases
  - `pyproject.toml` configuration following PEP standards
  - Proper package structure with `src/azuredevops_github_migration/`
  - Entry points for all CLI commands
  - Code formatting with Black
  - Import sorting with isort
  - Type checking with mypy
  - Security scanning integration

### Changed

### Enhanced

### Migration Notes for Existing Users
  ```bash
  python src/migrate.py --project "MyProject" --repo "my-repo"
  ```
  ```bash
  azuredevops-github-migration migrate --project "MyProject" --repo "my-repo"
  ```

## [2.0.0] - 2024-01-XX
### Added
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