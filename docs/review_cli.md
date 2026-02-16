# fmem CLI Review Report

**Review Date:** 2026-02-16  
**CLI Version:** Documented in code (no --version flag)  
**Source:** `src/fmem/cli.py`

---

## Executive Summary

The fmem CLI provides three core commands (`index`, `search`, `status`) with a clean argument structure. The implementation follows argparse conventions and supports both interactive indexing (directory/file arguments) and configuration-driven auto-indexing. However, there are significant documentation gaps between the actual CLI implementation and what ARCHITECTURE.md describes.

---

## Part 1: Complete CLI Command Reference

### Command Structure

```
fmem <command> [options]
```

### Available Commands

| Command | Description | Handler Function |
|---------|-------------|------------------|
| `index` | Index a directory or auto-index configured directories | `cmd_index()` |
| `search` | Search memory with semantic ranking | `cmd_search()` |
| `status` | Show index status and configuration | `cmd_status()` |

### Detailed Command Documentation

#### `index` Command

**Purpose:** Index documents into the fmem memory system

**Usage:**
```bash
# Index a specific directory
fmem index /path/to/directory

# Index a specific file
fmem index /path/to/file.md

# Auto-index all configured directories (from fmem.conf)
fmem index
```

**Arguments:**
| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `directory` | path | No | Directory or file to index. If omitted, uses auto-index mode from config. |

**Auto-Index Behavior (Trigger Conditions):**

1. **Manual Trigger:** User explicitly runs `fmem index` without arguments
2. **Configuration Used:** Reads `additional_dirs`, `exclude_dirs`, and `index_files` from `~/.openclaw/memory/fmem.conf`
3. **Output:**
   - Lists directories being indexed
   - Shows excluded directories being skipped
   - Displays file types being indexed (from `VALID_EXTENSIONS`)
   - Reports individual file indexing results
   - Provides total file count summary

**Auto-Index Implementation Details:**
```python
# From cmd_index() - auto-index mode when no directory provided
directories = config.additional_dirs.split(',')  # Comma-separated list
exclude_dirs = config.exclude_dirs.split(',')    # Comma-separated exclusions
index_files = config.index_files.split(',')      # Specific files
```

**Output Example (Auto-Index):**
```
Indexing 4 configured directories...
File types: .md, .txt
Excluding: venv, env, .venv, node_modules, __pycache__, ...

📁 Indexing /home/luis/.openclaw/workspace/memory/...
   ✓ Indexed 15 files

📁 Indexing /home/luis/.openclaw/workspace/notes/...
   ✓ Indexed 8 files

📄 Indexing 2 specific files...
   Indexing /home/luis/.openclaw/workspace/projects/fmem/README.md...
   ✓ Indexed 12 chunks from /home/luis/.openclaw/workspace/projects/fmem/README.md
   ...

✅ Total indexed 25 files across all configured directories
```

---

#### `search` Command

**Purpose:** Search the indexed memory using semantic similarity

**Usage:**
```bash
fmem search "your query here"
fmem search "your query here" -k 10
fmem search "your query here" --top-k 3
```

**Arguments:**
| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `query` | string | Yes | - | Search query text |
| `-k, --top-k` | int | No | 5 | Number of results to return |

**Output Format:**
```
1. Score: 0.845
   Source: /path/to/file.md#section-heading
   Content preview (first 200 chars)...

2. Score: 0.823
   Source: /path/to/other.md#section-heading
   Content preview...
```

**Implementation Details:**
- Calls `memory.search(query, top_k=args.top_k)` from fmem core
- Results returned as list of dicts with keys: `score`, `source`/`filepath`, `content`/`chunk`
- Preview truncated to 200 characters with "..." suffix

---

#### `status` Command

**Purpose:** Display current index statistics and configuration

**Usage:**
```bash
fmem status
```

**Arguments:** None

**Output Format:**
```
fmem Index Status
========================================
Documents indexed: 42
Chunks indexed: 128

Configuration:
  Data directory: /home/luis/.openclaw/memory/
  Ollama URL: http://localhost:11434
```

