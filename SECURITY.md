# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 3.0.0   | :white_check_mark: |
| 2.x.x   | :x:                |
| 1.x.x   | :x:                |

## Security Features

fmem implements multiple layers of security to protect your data:

### Path Traversal Protection
- Sanitizes all file paths to prevent `../` attacks
- Validates paths are within allowed base directories
- Rejects absolute paths without explicit base directory

### Input Validation
- Query length limited to 1000 characters
- File extension whitelist (`.md`, `.txt`, `.py`, `.json`, `.yaml`, `.csv`)
- File size limit: 50MB
- Path length limit: 1024 characters

### SQL Injection Prevention
- Uses parameterized queries for all database operations
- Prepared statements for SQLite operations

### File Safety
- Validates file extensions against whitelist
- Checks file size before processing
- Handles encoding errors gracefully (UTF-8, latin-1 fallback)
- Secure file reading with proper error handling

## Reporting a Vulnerability

If you discover a security vulnerability:

1. **Do NOT open a public issue**
2. Email details to: luiseduardo.avila@gmail.com
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

We will respond within 48 hours and work to resolve the issue promptly.

## Security Audit

This project has been audited for:
- [x] Path traversal vulnerabilities
- [x] SQL injection vulnerabilities  
- [x] Input validation issues
- [x] Error handling problems
- [x] Security logging

Last audit: 2026-02-14
