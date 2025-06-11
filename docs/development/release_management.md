# Release Management and Automation

This document describes the automated release management system implemented for the HB Candles Feed project.

## Overview

The automated release management system provides:

- **Semantic Versioning**: Automatic version calculation based on conventional commits
- **Automated Changelog**: Generated from commit history using conventional changelog
- **PyPI Publishing**: Trusted publishing to PyPI with comprehensive verification
- **Multi-platform Testing**: Comprehensive testing across Python versions and platforms
- **TaskMaster Integration**: Project status integration in release notes
- **Tag Protection**: Repository protection rules for release integrity

## Release Triggers

### 1. Manual Release (workflow_dispatch)
```bash
# Trigger via GitHub UI or CLI
gh workflow run "Automated Release Management" \
  -f version=v2.5.0 \
  -f prerelease=false \
  -f skip_tests=false
```

### 2. Tag-based Release (push)
```bash
# Create and push a tag
git tag v2.5.0
git push origin v2.5.0
```

### 3. Automated Release (schedule)
- Runs every Sunday at 2 AM UTC
- Analyzes commits since last release
- Automatically determines version bump based on conventional commits
- Creates release if significant changes are detected

## Conventional Commits

The system uses conventional commits to determine version bumps:

- `feat:` → Minor version bump (new features)
- `fix:` → Patch version bump (bug fixes)
- `BREAKING CHANGE:` → Major version bump (breaking changes)
- `docs:`, `chore:`, `style:`, `refactor:`, `test:` → No version bump

### Examples
```bash
# Minor bump (2.4.0 → 2.5.0)
git commit -m "feat: add new adapter for Exchange X"

# Patch bump (2.4.0 → 2.4.1)
git commit -m "fix: resolve connection timeout in Binance adapter"

# Major bump (2.4.0 → 3.0.0)
git commit -m "feat: redesign adapter interface

BREAKING CHANGE: Adapter interface signature changed"
```

## PyPI Publishing Setup

### 1. Trusted Publishing Configuration

1. **PyPI Configuration**:
   - Go to PyPI project settings: https://pypi.org/manage/project/hb-candles-feed/
   - Navigate to "Publishing" → "Add a new publisher"
   - Configure trusted publishing with:
     - **Repository**: `MementoRC/hb-candles-feed`
     - **Workflow**: `release.yml`
     - **Environment**: `pypi`

2. **GitHub Environment Setup**:
   ```bash
   # Create the PyPI environment in GitHub repository settings
   # Settings → Environments → New Environment
   # Name: pypi
   # Protection rules: Require reviewers (optional for automatic releases)
   ```

### 2. PyPI Token Setup (Alternative)

If trusted publishing is not available:

```bash
# Generate PyPI API token
# PyPI Account Settings → API tokens → Add API token
# Scope: Specific project (hb-candles-feed)

# Add to GitHub Secrets
# Settings → Secrets and variables → Actions
# Repository secrets → New repository secret
# Name: PYPI_API_TOKEN
# Value: pypi-xxx...
```

## Tag Protection Rules

Configure the following protection rules in GitHub repository settings:

### 1. Tag Protection Rules
```yaml
# Settings → Code and automation → Tags → Add rule
Pattern: v*.*.*
Restrict pushes that create matching tags:
  - Restrict pushes: Yes
  - Who can push: 
    - GitHub Actions (via GITHUB_TOKEN)
    - Repository administrators
```

### 2. Branch Protection Rules
```yaml
# Settings → Code and automation → Branches
Branch name pattern: main
Protection rules:
  - Require a pull request before merging
  - Require status checks to pass before merging:
    - CI / Build and Test Matrix
    - CI / Security Scanning
    - CI / Quality Gates
  - Require conversation resolution before merging
  - Require signed commits: Yes
  - Include administrators: Yes
```

## Release Workflow Stages

### 1. Version Detection and Validation
- Detects release trigger source (manual, tag, scheduled)
- Validates semantic version format
- Checks for version conflicts
- Generates automated changelog

### 2. Changelog Management
- Updates CHANGELOG.md with new release information
- Uses conventional commits for categorization
- Commits changelog updates automatically

### 3. Package Building
- Updates version in `candles_feed/__about__.py`
- Builds wheel and source distributions using hatch
- Verifies package integrity and metadata

### 4. Comprehensive Testing
- Multi-platform testing (Ubuntu, macOS, Windows)
- Multi-version Python testing (3.10, 3.11, 3.12)
- Installation verification from built packages
- Functional and integration testing
- Performance validation

### 5. PyPI Publishing
- Publishes to PyPI using trusted publishing
- Verifies successful publication
- Tests installation from PyPI

### 6. GitHub Release Creation
- Creates GitHub release with comprehensive notes
- Includes TaskMaster project status (if available)
- Attaches build artifacts
- Links to PyPI package and documentation

## Quality Gates

The release process includes mandatory quality gates:

1. **Version Validation**: Format and uniqueness checks
2. **Package Integrity**: Metadata and structure verification
3. **Test Suite**: Comprehensive multi-platform testing
4. **Security Scanning**: Automated vulnerability detection
5. **Performance**: Import speed and memory usage validation

## Emergency Procedures

### Skip Testing (Emergency Releases)
```bash
gh workflow run "Automated Release Management" \
  -f version=v2.4.1 \
  -f prerelease=false \
  -f skip_tests=true
```

### Pre-release Creation
```bash
gh workflow run "Automated Release Management" \
  -f version=v2.5.0-alpha.1 \
  -f prerelease=true
```

### Rollback Procedure
```bash
# 1. Remove problematic tag
git tag -d v2.5.0
git push origin :refs/tags/v2.5.0

# 2. Delete GitHub release
gh release delete v2.5.0

# 3. Revert version in __about__.py
git checkout HEAD~1 -- candles_feed/__about__.py
git commit -m "revert: rollback version to previous release"

# 4. Contact PyPI to remove problematic version (if published)
```

## Monitoring and Alerts

### Release Notifications
- GitHub releases automatically notify watchers
- Integration with project communication channels
- TaskMaster status updates for project tracking

### Failure Handling
- Failed releases trigger GitHub notifications
- Detailed logs available in GitHub Actions
- Automatic rollback on critical failures

## Best Practices

1. **Use Conventional Commits**: Ensures accurate version bumping
2. **Test Locally**: Run tests before pushing changes
3. **Review Changelogs**: Verify generated changelogs before releases
4. **Monitor Releases**: Check PyPI and GitHub release status
5. **Version Consistency**: Ensure all version references are updated

## Troubleshooting

### Common Issues

1. **PyPI Upload Failures**:
   - Check trusted publishing configuration
   - Verify package metadata and structure
   - Ensure version doesn't already exist

2. **Test Failures**:
   - Review test logs in GitHub Actions
   - Run tests locally to reproduce issues
   - Check for environment-specific problems

3. **Version Conflicts**:
   - Ensure version doesn't already exist as tag
   - Check for version format compliance
   - Verify conventional commit messages

### Debug Commands

```bash
# Check release status
gh run list --workflow="Automated Release Management"

# View specific run details
gh run view <run-id>

# Check package status on PyPI
pip index versions hb-candles-feed

# Verify package installation
pip install hb-candles-feed==2.5.0 --dry-run
```

---

This automated release management system ensures consistent, reliable, and comprehensive releases while maintaining high quality standards and providing extensive visibility into the release process.