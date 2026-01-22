# Contributing to Gmail Agent

Thank you for your interest in contributing to the Gmail Agent project! This document provides guidelines and instructions for contributing.

## Code of Conduct

Be respectful and professional in all interactions.

## Getting Started

### Prerequisites
- Python 3.8+
- Git
- pip or conda

### Setup Development Environment

1. Clone the repository:
```bash
git clone https://github.com/bhanuteja449896/gmail_agent.git
cd gmail_agent
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

4. Install pre-commit hooks:
```bash
pre-commit install
```

## Development Workflow

### Branch Naming
- Feature: `feature/description`
- Bug fix: `fix/description`
- Documentation: `docs/description`
- Release: `release/version`

### Commit Messages
Follow conventional commits format:
```
type(scope): subject

body

footer
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Example:
```
feat(auth): add JWT token refresh endpoint

This allows clients to refresh expired tokens without re-authentication.

Closes #123
```

### Testing

Run tests locally:
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_auth.py

# Run with verbose output
pytest -v

# Run specific test
pytest tests/unit/test_auth.py::TestAuth::test_login
```

### Code Quality

Before committing, ensure code quality:
```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Lint code
flake8 src/ tests/

# Type check
mypy src/

# Security check
bandit -r src/
```

Or use pre-commit to run all checks:
```bash
pre-commit run --all-files
```

## Creating a Pull Request

1. Create a feature branch:
```bash
git checkout -b feature/my-feature
```

2. Make your changes and write tests

3. Ensure all tests pass:
```bash
pytest --cov=src
```

4. Format and lint your code:
```bash
black src/ tests/
isort src/ tests/
flake8 src/ tests/
```

5. Push your branch:
```bash
git push origin feature/my-feature
```

6. Create a Pull Request on GitHub with:
   - Clear title describing the change
   - Detailed description of what changed and why
   - Reference to related issues
   - Test coverage information

## PR Review Process

- At least one approval required
- All CI/CD checks must pass
- Code coverage should not decrease
- Meaningful commit history preferred

## Testing Guidelines

### Unit Tests
- Test one unit in isolation
- Mock external dependencies
- Use fixtures for setup/teardown
- Aim for >80% coverage

### Integration Tests
- Test interactions between components
- Use test databases when needed
- Verify end-to-end workflows

### Example Test Structure
```python
class TestMyFeature:
    """Test my feature."""
    
    def test_successful_operation(self):
        """Test successful operation."""
        # Arrange
        input_data = {...}
        
        # Act
        result = my_function(input_data)
        
        # Assert
        assert result == expected_output
    
    def test_error_handling(self):
        """Test error handling."""
        with pytest.raises(ValueError):
            my_function(invalid_input)
```

## Documentation

- Add docstrings to all functions/classes
- Use Google-style docstrings
- Update README.md for significant changes
- Add type hints to all function signatures

Example:
```python
def process_email(email_id: str, priority: int = 0) -> Dict[str, Any]:
    """Process an email message.
    
    Args:
        email_id: The ID of the email to process
        priority: Priority level (0-10), defaults to 0
        
    Returns:
        Dictionary containing processing results with keys:
            - success: bool indicating if processing succeeded
            - message: str describing the result
            - data: Optional processed email data
            
    Raises:
        ValueError: If email_id is invalid
        ConnectionError: If unable to connect to email service
    """
```

## Reporting Issues

When reporting issues:
1. Use a clear, descriptive title
2. Provide detailed reproduction steps
3. Include expected vs actual behavior
4. Add relevant version/environment info
5. Attach logs or error messages

## Release Process

1. Update version number
2. Update CHANGELOG.md
3. Create release branch: `release/v1.2.3`
4. Create GitHub release with tag `v1.2.3`
5. CI/CD automatically publishes to PyPI

## Questions?

- Check existing issues/discussions
- Review documentation
- Create a new discussion for questions
- Contact maintainers directly

## License

By contributing, you agree that your contributions will be licensed under the project's license.

Thank you for contributing! 🎉