**Implementation Details:**
- Uses `memory.get_document_count()` and `memory.get_chunk_count()`
- Displays `config.data_dir` and `config.ollama_url`

---

### Subcommands Structure

```
fmem
├── index
│   └── [directory: optional path] → handles both files and directories
├── search
│   ├── query (required string)
│   └── -k/--top-k (optional int, default=5)
└── status
    └── (no arguments)
```

---

## Part 2: Configuration Options Used by CLI

### Config File Location
**Primary:** `~/.openclaw/memory/fmem.conf`

### Config Sections Accessed by CLI

#### `[settings]` Section

**Directly Used Properties:**

| Config Key | Used In | Purpose |
|------------|---------|---------|
| `additional_dirs` | `cmd_index()` (auto-index) | List of directories to auto-index |
| `exclude_dirs` | `cmd_index()` (auto-index) | Directories to skip |
| `index_files` | `cmd_index()` (auto-index) | Specific files to index (e.g., READMEs) |

**Note:** The CLI implementation uses attribute access with `hasattr()` checks:
```python
# From cli.py
if hasattr(config, 'additional_dirs') and config.additional_dirs:
    directories = [d.strip() for d in config.additional_dirs.split(',')]
```

### Config Options NOT Used by CLI (but defined in fmem.conf)

| Config Option | Used By | CLI Relevance |
|---------------|---------|---------------|
| `data_dir` | Core `fmem.py` only | CLI displays it in `status` via `memory.config` |
| `ollama_url` | Core `fmem.py` only | CLI displays it in `status` |
| `index_name` | Core only | Not CLI-relevant |
| `metadata_name` | Core only | Not CLI-relevant |
| `sqlite_name` | Core only | Not CLI-relevant |
| `enable_location_ranking` | Core only | Not CLI-relevant |
| `location_weight` | Core only | Not CLI-relevant |
| `enable_recency_ranking` | Core only | Not CLI-relevant |
| `recency_weight` | Core only | Not CLI-relevant |
| `recency_threshold_days` | Core only | Not CLI-relevant |
| `min_recency_score` | Core only | Not CLI-relevant |
| `*weight` (location weights) | Core only | Not CLI-relevant |
| `ollama_timeout` | Core only | Not CLI-relevant |
| `max_retries` | Core only | Not CLI-relevant |
| `debug` | Core only | Not CLI-relevant |
| `max_file_size` | Core only | Not CLI-relevant |
| `max_query_length` | Core only | Not CLI-relevant |
| `max_path_length` | Core only | Not CLI-relevant |
| `extensions` | Core only | CLI uses `config.VALID_EXTENSIONS` instead |

### Important Discovery: `VALID_EXTENSIONS` vs `extensions`

**Inconsistency:** The CLI references `config.VALID_EXTENSIONS`:
```python
print(f"File types: {', '.join(config.VALID_EXTENSIONS)}")
```

But the config file uses `extensions` (lowercase, comma-separated string).

**Likely Issue:** The actual fmem.Config class maps `extensions` → `VALID_EXTENSIONS` as a property.

---

## Part 3: Help Text Accuracy Review

### Current Help Output

```bash
$ fmem --help
usage: fmem [-h] {index,search,status} ...

fmem - FAISS-based Memory Search for OpenClaw

positional arguments:
  {index,search,status}
                        Available commands
    index               Index a directory
    search              Search memory
    status              Show index status

options:
  -h, --help            show this help message and exit

$ fmem index --help
usage: fmem index [-h] [directory]

positional arguments:
  directory   Directory to index (optional - auto-indexes all configured directories)

$ fmem search --help
usage: fmem search [-h] [-k TOP_K] query

positional arguments:
  query       Search query

options:
  -h, --help  show this help message and exit
  -k, --top-k  Number of results (default: 5)

$ fmem status --help
usage: fmem status [-h]

options:
  -h, --help  show this help message and exit
```

### Help Text Issues

