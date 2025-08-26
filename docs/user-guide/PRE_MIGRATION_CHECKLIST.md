# Pre-Migration Checklist

Use this comprehensive checklist before running any Azure DevOps to GitHub migration to ensure a successful and safe migration process.

## ✅ Prerequisites Verification

### System Requirements
- [ ] **Python 3.7+** installed and accessible
- [ ] **Git 2.20+** installed and accessible from command line
- [ ] **Sufficient disk space** (at least 3x repository size for temporary files)
- [ ] **Network connectivity** to both Azure DevOps and GitHub APIs
- [ ] **Administrative permissions** on target GitHub organization (if applicable)

### Access Requirements
- [ ] **Azure DevOps organization access** with project visibility
- [ ] **GitHub organization owner/admin** permissions (if migrating to organization)
- [ ] **Write access** to target GitHub repositories location

## ✅ Credential Setup

### Azure DevOps Personal Access Token (PAT)
- [ ] **PAT created** with **minimum required scopes:**
  - [ ] **Code (Read)** - for repository access (required)
  - [ ] **Project and Team (Read)** - for project information (required)
  - [ ] **Work Items (Read)** - ONLY if migrating work items (skip if using Jira)
- [ ] **PAT expiration date** set appropriately (recommend short duration: 30-60 days)
- [ ] **Least privilege principle applied** - only scopes actually needed
- [ ] **PAT tested** with Azure DevOps REST API
- [ ] **PAT stored securely** in environment variable or secure vault

### GitHub Personal Access Token
- [ ] **Fine-grained PAT created** (recommended) or Classic PAT
- [ ] **Token created** with **minimum required scopes:**
  - [ ] **repo** - full control of private repositories (required)
  - [ ] **admin:org** - ONLY if tool needs to create repositories in organization
  - [ ] **delete_repo** - ONLY if implementing rollback functionality
  - [ ] **workflow** - ONLY if manipulating workflow runs beyond committing YAML
- [ ] **Repository access** configured (specific repos preferred over "All repositories")
- [ ] **Token expiration date** set appropriately
- [ ] **Token tested** with GitHub API
- [ ] **Token stored securely** in environment variable

### Credential Testing
- [ ] **All connections validated:**
  ```bash
  azuredevops-github-migration migrate --validate-only --config config.json
  ```
- [ ] **GitHub connection validated**
- [ ] **Rate limits checked** for both services
- [ ] **Organization access confirmed**

## ✅ Configuration Setup

### Configuration Files
- [ ] **Configuration file created** (config.json or config.yaml)
- [ ] **Environment variables configured:**
  ```bash
  export AZURE_DEVOPS_PAT="your_azure_devops_pat"
  export GITHUB_TOKEN="your_github_token"
  ```
- [ ] **Configuration validated:**
  ```bash
  azuredevops-github-migration migrate --validate-only --config config.json
  ```
- [ ] **Sensitive data excluded** from version control
- [ ] **Backup of configuration** stored securely

### Migration Settings Review
- [ ] **Repository mapping** defined correctly
- [ ] **Work item type mappings** configured
- [ ] **State mappings** reviewed and approved
- [ ] **Rate limiting** configured appropriately
- [ ] **Output directory** configured and accessible
- [ ] **Logging level** set appropriately

## ✅ Source Analysis (Azure DevOps)

### Repository Assessment
- [ ] **Repository analysis completed:**
  ```bash
  azuredevops-github-migration analyze --project "ProjectName" --config config.json
  ```
- [ ] **Repository sizes determined**
- [ ] **Large repositories identified** (> 1GB warning)
- [ ] **Repository dependencies mapped**
- [ ] **Branch structure analyzed**
- [ ] **Git LFS usage identified** (if applicable)

### Work Items Analysis (Skip if using Jira)
- [ ] **Decision made:** Migrate work items to GitHub Issues OR continue using Jira
- [ ] **If migrating work items:**
  - [ ] Work item count determined
  - [ ] Work item types catalogued
  - [ ] Custom fields identified
  - [ ] Work item relationships mapped
