# Contributing to fmem

Thank you for your interest in contributing to fmem! This document provides guidelines for contributing to the project.

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally
3. Install development dependencies
4. Create a new branch for your feature or bug fix

## Development Setup

### Prerequisites

- Python 3.8 or higher
- Ollama installed and running (for embedding generation)
- Git

### Installation Steps

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/DarthSpudFmem.git
cd DarthSpudFmem

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Pull required Ollama model
ollama pull nomic-embed-text

# Verify installation
python3 -c "from fmem import MemoryRetrieval; print('✓ fmem installed')"
```

### Development Dependencies

The `[dev]` extra includes:
- `pytest>=7.0` - Testing framework
- `pytest-cov>=4.0` - Coverage reporting
- `black>=23.0` - Code formatting
- `flake8>=6.0` - Linting
- `mypy>=1.0` - Type checking

## Code Style

- Follow PEP 8 guidelines
- Use type hints where appropriate
- Add docstrings for new functions and classes (Google style preferred)
- Keep functions focused and modular (single responsibility)
- Maximum line length: 100 characters (enforced by black)

### Formatting

```bash
# Format code
black fmem/ tests/

# Check linting
flake8 fmem/ tests/

# Type checking
mypy fmem/
```

## Testing

### Running Tests

Before submitting a pull request, ensure all tests pass:

```bash
# Run all tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=fmem --cov-report=term-missing

# Run specific test files
python -m pytest tests/test_chunking.py -v
python -m pytest tests/test_recency.py -v
python -m pytest tests/test_location_ranking.py -v

# Run with verbose output
python -m pytest tests/ -v

# Run failed tests only
python -m pytest tests/ --lf
```

### Pytest Configuration

Create `pytest.ini` in the project root for custom configuration:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    unit: marks tests as unit tests
```

Or use `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --tb=short"
markers = [
    "slow: marks tests as slow",
    "integration: marks tests as integration tests",
    "unit: marks tests as unit tests",
]
```

### Writing Tests

- Place tests in the `tests/` directory
- Name test files with `test_` prefix
- Use descriptive test function names
- Include docstrings explaining what is being tested
- Mock external dependencies (Ollama, file system) for unit tests

Example:

```python
def test_sanitize_path_traversal():
    """Test that path traversal attempts are blocked."""
    result = sanitize_path("../../../etc/passwd")
    assert result is None
```

## Code Review Process

### Before Submitting

1. **Self-review** your code:
   - [ ] All tests pass locally
   - [ ] Code is formatted with black
   - [ ] No flake8 warnings
   - [ ] Type hints are correct (mypy)
   - [ ] Docstrings are complete
   - [ ] Commit messages follow convention

2. **Update documentation** if needed:
   - README.md for user-facing changes
   - SECURITY.md for security-related changes
   - This file for process changes

3. **Add tests** for new functionality

### Pull Request Workflow

1. **Create a branch**: `git checkout -b feature/your-feature-name`
   - Use prefixes: `feature/`, `fix/`, `docs/`, `test/`, `refactor/`

2. **Make commits** with clear messages following convention

3. **Push to your fork**: `git push origin feature/your-feature-name`

4. **Open a Pull Request** with:
   - Clear title describing the change
   - Description explaining what and why
   - Reference to any related issues
   - Checklist of changes made

5. **Review process**:
   - Maintainers will review within 48 hours
   - Address feedback promptly
   - Keep discussion focused and professional
   - Request re-review when ready

### Review Criteria

Maintainers check for:
- Code correctness and edge cases
- Test coverage for new code
- Documentation completeness
- Security implications
- Performance impact
- Backward compatibility

## Commit Message Convention

Format: `<type>: <description>`

Types:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `test:` Test-related changes
- `refactor:` Code refactoring (no behavior change)
- `perf:` Performance improvements
- `style:` Code style changes (formatting, semicolons)
- `chore:` Maintenance tasks (deps, build, etc.)

Examples:
```
feat: add health check command to CLI
fix: handle empty query in search function
docs: update installation instructions
test: add unit tests for chunking function
refactor: extract validation logic to separate module
```

## Reporting Issues

When reporting issues, please include:
- OpenClaw version (if applicable)
- Python version: `python3 --version`
- Operating system and version
- fmem version: `python3 -m fmem.cli version`
- Steps to reproduce
- Expected vs actual behavior
- Full error messages and stack traces
- Relevant configuration files (sanitized)

### Security Issues

For security vulnerabilities, see [SECURITY.md](SECURITY.md). **Do not open public issues**.

## Development Tips

### Testing with Ollama

```bash
# Check Ollama status
curl http://localhost:11434/api/tags

# Test embedding generation
python3 -c "
from fmem.fmem import OllamaClient
client = OllamaClient()
print('Health:', client.health_check())
"
```

### Debugging

Enable debug logging:
```bash
export FMEM_DEBUG=1
python3 -m fmem.cli search "test query"
```

### Common Issues

**ImportError during development:**
```bash
# Ensure running from project root
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

**Ollama connection issues:**
- Verify Ollama is running: `ollama serve`
- Check URL in config: `FMEM_OLLAMA_URL`
- Test connection: `curl http://localhost:11434/api/tags`

## Questions?

Feel free to:
- Open an issue for questions
- Start a discussion in GitHub Discussions
- Join community channels (if available)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for helping make fmem better!**