| Issue | Severity | Description |
|-------|----------|-------------|
| `index --help` doesn't mention file support | Medium | Can index single files, but help only mentions "Directory" |
| `status --help` missing description | Low | No description of what status shows |
| Missing `--version` flag | Low | No way to check installed version |
| No config file path in help | Low | Users don't know where config is located |

### Recommended Help Text Changes

**`index` command help:**
```python
# Current
index_parser.add_parser("index", help="Index a directory")
index_parser.add_argument("directory", nargs="?", help="Directory to index (optional - auto-indexes all configured directories)")

# Recommended
index_parser.add_parser("index", help="Index a directory or specific file")
index_parser.add_argument("path", nargs="?", help="Directory or file to index (optional - auto-indexes all configured directories from fmem.conf)")
```

---

## Part 4: Documentation Gaps

### Critical Gaps

#### Gap 1: README.md Missing CLI Examples

**Current State:** README.md has NO CLI usage examples.

**Expected:** The README should document:
- How to install the CLI (`pip install -e .` assumed)
- Basic usage examples for all three commands
- Configuration file location
- Auto-index behavior

**Suggested Addition:**
```markdown
## CLI Usage

### Installation
```bash
cd projects/fmem
pip install -e .
```

### Commands

#### Index
```bash
# Index a specific directory
fmem index /path/to/docs

# Index a specific file
fmem index /path/to/README.md

# Auto-index all configured directories (see ~/.openclaw/memory/fmem.conf)
fmem index
```

#### Search
```bash
# Search with default 5 results
fmem search "machine learning"

# Search with more results
fmem search "pytorch tutorial" -k 10
```

#### Status
```bash
# Check index status
fmem status
```

### Configuration

Edit `~/.openclaw/memory/fmem.conf` to customize:
- `additional_dirs`: Directories to auto-index
- `exclude_dirs`: Directories to skip
- `index_files`: Specific files to index (e.g., project READMEs)
```

---

#### Gap 2: ARCHITECTURE.md CLI Reference Mismatch

**Current Issue:** ARCHITECTURE.md states CLI has commands: `search`, `add`, `status`, `reset`

**Actual CLI:** Commands are: `index`, `search`, `status`

**The mismatch:**
- `add` command does NOT exist (replaced by `index`)
- `reset` command does NOT exist (only in core API via `memory.reset()`)

**Fix Required:** Update ARCHITECTURE.md to reflect actual CLI commands.

---

#### Gap 3: Missing `index_files` Documentation

**Feature:** The `index_files` config option allows indexing specific files (like project READMEs) that live outside the `additional_dirs`.

**Current Behavior:** Working in code, but NOT documented anywhere.

**Location in Code:**
```python
# cli.py, cmd_index()
if hasattr(config, 'index_files') and config.index_files:
    files = [f.strip() for f in config.index_files.split(',') if f.strip()]
```

**Needs Documentation in:**
- README.md
- fmem.conf comments (already has it ✅)
- ARCHITECTURE.md

---

#### Gap 4: No Documentation of Auto-Index Trigger Conditions

**Current:** It's unclear what triggers auto-index vs single-file indexing.

**Clarification needed:**
- Auto-index triggers when `fmem index` is called without arguments
- Uses `additional_dirs`, `exclude_dirs`, `index_files` from config
- Single-file/directory indexing bypasses config

---

## Part 5: Architecture Documentation Issues

### Section: CLI Integration

**Current (misleading):**
> Direct Python API access via `fmem.cli` module:
> - Commands: `search`, `add`, `status`, `reset`
> - Arguments: Parsed with argparse
> - Output: Formatted text or JSON

**Should Be:**
> Direct Python API access via `fmem.cli` module:
> - Commands: `index`, `search`, `status`
> - Arguments: Parsed with argparse
> - Output: Formatted text
> - Note: For `reset` functionality, use the Python API (`memory.reset()`)

### Section: Data Flow - CLI Integration

The ASCII diagram under "CLI Integration" is actually for OpenClaw Integration, not CLI. This appears to be a copy-paste error.

