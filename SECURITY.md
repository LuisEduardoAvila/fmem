# fmem Security Documentation

## Overview

This document describes the security features, threats, and countermeasures implemented in the fmem skill.

**Version:** 2.0.0  
**Last Updated:** 2026-02-14  
**Author:** Security Team

---

## Table of Contents

1. [Security Features](#security-features)
2. [Threat Model](#threat-model)
3. [Security Controls](#security-controls)
4. [Secure Coding Practices](#secure-coding-practices)
5. [Security Testing](#security-testing)
6. [Incident Response](#incident-response)

---

## Security Features

### ✅ Implemented Security Controls

| Feature | Status | Description |
|---------|--------|-------------|
| Path Traversal Protection | ✅ | Prevents access to files outside allowed directories |
| Input Validation | ✅ | Validates all user inputs before processing |
| File Extension Whitelist | ✅ | Only allows specific file types to be indexed |
| Safe File Size Limits | ✅ | Prevents denial of service via large files |
| Query Length Limits | ✅ | Prevents resource exhaustion via long queries |
| Comprehensive Logging | ✅ | Security-relevant events are logged |
| Error Handling | ✅ | Graceful error handling without information leakage |

---

## Threat Model

### Threat Actors

1. **Malicious User** - Attempts to access sensitive files
2. **Compromised Agent** - Attempts to exploit memory system
3. **External Attacker** - Attempts remote code execution

### Attack Vectors

| Attack Vector | Severity | Countermeasure |
|---------------|----------|----------------|
| Path Traversal | Critical | Path sanitization with base directory validation |
| SQL Injection | High | Parameterized queries in SQLite |
| DoS (Large Files) | Medium | File size limits (50MB) |
| DoS (Long Queries) | Low | Query length limits (1000 chars) |
| Injection (Null Bytes) | Critical | Input sanitization |
| Control Character Injection | High | Input sanitization |

---

## Security Controls

### 1. Path Traversal Prevention

**Implementation:** `sanitize_path()` function

```python
def sanitize_path(filepath: str, base_dir: Optional[str] = None) -> Optional[str]:
    """Validate path to prevent path traversal attacks."""
    # Normalize path
    resolved = Path(filepath).resolve()
    
    # Get base directory
    if base_dir is None:
        base_dir = Path(CONFIG.data_dir).parent
    else:
        base_dir = Path(base_dir).resolve()
    
    # Check if path is within allowed directory
    try:
        resolved.relative_to(base_dir)
        return True
    except ValueError:
        return False
```

**Security Properties:**
- All file paths are normalized before validation
- Paths must be within allowed base directory
- Prevents `../` and absolute path attacks

### 2. File Extension Whitelist

**Implementation:** `ConfigManager.VALID_EXTENSIONS`

```python
VALID_EXTENSIONS = {'.md', '.txt', '.py', '.json', '.yaml', '.yml', '.csv'}
```

**Allowed file types:**
- `.md` - Markdown documentation
- `.txt` - Plain text files
- `.py` - Python source code
- `.json` - JSON configuration
- `.yaml`/`.yml` - YAML configuration
- `.csv` - CSV data files

**Blocklisted file types:**
- `.exe`, `.sh`, `.bat` - Executable files
- `.pyc`, `.pyo` - Compiled Python files
- `.so`, `.dll` - Shared libraries

### 3. Input Validation

**Query Validation:**
```python
def validate_query(self, query: str) -> Tuple[bool, str]:
    """Validate search query."""
    if not query or not isinstance(query, str):
        return False, "Query must be a non-empty string"
    
    if len(query) > self.MAX_QUERY_LENGTH:
        return False, f"Query too long (max {self.MAX_QUERY_LENGTH} chars)"
    
    if len(query.strip()) == 0:
        return False, "Query cannot be whitespace only"
    
    return True, ""
```

**Path Validation:**
- Maximum path length: 1024 characters
- Maximum file size: 50MB
- Maximum query length: 1000 characters

### 4. SQL Injection Prevention

**Implementation:** Parameterized queries

```python
# Vulnerable (avoid):
cursor.execute(f"SELECT * FROM documents WHERE filepath = '{filepath}'")

# Secure:
cursor.execute("SELECT id FROM documents WHERE filepath = ?", (filepath,))
```

### 5. Error Handling

**Security Principles:**
- Never crash on error (no `sys.exit(1)`)
- Log errors without exposing sensitive details
- Return empty results on failure

```python
def search(self, query: str, top_k: int = 5) -> List[Dict]:
    """Search with proper error handling."""
    try:
        # Validate query
        valid, msg = self.config.validate_query(query)
        if not valid:
            logger.warning(f"Invalid query: {msg}")
            return []  # Return empty, don't crash
        
        # ... search logic ...
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return []  # Graceful degradation
```

---

## Secure Coding Practices

### 1. Never Trust User Input

**Bad:**
```python
filepath = request.args['path']
with open(filepath) as f:  # VULNERABLE
    content = f.read()
```

**Good:**
```python
filepath = request.args['path']
safe_path = sanitize_path(filepath)
if safe_path is None:
    raise ValueError("Invalid path")
with open(safe_path) as f:
    content = f.read()
```

### 2. Use Parameterized Queries

**Bad:**
```python
query = f"SELECT * FROM documents WHERE content LIKE '%{user_query}%'"
cursor.execute(query)  # SQL INJECTION VULNERABLE
```

**Good:**
```python
query = "SELECT * FROM documents WHERE content LIKE ?"
cursor.execute(query, (f"%{user_query}%",))
```

### 3. Validate All Paths

**Bad:**
```python
filepath = user_input  # Direct use of user input
with open(filepath) as f:  # VULNERABLE
    pass
```

**Good:**
```python
filepath = sanitize_path(user_input)
if filepath is None:
    raise ValueError("Invalid path")
with open(filepath) as f:
    pass
```

### 4. Implement Proper Error Handling

**Bad:**
```python
try:
    risky_operation()
except Exception:
    sys.exit(1)  # CRASHES APPLICATION
```

**Good:**
```python
try:
    risky_operation()
except Exception as e:
    logger.error(f"Operation failed: {e}")
    return []  # Graceful degradation
```

---

## Security Testing

### Unit Tests

Run the comprehensive test suite:

```bash
# Run all tests
python3 test_fmem_comprehensive.py

# Run specific test class
python3 -m unittest test_fmem_comprehensive.TestSecurity

# Run with verbose output
python3 test_fmem_comprehensive.py -v
```

### Security Test Cases

| Test | Description | Command |
|------|-------------|---------|
| Path Traversal | Tests `../` attacks | `test_sanitize_path_traversal()` |
| Null Byte Injection | Tests `\x00` attacks | `test_sanitize_null_bytes()` |
| Invalid Extension | Tests blocklisted extensions | `test_invalid_extension()` |
| Empty Content | Tests empty file handling | `test_empty_content()` |
| SQL Injection | Tests parameterized queries | `test_store_document()` |

### Manual Security Testing

```bash
# Test path traversal protection
python3 -c "
from fmem import MemoryRetrieval
mr = MemoryRetrieval()

# This should fail gracefully
result = mr.add_document('../../../etc/passwd')
print(f'Result: {result}')  # Should be False
"

# Test invalid extension
python3 -c "
from fmem import MemoryRetrieval
mr = MemoryRetrieval()

# This should fail gracefully
result = mr.add_document('/tmp/test.exe')
print(f'Result: {result}')  # Should be False
"
```

---

## Incident Response

### Security Incident Types

| Incident | Response |
|----------|----------|
| Path Traversal Attempt | Log event, block request, notify admin |
| SQL Injection Attempt | Log event, block request, audit database |
| DoS Attack | Rate limit, increase monitoring, consider WAF |
| Unauthorized Access | Block IP, rotate credentials, audit logs |

### Logging Requirements

**Security-relevant events that must be logged:**
- Path traversal attempts
- Invalid file extensions
- Query validation failures
- Database errors
- Ollama connection failures

### Audit Trail

```bash
# Check logs for security events
grep -E "(traversal|injection|invalid)" ~/.openclaw/memory/*.log

# Monitor access patterns
grep "Search" ~/.openclaw/memory/*.log | tail -100

# Review failed operations
grep -E "(Failed|Error|Warning)" ~/.openclaw/memory/*.log | tail -50
```

---

## Security Best Practices

### For Developers

1. **Always validate user input**
2. **Never use string concatenation for SQL queries**
3. **Always use `sanitize_path()` for file operations**
4. **Log security-relevant events**
5. **Handle errors gracefully**

### For Operators

1. **Keep dependencies updated**
2. **Monitor logs for security events**
3. **Regularly review access patterns**
4. **Backup data regularly**
5. **Test security controls periodically**

---

## Compliance

### OWASP Top 10 Alignment

| OWASP Category | Addressed | Details |
|----------------|-----------|---------|
| A01:2021 Broken Access Control | ✅ | Path traversal protection |
| A03:2021 Injection | ✅ | SQL injection prevention |
| A05:2021 Security Misconfiguration | ✅ | Configurable settings |
| A06:2021 Vulnerable Components | ✅ | Dependency management |
| A07:2021 IDOR | ✅ | Path validation |
| A09:2021 Security Logging | ✅ | Comprehensive logging |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0.0 | 2026-02-14 | Initial production security release |
| 1.0.0 | 2026-02-12 | Initial release (no security features) |

---

## Contact

For security issues, contact the development team.
Do not disclose security issues publicly.

---

**Last Updated:** 2026-02-14
