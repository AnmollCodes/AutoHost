# Contributing to AutoHost

Thank you for your interest in contributing to AutoHost! This document provides guidelines and steps for contributing.

## Code of Conduct

We are committed to providing a welcoming and inclusive environment. Please be respectful to all contributors.

## Getting Started

### Prerequisites

- Python 3.11+
- Git
- Docker (optional)
- Ollama (optional)

### Development Setup

```bash
# 1. Fork and clone
git clone https://github.com/yourusername/autohost.git
cd autohost

# 2. Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install development dependencies
pip install -e ".[dev]"

# 4. Set up pre-commit hooks
pre-commit install

# 5. Run tests to verify setup
pytest
```

## Development Workflow

### 1. Create a Branch

```bash
# Branch naming conventions
git checkout -b feature/description       # New feature
git checkout -b bugfix/description        # Bug fix
git checkout -b docs/description          # Documentation
git checkout -b refactor/description      # Code refactoring
```

### 2. Make Changes

- Keep commits atomic and logical
- Follow code style guidelines (see below)
- Add tests for new functionality
- Update documentation as needed

### 3. Code Style Guidelines

**Python (PEP 8)**:
```bash
# Format code
ruff format agent tests

# Check linting
ruff check agent tests

# Type checking
mypy agent
```

**Imports**:
- Use absolute imports: `from agent.orchestrator import server`
- Not relative: `from ..orchestrator import server`
- Group: stdlib, third-party, local

**Naming**:
- Functions/variables: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private members: `_leading_underscore`

**Docstrings**:
```python
def analyze_code(path: str, rules: List[str]) -> dict:
    """Analyze Python code for issues.
    
    Args:
        path: File path to analyze
        rules: List of rule names to check
        
    Returns:
        Dictionary with issues found
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If rules list is empty
    """
    pass
```

### 4. Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=agent --cov-report=term-missing

# Run specific test
pytest tests/test_react_agent.py::TestReActLoop::test_observe_state -v

# Run security tests
pytest tests/test_security.py -v

# Run with markers
pytest -m "not slow"  # Skip slow tests
```

**Test Files**:
- Place in `tests/` directory
- Name: `test_*.py`
- Use pytest conventions
- Aim for >80% coverage

### 5. Commit Messages

Format: `<type>: <subject>`

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Code style (no logic change)
- `refactor`: Code refactoring
- `test`: Test additions/changes
- `chore`: Build, dependencies, etc.

Examples:
```
feat: add RestrictedPython sandbox isolation
fix: sanitize LLM prompt injections
docs: update deployment guide for Docker
test: add security vulnerability tests
```

### 6. Create Pull Request

**Title**: Clear, descriptive title

**Description Template**:
```markdown
## Description
Brief description of changes

## Related Issues
Fixes #123

## Type of Change
- [ ] New feature
- [ ] Bug fix
- [ ] Documentation
- [ ] Breaking change

## Testing
- [ ] Added tests
- [ ] All tests passing
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] No new warnings generated
- [ ] Documentation updated
- [ ] Tests added/updated
```

**PR Requirements**:
- ✅ Tests passing (CI/CD)
- ✅ Code coverage maintained (>80%)
- ✅ No new security issues
- ✅ Documentation updated
- ✅ At least 1 approval

## Areas for Contribution

### High Priority

- [ ] Performance optimization (async, caching)
- [ ] Additional LLM providers (Anthropic, OpenAI, etc.)
- [ ] Enhanced sandbox options (GPU support)
- [ ] Database backends (PostgreSQL, MySQL)
- [ ] Monitoring/logging improvements

### Medium Priority

- [ ] Documentation improvements
- [ ] Example scripts
- [ ] Bug fixes
- [ ] Test coverage expansion
- [ ] CI/CD improvements

### Low Priority

- [ ] UI improvements
- [ ] Minor refactoring
- [ ] Development tooling

## Reporting Issues

### Before Reporting

- Check existing issues (GitHub Issues)
- Check documentation (./docs/)
- Try latest version

### Issue Template

**Title**: Clear, concise title

**Body**:
```markdown
## Description
Clear description of the issue

## Steps to Reproduce
1. Step 1
2. Step 2
3. Step 3

## Expected Behavior
What should happen

## Actual Behavior
What actually happens

## Screenshots/Logs
If applicable, add screenshots or logs

## Environment
- OS: [e.g., Linux, macOS, Windows]
- Python: [e.g., 3.11.2]
- AutoHost Version: [e.g., 1.0.0]
```

### Security Issues

**DO NOT** open public issues for security vulnerabilities.  
Email: **security@autohost.dev**

## Documentation

### Adding Docs

1. Create file in `docs/` directory
2. Use Markdown format
3. Include code examples
4. Update main `README.md` if necessary

### Documentation Templates

**API Endpoint**:
```markdown
### POST /api/tasks

Create a new task for the agent to execute.

**Parameters**:
- `request` (string, required): Task description

**Response** (201 Created):
```json
{
  "id": "task-123",
  "request": "...",
  "created_at": "2024-01-01T00:00:00Z"
}
```

**Errors**:
- `400 Bad Request`: Invalid input
- `401 Unauthorized`: Missing authentication
- `429 Too Many Requests`: Rate limited
```

## Release Process

### Version Numbering

Using Semantic Versioning: `MAJOR.MINOR.PATCH`

- `MAJOR`: Breaking changes
- `MINOR`: New features (backward compatible)
- `PATCH`: Bug fixes

### Release Steps

1. Update version in `agent/version.py`
2. Update `CHANGELOG.md`
3. Create git tag: `git tag v1.0.0`
4. Push tag: `git push origin v1.0.0`
5. GitHub Actions triggers release workflow
6. Artifacts published to PyPI

## Getting Help

- 📖 [Documentation](./docs/)
- 💬 [Discussions](https://github.com/yourusername/autohost/discussions)
- 🐛 [Issues](https://github.com/yourusername/autohost/issues)
- 📧 Email: team@autohost.dev

## Recognition

Contributors are recognized in:
- `CONTRIBUTORS.md`
- Release notes
- GitHub profile (automatic)

Thank you for contributing! 🎉
