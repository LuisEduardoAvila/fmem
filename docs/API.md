# API Reference

## MemoryRetrieval

Main class for memory search operations.

### `__init__(index_dir=None, db_path=None, model="nomic-embed-text")`

Initialize memory retrieval.

**Parameters:**
- `index_dir` — Directory for FAISS index (default: `~/.fmem`)
- `db_path` — SQLite database path
- `model` — Ollama model for embeddings

### `search(query, top_k=5, filters=None)`

Search for relevant memory chunks.

**Parameters:**
- `query` — Search query string
- `top_k` — Number of results (default: 5)
- `filters` — Optional path filters

**Returns:**
List of dicts with `score`, `content`, `source`, `modified_time`

### `index_file(filepath)`

Index a single markdown file.

### `index_directory(dirpath, extensions=[".md"])`

Index all files in directory.

---

## Utility Functions

### `chunk_markdown(text, min_size=100)`

Split markdown by `##` headings.

### `auto_recall(query_text, system=None, top_k=3)`

Auto-search with formatted results for agents.
