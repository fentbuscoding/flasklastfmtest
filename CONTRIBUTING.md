# Contributing to Last.fm Scrobbler

Thank you for your interest in contributing to Last.fm Scrobbler! This document provides guidelines and information for contributors.

## 🤝 How to Contribute

### Reporting Bugs

1. **Check existing issues** - Search the issue tracker to avoid duplicates
2. **Use the bug report template** - Provide detailed information
3. **Include relevant details**:
   - Operating system and version
   - Python version
   - Browser and version (if applicable)
   - Steps to reproduce
   - Expected vs actual behavior
   - Error messages or screenshots

### Suggesting Features

1. **Check existing discussions** - Look for similar feature requests
2. **Use the feature request template** - Explain your idea clearly
3. **Provide context**:
   - What problem does this solve?
   - Who would benefit from this feature?
   - Are there any alternatives?
   - Mockups or examples (if applicable)

### Code Contributions

1. **Fork the repository**
2. **Create a feature branch** - `git checkout -b feature/your-feature-name`
3. **Make your changes** - Follow the coding standards below
4. **Add tests** - Ensure your changes are tested
5. **Update documentation** - Update README, docstrings, etc.
6. **Submit a pull request** - Use the PR template

## 📋 Development Setup

### Prerequisites

- Python 3.9 or higher
- Git
- A Last.fm account for testing

### Setup Instructions

1. **Clone your fork**
   ```bash
   git clone https://github.com/yourusername/lastfm-scrobbler.git
   cd lastfm-scrobbler
   ```

2. **Set up virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -e .  # Install in development mode
   ```

4. **Set up environment**
   ```bash
   cp .env.example .env
   # Edit .env with your test API credentials
   ```

5. **Run tests**
   ```bash
   pytest
   ```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov=token_store

# Run specific test file
pytest tests/test_app.py -v

# Run tests matching a pattern
pytest -k "test_scrobble"
```

### Writing Tests

- Place test files in the `tests/` directory
- Follow the naming convention: `test_*.py`
- Use descriptive test names: `test_scrobble_with_custom_time`
- Mock external API calls using `pytest` fixtures
- Aim for high test coverage on new code

### Test Categories

- **Unit Tests** - Test individual functions and methods
- **Integration Tests** - Test component interactions
- **API Tests** - Test external API interactions (mocked)

## 🎨 Code Style

### Python Style Guide

We follow [PEP 8](https://pep8.org/) with some modifications:

- **Line length**: 88 characters (Black default)
- **String quotes**: Double quotes preferred
- **Import sorting**: Use `isort` with Black profile
- **Type hints**: Use where appropriate, especially for public APIs

### Code Formatting

```bash
# Format code
black .

# Sort imports
isort .

# Check formatting
black --check .
isort --check-only .
```

### Linting

```bash
# Lint code
flake8 .

# Security scan
bandit -r . -ll

# Type checking (if using mypy)
mypy app.py token_store.py
```

## 📖 Documentation

### Docstrings

Use Google-style docstrings:

```python
def scrobble_track(artist: str, track: str, timestamp: int = None) -> bool:
    """Scrobble a track to Last.fm.
    
    Args:
        artist: The artist name
        track: The track name  
        timestamp: Unix timestamp (optional, defaults to now)
        
    Returns:
        True if successful, False otherwise
        
    Raises:
        LastFMError: If the API request fails
    """
```

### Code Comments

- Use comments sparingly for complex logic
- Prefer self-documenting code with clear variable names
- Add comments for business logic and API quirks
- Keep comments up-to-date with code changes

## 🏗️ Architecture Guidelines

### File Organization

```
app.py              # Main Flask application
token_store.py      # Token storage and encryption
config.py           # Configuration management
models/             # Data models (if added)
services/           # Business logic services
utils/              # Utility functions
tests/              # Test suite
```

### Design Principles

- **Single Responsibility** - Each function/class has one clear purpose
- **Dependency Injection** - Pass dependencies as parameters
- **Error Handling** - Use custom exceptions and proper error messages
- **Security First** - Always validate input and encrypt sensitive data

## 🔒 Security Guidelines

### Sensitive Data

- Never commit API keys, tokens, or passwords
- Use environment variables for configuration
- Encrypt sensitive data at rest
- Use secure session management

### Input Validation

- Validate all user input
- Sanitize data before database operations
- Use parameterized queries
- Implement rate limiting

### Authentication

- Use secure session cookies
- Implement CSRF protection
- Validate OAuth tokens properly
- Handle authentication errors gracefully

## 🚀 Pull Request Process

### Before Submitting

1. **Update your branch**
   ```bash
   git checkout main
   git pull upstream main
   git checkout your-feature-branch
   git rebase main
   ```

2. **Run the full test suite**
   ```bash
   pytest
   black --check .
   isort --check-only .
   flake8 .
   bandit -r . -ll
   ```

3. **Update documentation** if needed

### PR Requirements

- [ ] Tests pass
- [ ] Code is formatted (Black + isort)
- [ ] No linting errors
- [ ] Documentation updated
- [ ] CHANGELOG.md updated (for significant changes)
- [ ] PR description follows template

### Review Process

1. **Automated checks** must pass
2. **Code review** by maintainers
3. **Testing** in development environment
4. **Approval** and merge

## 🏷️ Issue Labels

We use these labels to categorize issues:

- `bug` - Something isn't working
- `enhancement` - New feature or request
- `documentation` - Improvements to documentation
- `good first issue` - Good for newcomers
- `help wanted` - Extra attention is needed
- `security` - Security-related issues
- `performance` - Performance improvements
- `ui/ux` - User interface and experience

## 📅 Release Process

### Version Numbers

We use [Semantic Versioning](https://semver.org/):
- `MAJOR.MINOR.PATCH`
- Major: Breaking changes
- Minor: New features (backward compatible)
- Patch: Bug fixes

### Release Checklist

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create release branch
4. Run full test suite
5. Create GitHub release
6. Deploy to production

## 🆘 Getting Help

### Community

- **GitHub Discussions** - General questions and ideas
- **GitHub Issues** - Bug reports and feature requests
- **Code Review** - Get feedback on your contributions

### Maintainers

Current maintainers:
- [@yourusername](https://github.com/yourusername) - Lead maintainer

### Resources

- [Flask Documentation](https://flask.palletsprojects.com/)
- [Last.fm API Documentation](https://www.last.fm/api/intro)
- [Python Testing 101](https://realpython.com/python-testing/)
- [Git Workflow](https://www.atlassian.com/git/tutorials/comparing-workflows)

## 📜 Code of Conduct

### Our Pledge

We are committed to making participation in this project a harassment-free experience for everyone, regardless of age, body size, disability, ethnicity, gender identity and expression, level of experience, nationality, personal appearance, race, religion, or sexual identity and orientation.

### Expected Behavior

- Use welcoming and inclusive language
- Be respectful of differing viewpoints
- Gracefully accept constructive criticism
- Focus on what is best for the community
- Show empathy towards other community members

### Unacceptable Behavior

- Harassment of any kind
- Discriminatory language or behavior
- Personal attacks or insults
- Publishing private information without permission
- Other conduct which could reasonably be considered inappropriate

### Enforcement

Report any behavior that violates this code of conduct to the maintainers. All reports will be handled confidentially.

---

Thank you for contributing to Last.fm Scrobbler! 🎵