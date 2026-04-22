# Installation

Complete installation guide for fmem — the privacy-first memory system for AI conversations.

---

## Prerequisites

Before installing fmem, ensure you have:

| Requirement | Minimum Version | Notes |
|-------------|---------------|-------|
| Python | 3.8+ | 3.10+ recommended |
| pip | Latest | For package installation |
| ~500MB disk | — | For index and dependencies |
| Ollama **or** FastEmbed | — | For local embeddings (all-MiniLM-L6-v2) |

**Embedding backends:** fmem supports two local embedding backends — no cloud services required:

- **FastEmbed** (default) — pure Python, no extra daemon. Install via `pip install fastembed`.
- **Ollama** — if you already run Ollama, fmem can use it for embeddings. Ensure the `nomic-embed-text` (or compatible) model is pulled.

**For the OpenClaw plugin** (optional):

| Requirement | Minimum Version | Notes |
|-------------|---------------|-------|
| OpenClaw | 2026.4.15+ | Plugin SDK support |
| Node.js | 18+ | For `npm install` in plugin directory |

---

## Step 1: Install Dependencies

fmem requires Python and standard ML libraries. No external embedding service needed if using FastEmbed.

### Required Packages

```bash
pip install faiss-cpu fastembed numpy --break-system-packages --user
```

On ARM64 (Raspberry Pi):
```bash
pip install faiss-cpu numpy --index-url https://piwheels.org/simple
pip install fastembed --break-system-packages --user
```

### (Optional) Ollama as Embedding Backend

If you prefer Ollama over FastEmbed:

```bash
# Install Ollama (see https://ollama.com)
curl -fsSL https://ollama.com/install.sh | sh

# Pull an embedding model
ollama pull nomic-embed-text
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

## Step 6: Install the OpenClaw Plugin (Optional)

fmem ships with an OpenClaw plugin (`fmem-auto`) that automatically injects relevant memory context into your AI conversations. When installed, every message you send to your OpenClaw agent will be enriched with semantically similar chunks from your fmem index — no manual retrieval needed.

### 6.1 Locate the Plugin

The plugin lives in the fmem repository at:

```
plugins/openclaw-fmem-auto/
```

If you installed from source, you already have it. If you installed via pip, clone the repo to get the plugin directory:

```bash
git clone https://github.com/LuisEduardoAvila/fmem.git /opt/fmem
```

### 6.2 Install Plugin Dependencies

```bash
cd /opt/fmem/plugins/openclaw-fmem-auto
npm install
```

This pulls in `@openclaw/plugin-sdk` and any other runtime dependencies.

### 6.3 Add to OpenClaw Configuration

Edit your OpenClaw config file (typically `~/.openclaw/config.yaml`) and add the plugin:

```yaml
plugins:
  load:
    paths:
      - /opt/fmem/plugins          # Directory containing openclaw-fmem-auto/
  entries:
    fmem-auto:
      enabled: true
      topK: 3              # Number of memory chunks to inject
      minScore: 0.25       # Minimum similarity score (0–1)
      timeoutMs: 5000      # Timeout for fmem lookup (ms)
```

**Key settings:**

| Setting | Default | Description |
|---------|---------|-------------|
| `topK` | `3` | How many top-scoring chunks to inject into context |
| `minScore` | `0.25` | Similarity threshold — chunks below this are ignored |
| `timeoutMs` | `5000` | Max wait time for fmem query before falling back silently |

### 6.4 Restart OpenClaw

```bash
openclaw gateway restart
```

### 6.5 Verify the Plugin

Check that the plugin loaded:

```bash
openclaw gateway status
```

You should see `fmem-auto` listed in the loaded plugins. Send a message to your agent — if fmem has indexed documents, the plugin will silently enrich your prompt with relevant memory.

---

## Troubleshooting

### `fmem: command not found`

The `fmem` CLI isn't on your `PATH`. This usually means pip installed to a user-local bin that isn't sourced.

```bash
# Check where pip installed it
pip show fmem | grep Location

# Common fix: add pip user bin to PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Or run directly
python -m fmem.cli status
```

### `No module named 'faiss'`

```bash
# Install FAISS CPU version
pip install faiss-cpu --break-system-packages --user

# On ARM64 (Raspberry Pi):
pip install faiss-cpu numpy --index-url https://piwheels.org/simple
```

### `No module named 'fastembed'`

```bash
# Install FastEmbed
pip install fastembed --break-system-packages --user
```

### Ollama Not Running / Connection Refused

If you configured fmem to use Ollama for embeddings and it can't connect:

```bash
# Check Ollama is running
ollama list

# Start it if needed
ollama serve &

# Verify the embedding model is available
ollama list | grep nomic-embed-text

# Pull it if missing
ollama pull nomic-embed-text
```

fmem will fall back to FastEmbed if Ollama is unavailable and FastEmbed is installed.

### Index Directory Not Found

Ensure the paths in `additional_dirs` exist:

```bash
# Check if directory exists
ls -la ~/Documents/notes

# Create if needed
mkdir -p ~/Documents/notes
```

### Slow Indexing on First Run

- FastEmbed downloads the embedding model on first use (~90MB)
- Subsequent runs are much faster
- Consider indexing in batches for large directories

### OpenClaw Plugin Not Loading

```bash
# Verify Node.js is available (18+ required)
node --version

# Reinstall plugin dependencies
cd /opt/fmem/plugins/openclaw-fmem-auto
rm -rf node_modules package-lock.json
npm install

# Check the plugin path in config matches actual location
ls -la /opt/fmem/plugins/openclaw-fmem-auto/package.json

# Restart OpenClaw and check logs
openclaw gateway restart
openclaw gateway status
```

If the plugin still doesn't appear, check OpenClaw's gateway logs for errors. Common causes:

- **Wrong path:** The `paths` entry must point to the *parent* directory of `openclaw-fmem-auto/`
- **Missing `npm install`:** The plugin won't load without `node_modules`
- **OpenClaw version too old:** Requires 2026.4.15+ for plugin SDK support

---

## Environment Variables

Override config file settings with environment variables:

| Variable | Description | Default |
|----------|-------------|--------|
| `FMEM_DATA_DIR` | Storage directory | `~/.openclaw/memory` |
| `FMEM_CONFIG` | Config file path | `~/.openclaw/memory/fmem.conf` |
| `FMEM_DEBUG` | Enable debug logging | `false` |

---

## Next Steps

- Read the [API documentation](./API.md) for programmatic usage
- Check [Examples](./EXAMPLES.md) for common workflows
- Review [Architecture](./ARCHITECTURE.md) for implementation details