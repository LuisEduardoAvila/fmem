# SCANNER.md - Memory File Scanner Documentation

## Purpose

The `scanner.py` utility scans specified directories and indexes files into the FAISS-based memory system. It respects a time-gate (default 30 minutes) to prevent re-indexing fresh content.

## Usage

### Manual Scan

```bash
# Full scan from configuration
python3 scanner.py

# Scan specific directory
python3 scanner.py /path/to/directory
```

### Automated Scan (Cron)

The scanner runs automatically via cron job (typically every 2-4 hours).
Configuration in `memory-scan-config.md`.