- [ ] **If using Jira mode:**
  - [ ] `examples/jira-users-config.json` selected as template
  - [ ] `--skip-work-items` flag planned for analysis

### Pipelines Analysis
- [ ] **Pipeline count determined**
- [ ] **Pipeline complexity assessed**
- [ ] **Custom tasks identified**
- [ ] **Pipeline dependencies mapped**
- [ ] **Conversion effort estimated**

### Project Analysis
- [ ] **Organization analysis completed:**
  ```bash
  azuredevops-github-migration analyze --create-plan --config config.json
  # OR for Jira users (no work items):
  azuredevops-github-migration analyze --create-plan --config config.json --skip-work-items
  ```
- [ ] **Migration plan generated and reviewed**
- [ ] **Priority repositories identified**
- [ ] **Migration order determined**

## ✅ Target Preparation (GitHub)

### GitHub Organization Setup
- [ ] **Target organization created** (if applicable)
- [ ] **Organization settings configured**
- [ ] **Team permissions planned**
- [ ] **Repository naming conventions defined**
- [ ] **Branch protection rules planned**

### Repository Preparation
- [ ] **Repository names validated** for GitHub compatibility
- [ ] **Name conflicts resolved**
- [ ] **Repository descriptions prepared**
- [ ] **Initial repository settings planned**

## ✅ Migration Planning

### Migration Strategy
- [ ] **Migration approach selected:**
  - [ ] Big Bang (all at once)
  - [ ] Phased (by priority/team)
  - [ ] Gradual (one by one)
- [ ] **Migration timeline established**
- [ ] **Rollback plan documented**
- [ ] **Communication plan prepared**

### Testing Strategy
- [ ] **Test migration performed:**
  ```bash
  azuredevops-github-migration migrate --project "TestProject" --repo "test-repo" --dry-run --config config.json
  ```
- [ ] **Dry run results validated**
- [ ] **Test repository successfully migrated**
- [ ] **Migration report reviewed**
- [ ] **Performance benchmarks established**

### Risk Assessment
- [ ] **Repository size risks assessed**
- [ ] **Network timeout risks evaluated**
- [ ] **Rate limiting risks planned for**
- [ ] **Data loss risks mitigated**
- [ ] **Security risks evaluated**

## ✅ Team Preparation

### Stakeholder Communication
- [ ] **Migration announcement sent** to affected teams
- [ ] **Migration timeline communicated**
- [ ] **Access changes documented**
- [ ] **Training materials prepared**
- [ ] **Support contacts established**

### Team Readiness
- [ ] **Team members notified** of GitHub access requirements
- [ ] **GitHub accounts created** for all team members
- [ ] **GitHub organization invitations sent**
- [ ] **Permission mappings planned**

## ✅ Technical Preparation

### Environment Setup
- [ ] **Migration tool installed:**
  ```bash
  pip install -r requirements.txt
  ```
- [ ] **Dependencies validated**
- [ ] **Tool version confirmed** (latest stable)
- [ ] **Migration environment prepared**
- [ ] **Monitoring setup configured**

### Backup and Recovery
- [ ] **Azure DevOps repository backups confirmed**
- [ ] **Work item export backup created**
- [ ] **Pipeline definitions backed up**
- [ ] **Recovery procedures documented**
- [ ] **Rollback scripts prepared**

### Performance Optimization
- [ ] **Migration server resources allocated**
- [ ] **Network bandwidth verified**
- [ ] **Parallel migration capability assessed**
- [ ] **Resource monitoring configured**

## ✅ Security and Compliance

### Security Measures
- [ ] **Credential security validated**
- [ ] **API logging reviewed** for sensitive data
- [ ] **Network security confirmed**
- [ ] **Access audit trail configured**

### Compliance Requirements
- [ ] **Data residency requirements checked**
- [ ] **Audit trail requirements confirmed**
- [ ] **Retention policies applied**
- [ ] **Compliance documentation updated**

## ✅ Final Validation

### Pre-Migration Testing
- [ ] **Complete dry run performed:**
  ```bash
  azuredevops-github-migration migrate --project "RealProject" --repo "target-repo" --dry-run --debug --config config.json
  ```
