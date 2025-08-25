# Troubleshooting Guide

This guide helps you diagnose and resolve common issues when using the Azure DevOps to GitHub Migration Tool.

## Table of Contents

1. [General Troubleshooting](#general-troubleshooting)
2. [Authentication Issues](#authentication-issues)
3. [API Rate Limiting](#api-rate-limiting)
4. [Repository Migration Issues](#repository-migration-issues)
5. [Work Item Migration Issues](#work-item-migration-issues)
6. [Network and Connectivity Issues](#network-and-connectivity-issues)
7. [Performance Issues](#performance-issues)
8. [Data Integrity Issues](#data-integrity-issues)
9. [Common Error Messages](#common-error-messages)
10. [Debug Tools and Techniques](#debug-tools-and-techniques)

## General Troubleshooting

### Enable Debug Logging

First step in troubleshooting is to enable detailed logging:

```json
{
  "logging": {
    "level": "DEBUG",
    "console": true
  }
}
```

Or use command line:
```bash
python migrate.py --debug --project "MyProject" --repo "my-repo"
```

### Check Tool Version and Dependencies

```bash
# Check Python version
python --version

# Check installed packages
pip list | grep -E "(requests|pyyaml|html2text|markdown)"

# Verify all dependencies
pip check
```

### Validate Configuration

```bash
# Validate configuration file
python migrate.py --validate-config

# Test API connections
python migrate.py --test-connections
```

## Authentication Issues

### Azure DevOps Authentication Errors

#### Error: "Invalid credentials or access token expired"

**Symptoms:**
- HTTP 401 Unauthorized responses
- "Access denied" messages

**Solutions:**

1. **Check Token Expiration**
   ```bash
   # Test token validity
   curl -u ":YOUR_PAT" https://dev.azure.com/yourorg/_apis/projects
   ```

2. **Verify Token Permissions**
   Required scopes:
   - Code (Read)
   - Work Items (Read)
   - Project and Team (Read)

3. **Regenerate Token**
   - Go to Azure DevOps → User Settings → Personal Access Tokens
   - Create new token with required permissions
   - Update `.env` file

#### Error: "Organization not found"

**Symptoms:**
- HTTP 404 responses when accessing organization

**Solutions:**
1. Verify organization name in configuration
2. Check if you have access to the organization
3. Ensure organization URL is correct

### GitHub Authentication Errors

#### Error: "Bad credentials"

**Symptoms:**
- HTTP 401 responses from GitHub API
- Authentication failure messages

**Solutions:**

1. **Check Token Validity**
   ```bash
   curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/user
   ```

2. **Verify Token Permissions**
   Required scopes:
   - `repo` (for private repositories)
   - `public_repo` (for public repositories)  
   - `admin:org` (for organization operations)

3. **Update Token**
   - Go to GitHub → Settings → Developer Settings → Personal Access Tokens
   - Generate new token with required scopes
   - Update `.env` file

#### Error: "Not Found" when creating repositories

**Symptoms:**
- HTTP 404 when creating repositories in organization

**Solutions:**
1. Verify you have admin/owner permissions in the GitHub organization
2. Check if organization name is correct
3. Ensure token has `admin:org` scope

## API Rate Limiting

### Azure DevOps Rate Limiting

#### Error: "Rate limit exceeded"

**Symptoms:**
- HTTP 429 responses
- "TF400733" error codes

**Solutions:**

1. **Reduce Request Rate**
   ```json
   {
     "rate_limiting": {
       "azure_devops_requests_per_second": 5,
       "enable_backoff": true,
       "backoff_factor": 2.0
     }
   }
   ```

2. **Implement Delays**
   ```json
   {
     "migration": {
       "delay_between_requests": 1.0
     }
   }
   ```

3. **Use Batch Processing**
   ```json
   {
     "migration": {
       "batch_size": 50
     }
   }
   ```

### GitHub Rate Limiting

#### Error: "API rate limit exceeded"

**Symptoms:**
- HTTP 403 responses with rate limit headers
- "You have exceeded a secondary rate limit" messages

**Solutions:**

1. **Check Rate Limit Status**
   ```bash
   curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/rate_limit
   ```

2. **Adjust Rate Limiting**
   ```json
   {
     "rate_limiting": {
       "github_requests_per_second": 10,
       "enable_backoff": true
     }
   }
   ```

3. **Use GitHub Enterprise** (if available)
   - Higher rate limits for GitHub Enterprise Cloud/Server

## Repository Migration Issues

### Large Repository Issues

#### Error: "Clone timeout" or "Repository too large"

**Symptoms:**
- Timeout errors during git clone
- Out of disk space errors

**Solutions:**

1. **Increase Timeout**
   ```bash
   git config --global http.postBuffer 524288000
   git config --global http.lowSpeedLimit 0
   git config --global http.lowSpeedTime 999999
   ```

2. **Use Shallow Clone**
   ```python
   # In migrate.py, modify git clone to use shallow clone
   git.clone_from(source_url, local_path, depth=1)
   ```

3. **Check Disk Space**
   ```bash
   df -h  # Check available disk space
   ```

### Repository Already Exists

#### Error: "Repository already exists"

**Symptoms:**
- HTTP 422 responses when creating repositories
- "Repository name already exists" messages

**Solutions:**

1. **Use Different Name**
   ```bash
   python migrate.py --project "MyProject" --repo "source-repo" --github-repo "new-repo-name"
   ```

2. **Delete Existing Repository** (if safe)
   ```bash
   # Through GitHub UI or API
   curl -X DELETE -H "Authorization: token YOUR_TOKEN" https://api.github.com/repos/owner/repo
   ```

3. **Skip if Exists**
   ```json
   {
     "migration": {
       "skip_existing_repos": true
     }
   }
   ```

## Work Item Migration Issues

### HTML to Markdown Conversion Issues

#### Error: "Cannot convert HTML content"

**Symptoms:**
- Malformed Markdown in GitHub issues
- Missing or corrupted content

**Solutions:**

1. **Update html2text Library**
   ```bash
   pip install --upgrade html2text
   ```

2. **Check HTML Content**
   ```python
   # Debug HTML content
   print(work_item['fields']['System.Description'])
   ```

3. **Custom Conversion Rules**
   ```python
   # In utils.py, customize HTML2Text settings
   h.ignore_images = False
   h.ignore_tables = False
   h.body_width = 0
   ```

### Missing Work Item Fields

#### Error: "Field not found in work item"

**Symptoms:**
- Empty issue descriptions
- Missing metadata

**Solutions:**

1. **Check Available Fields**
   ```python
   # Debug work item fields
   print(json.dumps(work_item['fields'].keys(), indent=2))
   ```

2. **Update Field Mappings**
   ```json
   {
     "field_mappings": {
       "description_field": "System.Description",
       "custom_field": "Custom.MyField"
     }
   }
   ```

3. **Handle Missing Fields**
   ```python
   # In migrate.py, add null checks
   description = fields.get('System.Description', 'No description available')
   ```

### Work Item Type Not Found

#### Error: "Work item type 'CustomType' not recognized"

**Symptoms:**
- Work items skipped during migration
- Unknown work item type warnings

**Solutions:**

1. **Add Custom Mappings**
   ```json
   {
     "work_item_mapping": {
       "type_mappings": {
         "CustomType": "enhancement",
         "Epic": "epic"
       }
     }
   }
   ```

2. **List Available Types**
   ```bash
   python analyze.py --project "MyProject" | grep "work_item_types"
   ```

## Network and Connectivity Issues

### Proxy Configuration

#### Error: "Connection timeout" or "Network unreachable"

**Solutions:**

1. **Configure Proxy**
   ```bash
   export HTTP_PROXY=http://proxy.company.com:8080
   export HTTPS_PROXY=http://proxy.company.com:8080
   ```

2. **Update requests Configuration**
   ```python
   # In migrate.py, add proxy configuration
   proxies = {
       'http': 'http://proxy.company.com:8080',
       'https': 'http://proxy.company.com:8080'
   }
   session.proxies.update(proxies)
   ```

### SSL Certificate Issues

#### Error: "SSL certificate verification failed"

**Solutions:**

1. **Update Certificate Bundle**
   ```bash
   pip install --upgrade certifi
   ```

2. **Disable SSL Verification** (not recommended for production)
   ```python
   session.verify = False
   ```

3. **Custom CA Bundle**
   ```python
   session.verify = '/path/to/ca-bundle.crt'
   ```

## Performance Issues

### Slow Migration Speed

**Symptoms:**
- Migration taking much longer than expected
- High memory usage

**Solutions:**

1. **Optimize Batch Size**
   ```json
   {
     "migration": {
       "batch_size": 25,  // Reduce if memory issues
       "delay_between_requests": 0.1
     }
   }
   ```

2. **Increase Parallelization**
   ```python
   # Use asyncio for concurrent requests
   import asyncio
   import aiohttp
   ```

3. **Monitor Resource Usage**
   ```bash
   top -p $(pgrep -f migrate.py)
   ```

### Memory Issues

#### Error: "Out of memory" or high memory usage

**Solutions:**

1. **Process in Smaller Batches**
   ```json
   {
     "migration": {
       "batch_size": 10
     }
   }
   ```

2. **Clear Cache Regularly**
   ```python
   # In migrate.py, add memory cleanup
   import gc
   gc.collect()
   ```

## Data Integrity Issues

### Missing Issues After Migration

**Symptoms:**
- Fewer GitHub issues than Azure DevOps work items
- Work items not found

**Solutions:**

1. **Check if Work Item Migration is Disabled (Common for Jira Users)**
   ```bash
   # If you're using Jira, this is expected and correct
   grep "migrate_work_items.*false" config.json
   # This means no GitHub issues will be created (which is what you want with Jira)
   ```

2. **Check Work Item States**
   ```json
   {
     "migration": {
       "include_closed_work_items": true
     }
   }
   ```

2. **Verify Date Filters**
   ```json
   {
     "filters": {
       "date_range": {
         "start_date": "",  // Remove date restrictions
         "end_date": ""
       }
     }
   }
   ```

3. **Check Work Item Types**
   ```json
   {
     "filters": {
       "exclude_work_item_types": []  // Don't exclude any types
     }
   }
   ```

### Corrupted Issue Content

**Symptoms:**
- Malformed issue descriptions
- Missing formatting

**Solutions:**

1. **Validate HTML Input**
   ```python
   # Check for malformed HTML
   from bs4 import BeautifulSoup
   soup = BeautifulSoup(html_content, 'html.parser')
   ```

2. **Update Conversion Settings**
   ```python
   # In utils.py
   h.unicode_snob = True
   h.escape_snob = True
   ```

## Common Error Messages

### "Project not found"

**Cause:** Invalid project name or no access to project

**Solution:**
```bash
# List available projects
python analyze.py --list-projects
```

### "Repository not found in project"

**Cause:** Repository name doesn't exist or is misspelled

**Solution:**
```bash
# List repositories in project
python analyze.py --project "MyProject" --list-repos
```

### "Maximum retries exceeded"

**Cause:** Network issues or API problems

**Solution:**
```json
{
  "migration": {
    "max_retries": 5,
    "delay_between_requests": 2.0
  }
}
```

### "Invalid JSON in configuration"

**Cause:** Malformed JSON in config file

**Solution:**
```bash
# Validate JSON syntax
python -m json.tool config.json
```

## Debug Tools and Techniques

### Enable Verbose Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### API Call Debugging

```python
# In migrate.py, add request/response logging
import requests
import http.client as http_client

http_client.HTTPConnection.debuglevel = 1
logging.getLogger("requests.packages.urllib3").setLevel(logging.DEBUG)
logging.getLogger("requests.packages.urllib3").propagate = True
```

### Memory Profiling

```bash
pip install memory-profiler
python -m memory_profiler migrate.py --project "MyProject" --repo "my-repo"
```

### Network Debugging

```bash
# Monitor network traffic
sudo tcpdump -i any -w migration_traffic.pcap host api.github.com
```

### Configuration Debugging

```python
# Print loaded configuration
import json
print(json.dumps(config, indent=2))
```

## Getting Additional Help

If issues persist after trying these solutions:

1. **Check Migration Logs**
   ```bash
   tail -f migration.log
   ```

2. **Create Minimal Reproduction Case**
   - Test with single repository
   - Use minimal configuration
   - Enable debug logging

3. **Gather System Information**
   ```bash
   python --version
   pip freeze > requirements_actual.txt
   uname -a  # Linux/Mac
   systeminfo  # Windows
   ```

4. **Document the Issue**
   - Exact error message
   - Configuration used
   - Steps to reproduce
   - System information

## Performance Monitoring

### Monitor Migration Progress

```bash
# Watch log file for progress
tail -f migration.log | grep -E "(INFO|ERROR|SUCCESS)"

# Monitor API rate limits
curl -H "Authorization: token YOUR_GITHUB_TOKEN" https://api.github.com/rate_limit
```

### Resource Monitoring

```bash
# Monitor CPU and memory usage
htop
# Or on Windows
taskmgr

# Monitor disk usage
du -sh migration_reports/
df -h
```

This troubleshooting guide covers the most common issues encountered during Azure DevOps to GitHub migrations. For specific issues not covered here, enable debug logging and examine the detailed error messages and stack traces.