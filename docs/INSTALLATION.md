# Installation

Complete installation guide for fmem - the privacy-first memory system for AI conversations.

---

## Prerequisites

Before installing fmem, ensure you have:

| Requirement | Minimum Version | Notes |
|-------------|---------------|-------|
| Python | 3.9+ | 3.10+ recommended |
| Ollama | Latest | Required for local embeddings |
| pip | Latest | For package installation |
| ~500MB disk | - | For index and dependencies |

---

## Step 1: Install Ollama

fmem uses Ollama for local embeddings. No external API calls needed.

### On Linux/macOS
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### On Raspberry Pi (ARM64)
```bash
curl -fsSL https://ollama.com/install.sh | sh
# Note: First run may take 5-10 minutes on ARM64
```

### Verify Installation
```bash
ollama --version
```

---

## Step 2: Pull Embedding Model

fmem uses `nomic-embed-text` for semantic search:

```bash
ollama pull nomic-embed-text
```

This downloads a 768-dimensional embedding model optimized for semantic similarity.

---

## Step 3: Install fmem

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
pip install faiss-cpu numpy litellm
```

---

## Step 4: Create Configuration

Create the configuration file at `~/.openclaw/memory/fmem.conf`:

```bash
mkdir -p ~/.openclaw/memory
```

Create the config file:
```ini
[settings]
data_dir = ~/.openclaw/memory
ollama_url = http://localhost:11434

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

## Step 5: Verify First Run

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
  Ollama URL: http://localhost:11434
```

---

## Step 6: Index Your First Documents

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

### "Ollama not running" Error
```bash
# Start Ollama service
ollama serve

# Or check if running
curl http://localhost:11434/api/tags
```

### Port Already in Use
If port 11434 is already in use:
```bash
# Find and kill existing process
lsof -ti:11434 | xargs kill -9

# Or use different port
export FMEM_OLLAMA_URL="http://localhost:11435"
```

### Permission Denied on Config
```bash
# Ensure proper permissions
chmod 644 ~/.openclaw/memory/fmem.conf
```

### "No module named 'faiss'"
```bash
# Install FAISS CPU version
pip install faiss-cpu --break-system-packages --user

# On ARM64 (Raspberry Pi):
pip install faiss-cpu numpy --index-url https://piwheels.org/simple
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
- Ollama model downloads on first use
- Subsequent runs are much faster
- Consider indexing in batches for large directories

---

## Environment Variables

Override config file settings with environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `FMEM_DATA_DIR` | Storage directory | `~/.openclaw/memory` |
| `OLLAMA_HOST` | Ollama API URL | `http://localhost:11434` |
| `FMEM_CONFIG` | Config file path | `~/.openclaw/memory/fmem.conf` |
| `FMEM_DEBUG` | Enable debug logging | `false` |

---

## Next Steps

- Read the [API documentation](./API.md) for programmatic usage
- Check [Examples](./EXAMPLES.md) for common workflows
- Review [Architecture](./ARCHITECTURE.md) for implementation details