- [ ] **All validation checks passed**
- [ ] **Performance within acceptable limits**
- [ ] **Error handling verified**
- [ ] **Cleanup procedures tested**

### Go/No-Go Decision
- [ ] **All checklist items completed**
- [ ] **Stakeholder approval obtained**
- [ ] **Migration window scheduled**
- [ ] **Support team notified and ready**
- [ ] **Rollback plan approved**

## ✅ Migration Execution Day

### Pre-Migration
- [ ] **Migration server prepared**
- [ ] **All team members notified**
- [ ] **Monitoring systems active**
- [ ] **Support team standing by**

### During Migration
- [ ] **Migration progress monitored**
- [ ] **Logs reviewed for errors**
- [ ] **Performance metrics tracked**
- [ ] **Communications updated**

### Post-Migration Verification
- [ ] **Repository integrity verified**
- [ ] **Branch structure confirmed**
- [ ] **Work item conversion validated**
- [ ] **Pipeline conversion reviewed**
- [ ] **Access permissions verified**
- [ ] **Team functionality confirmed**

## ✅ Common Pre-Migration Commands

### Validation Commands
```bash
# Validate configuration and credentials
azuredevops-github-migration migrate --validate-only --config config.json

# List available projects and analyze
azuredevops-github-migration analyze --config config.json

# Analyze specific project
azuredevops-github-migration analyze --project "MyProject" --config config.json
```

### Analysis Commands
```bash
# Analyze organization and create migration plan
azuredevops-github-migration analyze --create-plan --config config.json

# Jira users (skip work items completely)
azuredevops-github-migration analyze --create-plan --config config.json --skip-work-items

# Analyze specific project
azuredevops-github-migration analyze --project "MyProject" --config config.json

# Generate CSV report
azuredevops-github-migration analyze --format csv --config config.json
```

### Testing Commands
```bash
# Dry run single repository
azuredevops-github-migration migrate --project "MyProject" --repo "test-repo" --dry-run --config config.json

# Dry run batch migration
azuredevops-github-migration batch --dry-run --plan migration_plan.json --config config.json

# Test with debug logging and additional flags
azuredevops-github-migration migrate --project "MyProject" --repo "test-repo" --dry-run --debug --config config.json

# Test pipeline scope control
azuredevops-github-migration migrate --project "MyProject" --repo "test-repo" --pipelines-scope repository --dry-run --config config.json

# Test with remote verification
azuredevops-github-migration migrate --project "MyProject" --repo "test-repo" --verify-remote --dry-run --config config.json
```

## ⚠️ Common Issues to Check

### Configuration Issues
- [ ] **Environment variables not set** - Use `env | grep TOKEN`
- [ ] **Invalid JSON/YAML syntax** - Validate with `python -m json.tool config.json`
- [ ] **Missing required fields** - Check error messages carefully
- [ ] **Path issues on Windows** - Use forward slashes in paths

### Authentication Issues
- [ ] **Expired tokens** - Check token expiration dates
- [ ] **Insufficient permissions** - Verify token scopes
- [ ] **Organization access** - Confirm access to target organizations
- [ ] **Network restrictions** - Test from migration server

### Repository Issues
- [ ] **Repository name conflicts** - Check for existing repositories
- [ ] **Large repository warnings** - Plan for extended migration times
- [ ] **Empty repositories** - Verify repositories have content
- [ ] **Git LFS requirements** - Install Git LFS if needed

### Performance Issues
- [ ] **Rate limiting** - Adjust requests per second in config
- [ ] **Network timeouts** - Increase timeout values
- [ ] **Memory usage** - Monitor during large repository migrations
- [ ] **Disk space** - Ensure adequate temporary storage

## 📋 Pre-Migration Checklist Summary

**Total Items:** 100+
**Critical Items:** Authentication, Configuration, Dry Run Testing
**Estimated Completion Time:** 4-8 hours for complex migrations
**Required Roles:** DevOps Engineer, Project Manager, Security Team

**Final Check:** All items above must be completed and verified before proceeding with production migration.

---

**Note:** Keep this checklist and mark items as completed. Save completed checklists as documentation of migration preparation process.