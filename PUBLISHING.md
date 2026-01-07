# Publishing agentbench to PyPI

This guide walks you through publishing agentbench to PyPI for the first time.

## Prerequisites

1. **PyPI Account**: Create accounts on both:
   - **Test PyPI**: https://test.pypi.org/account/register/ (for testing)
   - **Production PyPI**: https://pypi.org/account/register/ (for real releases)

2. **API Token**: After creating your PyPI account:
   - Go to https://pypi.org/manage/account/
   - Scroll to "API tokens"
   - Click "Add API token"
   - Name it (e.g., "agentbench")
   - Scope: "Entire account" (for first time) or specific project
   - Copy the token (starts with `pypi-`)

## First Time Publishing Steps

### 1. Install build tools

```bash
pip install build twine
```

### 2. Update version (if needed)

Edit `pyproject.toml` and update the version number:
```toml
version = "0.0.1"
```

### 3. Clean previous builds

```bash
rm -rf dist/ build/ *.egg-info
```

### 4. Build the package

```bash
python -m build
```

This creates:
- `dist/agentbench-0.0.1.tar.gz` (source distribution)
- `dist/agentbench-0.0.1-py3-none-any.whl` (wheel)

### 5. Test on Test PyPI first (recommended)

```bash
# Upload to Test PyPI
twine upload --repository testpypi dist/*

# You'll be prompted for:
# - Username: __token__
# - Password: your test PyPI API token (starts with pypi-)
```

Then test installing from Test PyPI:
```bash
pip install --index-url https://test.pypi.org/simple/ agentbench
```

### 6. Publish to Production PyPI

Once you've verified on Test PyPI:

```bash
twine upload dist/*

# Username: __token__
# Password: your production PyPI API token
```

### 7. Verify Installation

```bash
pip install agentbench
python -c "import agentbench; print(agentbench.__version__)"
```

## Using GitHub Actions (Automated)

Once you've set up your PyPI API token:

1. Go to your GitHub repository
2. Settings → Secrets and variables → Actions
3. Add a new secret:
   - Name: `PYPI_API_TOKEN`
   - Value: Your PyPI API token

4. Create a GitHub Release:
   - Go to Releases → "Create a new release"
   - Tag: `v0.0.1` (must match version in pyproject.toml)
   - Title: `agentbench v0.0.1`
   - Description: Release notes
   - Click "Publish release"

The GitHub Action will automatically build and publish to PyPI!

## Updating Versions

For future releases:

1. Update version in `pyproject.toml`
2. Update version in `src/agentbench/__init__.py`
3. Commit and push
4. Create a new GitHub release with matching tag
5. GitHub Actions will publish automatically

## Troubleshooting

- **"Package already exists"**: Version already published, increment version
- **"Invalid credentials"**: Check your API token
- **"File already exists"**: Delete old files in `dist/` or increment version

