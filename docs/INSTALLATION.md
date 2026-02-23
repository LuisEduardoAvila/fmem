# Installation

Complete installation guide for fmem - the privacy-first memory system for AI conversations.

---

## Prerequisites

Before installing fmem, ensure you have:

| Requirement | Minimum Version | Notes |
|-------------|---------------|-------|
| Python | 3.9+ | 3.10+ recommended |
| pip | Latest | For package installation |
| ~500MB disk | - | For index and dependencies |

**Note:** fmem uses **FastEmbed** for local embeddings - no external services required.

---

## Step 1: Install Dependencies

fmem requires Python and standard ML libraries. No external embedding service needed.

### Required Packages

```bash
pip install faiss-cpu fastembed numpy --break-system-packages --user
```

On ARM64 (Raspberry Pi):
```bash
pip install faiss-cpu numpy --index-url https://piwheels.org/simple
pip install fastembed --break-system-packages --user
```

---

## Step 2: Install fmem

### Option A: Install from PyPI (Recommended)
```bash
pip install fmem
```

### Option B: Install from Source
```bash
# Clone the repository
git clone https://github.com/LuisEduardoAvila/fmem.git
cd fmem

# Install in development mode
pip install -e . --break-system-packages --user
```

### Option C: Install with Dependencies Manually
```bash
pip install faiss-cpu fastembed numpy
```

---

## Step 3: Create Configuration

Create the configuration file at `~/.openclaw/memory/fmem.conf`:

```bash
mkdir -p ~/.openclaw/memory
```

Create the config file:
```ini
[settings]
data_dir = ~/.openclaw/memory

# Directories to index (comma-separated)
additional_dirs = ~/Documents/notes, ~/projects

# Directories to exclude (comma-separated)
exclude_dirs = .git, __pycache__, node_modules, .venv

# Specific files to index (comma-separated paths)
index_files = ~/README.md, ~/todo.txt

# File extensions to index (narrows default: .md, .txt, .py, .json, .yaml, .yml, .csv)
extensions = .md, .txt, .py

# Index memory files (daily logs)
index_memory_md = true
index_daily_files = true

# Ranking settings
enable_recency_ranking = true
recency_weight = 0.3
enable_location_ranking = true
location_weight = 0.2
```

**Note:** The `extensions` config narrows the code defaults `.md, .txt, .py, .json, .yaml, .yml, .csv`. Only specify extensions you want to keep.

---

## Step 4: Verify First Run

### Check System Status
```bash
fmem status
```

Expected output:
```
fmem Index Status
========================================
Documents indexed: 0
Chunks indexed: 0

Configuration:
  Data directory: /home/user/.openclaw/memory
  Embedding: FastEmbed (local)
```

---

## Step 5: Index Your First Documents

### Auto-index configured directories
```bash
fmem index
```

### Index a specific directory
```bash
fmem index /path/to/documents
```

### Index a single file
```bash
fmem index /path/to/file.md
```

---

## Troubleshooting

### "No module named 'faiss'"
```bash
# Install FAISS CPU version
pip install faiss-cpu --break-system-packages --user

# On ARM64 (Raspberry Pi):
pip install faiss-cpu numpy --index-url https://piwheels.org/simple
```

### "No module named 'fastembed'"
```bash
# Install FastEmbed
pip install fastembed --break-system-packages --user
```

### Index Directory Not Found
Ensure the paths in `additional_dirs` exist:
```bash
# Check if directory exists
ls -la ~/Documents/notes

# Create if needed
mkdir -p ~/Documents/notes
```

### Slow Indexing on First Run
- FastEmbed downloads embedding model on first use
- Subsequent runs are much faster
- Consider indexing in batches for large directories

---

## Environment Variables

Override config file settings with environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `FMEM_DATA_DIR` | Storage directory | `~/.openclaw/memory` |
| `FMEM_CONFIG` | Config file path | `~/.openclaw/memory/fmem.conf` |
| `FMEM_DEBUG` | Enable debug logging | `false` |

---

## Next Steps

- Read the [API documentation](./API.md) for programmatic usage
- Check [Examples](./EXAMPLES.md) for common workflows
- Review [Architecture](./ARCHITECTURE.md) for implementation details