**Fix:** Either remove or create a proper diagram showing:
```
fmem index → cmd_index() → memory.index_directory() / memory.index_file()
fmem search → cmd_search() → memory.search()
fmem status → cmd_status() → memory.get_document_count() / get_chunk_count()
```

---

## Part 6: README Suggestions

### S1: Add CLI Quick Start Section

Add to README.md after Installation section:

```markdown
## Quick Start

```bash
# 1. Create config
cp config/fmem.conf.template ~/.openclaw/memory/fmem.conf

# 2. Customize directories to index
# Edit ~/.openclaw/memory/fmem.conf and set:
# additional_dirs = /path/to/your/docs

# 3. Index your content
fmem index

# 4. Test a search
fmem search "your first query"
```
```

### S2: Document Configuration Options

Add section explaining config options relevant to CLI:

```markdown
### CLI Configuration

The CLI is configured via `~/.openclaw/memory/fmem.conf`:

| Option | CLI Impact |
|--------|------------|
| `additional_dirs` | Directories auto-indexed when running `fmem index` without arguments |
| `exclude_dirs` | Directories skipped during auto-index |
| `index_files` | Specific files indexed in addition to directories (e.g., project READMEs) |
| `extensions` | File types the indexer will process |
```

### S3: Add CLI Examples to Integration Section

In the "Integration Options" section, after Option 1, add CLI as a standalone option:

```markdown
### Option: Direct CLI Usage

For command-line access without OpenClaw integration:

**Commands:**
- `fmem index [path]` - Index directory or file
- `fmem search <query>` - Search indexed content
- `fmem status` - View index statistics
```

---

## Part 7: Summary of Issues Found

| # | Issue | Location | Priority |
|---|-------|----------|----------|
| 1 | README has no CLI examples | `README.md` | **High** |
| 2 | ARCHITECTURE lists wrong commands | `docs/ARCHITECTURE.md` | **High** |
| 3 | ARCHITECTURE CLI diagram is wrong | `docs/ARCHITECTURE.md` | Medium |
| 4 | `index_files` feature undocumented | README.md, ARCHITECTURE.md | Medium |
| 5 | Auto-index trigger not documented | README.md | Medium |
| 6 | Help text for `index` says "directory" only | `src/fmem/cli.py` | Low |
| 7 | Missing `--version` flag | `src/fmem/cli.py` | Low |

---

## Part 8: Code Quality Notes

### Positive Observations

1. **Security:** `index` command validates paths using `Path(directory).resolve()` and checks existence
2. **Error Handling:** All commands have try/except blocks with informative messages
3. **Help Text:** Basic argparse help is present and functional
4. **Auto-index Logic:** Well-structured with clear separation between single-directory and auto-index modes

### Areas for Improvement

1. **Argument Naming:** `directory` argument can be file or directory, rename to `path`
2. **Consistency:** Help text should mention files are supported in `index` command
3. **Feature Completeness:** Consider adding `--version` flag
4. **Documentation:** The cli.py module docstring says "Simple CLI" - could be expanded

---

## Appendix: Configuration File Reference

### Full Config Example for CLI Usage

```ini
[settings]
# Core
ollama_url = http://localhost:11434
data_dir = ~/.openclaw/memory/

# Indexing (used by CLI auto-index)
additional_dirs = /home/user/docs,/home/user/projects/notes
exclude_dirs = venv,node_modules,__pycache__,.git
index_files = /home/user/projects/fmem/README.md,/home/user/projects/other/README.md

# File types
extensions = .md,.txt

# Ranking (used by CLI indirectly via search)
enable_location_ranking = true
location_weight = 0.2
enable_recency_ranking = true
recency_weight = 0.3
```

### Current Config in Use

**File:** `~/.openclaw/memory/fmem.conf`

Key CLI-relevant settings (as of 2026-02-16):
- `additional_dirs`: 4 directories configured (memory, notes, decisions, docs)
- `exclude_dirs`: 13 patterns (venv, node_modules, cache directories)
- `index_files`: 2 files configured (fmem, epm-dashboard READMEs)
- `extensions`: `.md, .txt` only

---

*Report generated by CLI Review task*
