# GitHub Automation

This directory contains GitHub Actions workflows and configurations.

## Workflows

### 🔄 CI Pipeline (`ci.yml`)
**Triggers:** Push to main/develop, Pull Requests
- **Lint**: Runs Ruff linter and formatter checks
- **Security**: Runs Bandit security scanner
- **Test**: Runs pytest on Python 3.12 and 3.13
- **Coverage**: Uploads coverage to Codecov

### 🔒 Security Scans

#### CodeQL (`codeql.yml`)
**Triggers:** Push, PRs, Weekly schedule (Sunday)
- Performs advanced security analysis
- Identifies potential vulnerabilities
- Security and quality queries

#### Dependency Review (`dependency-review.yml`)
**Triggers:** Pull Requests
- Reviews dependency changes in PRs
- Fails on moderate+ severity vulnerabilities
- Posts summary in PR comments

### 🤖 Automated Updates

#### Pre-commit Auto-update (`pre-commit-autoupdate.yml`)
**Triggers:** Weekly (Monday), Manual
- Automatically updates pre-commit hooks
- Creates PR with updates
- Labels: `dependencies`, `automated`

#### Dependabot (`dependabot.yml`)
**Triggers:** Weekly (Monday)
- Updates GitHub Actions weekly
- Updates Python dependencies weekly
- Groups related dependencies
- Auto-labels PRs

### 🚀 Release (`release.yml`)
**Triggers:** Tags matching `v*.*.*`, Manual
- Builds distribution packages
- Creates GitHub Release with notes
- Publishes to PyPI (when configured)

## Configuration Files

### CODEOWNERS
Defines code ownership and auto-assigns reviewers

### Pull Request Template
Standardized PR description template

## Setup Required

### For Codecov (Optional)
1. Sign up at https://codecov.io
2. Add `CODECOV_TOKEN` to repository secrets

### For PyPI Publishing (Optional)
1. Set up PyPI trusted publishing
2. Uncomment PyPI publish step in `release.yml`

## Usage

All workflows run automatically based on their triggers. You can also:

```bash
# Trigger workflows manually (using hub)
hub api -X POST repos/:owner/:repo/actions/workflows/ci.yml/dispatches -f ref=main
hub api -X POST repos/:owner/:repo/actions/workflows/pre-commit-autoupdate.yml/dispatches -f ref=main

# View workflow runs
hub api repos/:owner/:repo/actions/runs

# View pull requests
hub pr list
```

## Local Testing

Test workflows locally using [act](https://github.com/nektos/act):

```bash
# Install act
brew install act  # macOS

# Run CI workflow locally
act pull_request

# Run specific job
act -j lint
```
