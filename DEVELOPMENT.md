# Development Setup Guide

Complete guide for setting up a development environment for the Gmail Agent project.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Advanced Setup](#advanced-setup)
- [Running Tests](#running-tests)
- [Code Quality](#code-quality)
- [Debugging](#debugging)
- [Common Issues](#common-issues)

## Prerequisites

### Required

- **Python**: 3.8 or higher (3.11 recommended)
- **Git**: For version control
- **pip**: Python package manager (comes with Python)
- **Virtual Environment**: venv or conda

### Recommended

- **Docker**: For containerized development
- **GitHub CLI**: For PR management
- **IDE**: VS Code, PyCharm, or similar with Python support

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/bhanuteja449896/gmail_agent.git
cd gmail_agent
```

### 2. Create Virtual Environment

```bash
# Using venv
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Or using conda
conda create -n gmail_agent python=3.11
conda activate gmail_agent
```

### 3. Install Dependencies

```bash
# Install runtime dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements.txt
pip install pytest pytest-cov black isort flake8 mypy bandit pre-commit
```

### 4. Install Pre-commit Hooks

```bash
pre-commit install
```

### 5. Run Tests

```bash
pytest tests/ -v
```

## Advanced Setup

### Development with Tox

Test against multiple Python versions:

```bash
# Install tox
pip install tox

# Run all environments
tox

# Run specific environment
tox -e py311

# Run linting
tox -e lint

# Run type checking
tox -e type
```

### Development with Docker

```bash
# Build development image
docker build -f Dockerfile.dev -t gmail_agent:dev .

# Run container
docker run -it --rm -v $(pwd):/app gmail_agent:dev bash

# Run tests in container
docker run -it --rm -v $(pwd):/app gmail_agent:dev pytest tests/ -v
```

### IDE Setup

#### VS Code

1. Install extensions:
   - Python
   - Pylance
   - Black Formatter
   - Flake8
   - mypy Type Checker

2. Create `.vscode/settings.json`:

```json
{
  "[python]": {
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "ms-python.black-formatter",
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    }
  },
  "python.linting.flake8Enabled": true,
  "python.linting.flake8Args": ["--max-line-length=100"],
  "python.linting.mypyEnabled": true,
  "python.linting.banditEnabled": true
}
```

#### PyCharm

1. Set Python interpreter: Settings → Project → Python Interpreter
2. Enable code inspections: Settings → Editor → Inspections
3. Configure code style: Settings → Editor → Code Style → Python
4. Enable pre-commit hooks: Settings → Tools → Python Integrated Tools → Pre-commit

## Running Tests

### Basic Test Execution

```bash
# Run all tests
pytest tests/

# Run with verbose output
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_example.py

# Run tests matching pattern
pytest tests/ -k "test_email"
```

### Test Categories

Tests are organized by markers:

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run unit and integration, skip slow tests
pytest -m "not slow"

# Run specific category
pytest -m regression
```

### Continuous Testing

Watch tests with `pytest-watch`:

```bash
pip install pytest-watch
ptw tests/ -- -v
```

## Code Quality

### Code Formatting

```bash
# Format with black
black src/ tests/

# Sort imports with isort
isort src/ tests/

# Do both
black . && isort .
```

### Linting

```bash
# Lint with flake8
flake8 src/ tests/

# Check style compliance
pylint src/
```

### Type Checking

```bash
# Type check with mypy
mypy src/

# Strict mode
mypy src/ --strict
```

### Security Scanning

```bash
# Bandit
bandit -r src/ -ll

# Safety
safety check

# Pip audit
pip-audit
```

### Pre-commit Hooks

```bash
# Run all hooks
pre-commit run --all-files

# Update hook versions
pre-commit autoupdate

# Skip hooks (use sparingly)
git commit --no-verify
```

## Debugging

### Using Python Debugger (pdb)

```python
# Add to code
import pdb; pdb.set_trace()

# Or use breakpoint() (Python 3.7+)
breakpoint()
```

### VS Code Debugging

Create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Debug Tests",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": ["tests/", "-v", "-s"],
      "console": "integratedTerminal"
    }
  ]
}
```

### Pytest Debug Mode

```bash
# Show print statements
pytest tests/ -s

# Drop into debugger on failure
pytest tests/ --pdb

# Drop into debugger at start of each test
pytest tests/ --trace
```

## Common Issues

### Import Errors

```bash
# Reinstall package in editable mode
pip install -e .

# Verify PYTHONPATH
echo $PYTHONPATH
```

### Virtual Environment Issues

```bash
# Remove and recreate venv
rm -rf venv/
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Pre-commit Hook Failures

```bash
# Run specific hook
pre-commit run black --all-files

# Skip hook temporarily
git commit --no-verify
```

### Test Failures

```bash
# Run with full traceback
pytest tests/ -vv

# Run with print output
pytest tests/ -s

# Run single test with debug
pytest tests/test_example.py::test_case -vv -s
```

### Dependency Conflicts

```bash
# Clear pip cache
pip cache purge

# Reinstall from fresh requirements
pip install --force-reinstall -r requirements.txt
```

## Contributing

Before submitting a PR:

1. Ensure all tests pass: `pytest tests/`
2. Run code quality checks: `pre-commit run --all-files`
3. Update tests for new features
4. Update documentation
5. Follow commit conventions from [CONTRIBUTING.md](CONTRIBUTING.md)

## Resources

- [Python Official Docs](https://docs.python.org/3/)
- [pytest Documentation](https://docs.pytest.org/)
- [Black Code Formatter](https://black.readthedocs.io/)
- [Gmail API Reference](https://developers.google.com/gmail/api/reference/rest)

## Getting Help

- Check [GitHub Issues](https://github.com/bhanuteja449896/gmail_agent/issues)
- Review [CONTRIBUTING.md](CONTRIBUTING.md)
- Open a [Discussion](https://github.com/bhanuteja449896/gmail_agent/discussions)

## Need Support?

Please see [CONTRIBUTING.md](CONTRIBUTING.md) for support channels.
