# GitHub Repository Configuration

## Overview
This directory contains GitHub-specific configuration files for the AI-Powered Pakistani News Anchor project.

## Contents

### Issue Templates
- **`bug_report.md`**: Template for reporting bugs and issues
- **`feature_request.md`:** Template for requesting new features
- **`question.md`:** Template for asking questions about the project

### Pull Request Template
- **`PULL_REQUEST_TEMPLATE.md`**: Standard template for all pull requests

### Workflows
- **`ci.yml`**: Continuous Integration workflow for testing and linting
- **`release.yml`**: Automated release workflow for PyPI and GitHub releases
- **`docs.yml`**: Documentation building and deployment workflow

## Usage

### Issue Templates
When creating a new issue, GitHub will automatically suggest the appropriate template based on the issue type. This ensures consistent and complete issue reports.

### Pull Request Template
All pull requests will use the standard template, ensuring contributors provide all necessary information for review.

### Workflows
GitHub Actions will automatically run these workflows based on the configured triggers:
- **CI**: Runs on every push and pull request to main branch
- **Release**: Runs when new tags are pushed (version releases)
- **Docs**: Builds and deploys documentation on main branch pushes

## Configuration

### CI Workflow
- Tests Python versions 3.8-3.11
- Runs pytest with coverage reporting
- Uploads coverage to Codecov
- Runs linting with flake8, black, and isort
- Security scanning with bandit and safety

### Release Workflow
- Builds Python package with build
- Publishes to PyPI with twine
- Creates GitHub releases automatically

### Docs Workflow
- Builds Sphinx documentation
- Deploys to GitHub Pages on main branch

## Contributing

When contributing to this project:
1. Use the appropriate issue template when reporting issues
2. Follow the pull request template when submitting changes
3. Ensure all tests pass before submitting
4. Follow the code style guidelines in CONTRIBUTING.md

## Maintenance

The workflows and templates in this directory should be maintained to:
- Keep up with GitHub Actions updates
- Ensure compatibility with project requirements
- Improve developer experience
- Maintain security best practices

---

**> Built with ❤️ for Pakistani news content creation**