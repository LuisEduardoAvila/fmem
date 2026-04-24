# Contributing to fmem

## Getting Started

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `python -m pytest tests/`

## Code Style

- Follow PEP 8
- Add docstrings to functions
- Include type hints where possible

## Testing

**Python core:**
```bash
python tests/test_fmem.py
```

**TypeScript plugin:**
```bash
cd plugins/openclaw-fmem-auto && npm run typecheck
```

Note: The TypeScript plugin has no runtime test suite yet. Type checking confirms type correctness of the plugin code.

## Submitting Changes

- Open a PR with clear description
- Link related issues
- Ensure tests pass
