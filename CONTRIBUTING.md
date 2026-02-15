# Contributing to fmem

Thank you for your interest in contributing to fmem! This document provides guidelines for contributing to the project.

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally
3. Install development dependencies
4. Create a new branch for your feature or bug fix

## Development Setup

```bash
git clone https://github.com/LuisEduardoAvila/DarthSpudFmem.git
cd DarthSpudFmem
pip install -e ".[dev]"
```

## Code Style

- Follow PEP 8 guidelines
- Use type hints where appropriate
- Add docstrings for new functions and classes
- Keep functions focused and modular

## Testing

Before submitting a pull request, ensure all tests pass:

```bash
python -m pytest tests/
```

For chunk-level functionality:
```bash
python -m pytest tests/test_chunking.py -v
```

## Submitting Changes

1. Create a new branch: `git checkout -b feature/your-feature-name`
2. Make your changes and commit them: `git commit -m "feat: add your feature"`
3. Push to your fork: `git push origin feature/your-feature-name`
4. Submit a pull request

## Commit Message Convention

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `test:` Test-related changes
- `refactor:` Code refactoring
- `perf:` Performance improvements

## Reporting Issues

When reporting issues, please include:
- OpenClaw version
- Python version
- Operating system
- Steps to reproduce
- Expected vs actual behavior

## Questions?

Feel free to open an issue for questions or join discussions.
