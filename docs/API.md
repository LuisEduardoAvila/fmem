# API Reference

Complete reference for the fmem Python API.

---

## MemoryRetrieval

Main class for memory search operations.

### `__init__(db_path=None, config=None, ollama_client=None)`

Initialize memory retrieval system.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `db_path` | `str` | `None` | SQLite database path. Uses config default if None. |
| `config` | `ConfigManager` | `None` | ConfigManager instance. Uses global CONFIG if None. |
| `ollama_client` | `OllamaClient` | `None` | Ollama client for embeddings. Auto-created if None. |

**Returns:**
`MemoryRetrieval` instance

**Example:**
```python
from fmem import MemoryRetrieval

# Using default config
memory = MemoryRetrieval()

# With custom database path
memory = MemoryRetrieval(db_path="/custom/path/memory.db")
```

---

### `search(query, top_k=5, chunk_mode="chunk")`

Search for relevant memory chunks.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | `str` | Required | Search query string (max 1000 chars) |
| `top_k` | `int` | `5` | Number of results to return |
| `chunk_mode` | `str` | `"chunk"` | Result format: `"chunk"`, `"document"`, or `"hybrid"` |

**Returns:**
`List[Dict]` with keys:
- `score` (float): Similarity score (0.0-1.0)
- `filepath` (str): Source file path
- `content` (str): Full content or chunk
- `source` (str): Formatted source reference
- `modified_time` (int): File modification timestamp
- `chunk_id` (str, optional): Chunk identifier
- `chunk_info` (dict, optional): Additional chunk metadata

**Example:**
```python
results = memory.search("my favorite movies", top_k=5)

for result in results:
    print(f"[{result['score']:.3f}] {result['filepath']}")
    print(result['content'][:200])
```

**Note:** Results are ranked using multi-factor scoring: semantic (50%), recency (30%), location (20%).

---

### `add_document(filepath, content=None, chunk_by_sections=True)`

Index a single document with validation.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `filepath` | `str` | Required | Path to file |
| `content` | `str` | `None` | File content. If None, reads from disk. |
| `chunk_by_sections` | `bool` | `True` | Split markdown by ## headings |

**Returns:**
`bool` - True if successful, False otherwise

**Example:**
```python
# Index a single file
success = memory.add_document("/path/to/notes.md")

# With explicit content
content = "## My Notes\n\nImportant information here."
success = memory.add_document("notes.md", content=content)

# Index without chunking (as single document)
success = memory.add_document("file.txt", chunk_by_sections=False)
```

**Security:** Validates file paths to prevent directory traversal, checks extension whitelist, validates file size (<50MB).

---

### `add_documents_batch(files, use_progress=False)`

Add multiple documents in batch with progress indication.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `files` | `List[str]` | Required | List of file paths to index |
| `use_progress` | `bool` | `False` | Show progress logging |

**Returns:**
`Dict[str, bool]` - Mapping from filepath to success status

**Example:**
```python
files = ["file1.md", "file2.txt", "file3.py"]
results = memory.add_documents_batch(files, use_progress=True)

# Check results
for path, success in results.items():
    if success:
        print(f"✓ {path}")
    else:
        print(f"✗ {path}")
```

---

### `index_directory(directory, recursive=True, base_dir=None)`

Recursively index all files in a directory.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `directory` | `str` | Required | Directory path to index |
| `recursive` | `bool` | `True` | Recurse into subdirectories |
| `base_dir` | `str` | `None` | Base directory for security validation |

**Returns:**
`int` - Number of files indexed

**Example:**
```python
# Index entire directory
files_indexed = memory.index_directory("/path/to/notes")

# Exclude certain directories
memory.config.exclude_dirs = ".git,__pycache__"
count = memory.index_directory("/path/to/project")
```

**Note:** Only indexes files matching configured extensions (default: .md, .txt, .py, .json, .yaml, .yml, .csv).

---

### `index_file(filepath, base_dir=None)`

Index a single file.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `filepath` | `str` | Required | Path to file |
| `base_dir` | `str` | `None` | Base directory for security validation |

**Returns:**
`int` - Number of chunks indexed (1 for non-chunked files)

**Example:**
```python
# Index single file
chunks = memory.index_file("/path/to/readme.md")
print(f"Indexed {chunks} chunks")
```

**Difference from `add_document()`:**
- `index_file()` reads from disk and returns chunk count
- `add_document()` accepts optional content, returns success boolean

---

### `persist()`

Save index and metadata to disk.

**Returns:**
`bool` - True if successful

**Example:**
```python
# Manually persist after adding documents
memory.add_document("file.md")
success = memory.persist()

if success:
    print("Index saved successfully")
```

**Note:** Documents are automatically persisted when added. Call this only if you need explicit save control.

---

### `reset()`

Clear all data from memory.

**Returns:**
`bool` - True if successful

**Example:**
```python
# Clear all indexed data
memory.reset()
print("Index cleared")
```

**Warning:** This permanently deletes all indexed documents and chunks. Cannot be undone.

---

### `get_document_count()`

Get total number of indexed documents.

**Returns:**
`int` - Document count

**Example:**
```python
count = memory.get_document_count()
print(f"Indexed documents: {count}")
```

---

### `get_chunk_count()`

Get total number of indexed chunks.

**Returns:**
`int` - Chunk count

**Example:**
```python
chunks = memory.get_chunk_count()
print(f"Indexed chunks: {chunks}")
```

---

### `get_document_paths()`

Get list of all indexed file paths.

**Returns:**
`List[str]` - List of file paths

**Example:**
```python
paths = memory.get_document_paths()
for path in paths:
    print(f"Indexed: {path}")
```

---

### `health_check()`

Verify system health (Ollama connection, index state).

**Returns:**
`bool` - True if healthy

**Example:**
```python
if memory.health_check():
    print("All systems operational")
else:
    print("Check Ollama connection")
```

---

### `get_status()`

Get complete system status.

**Returns:**
`Dict` with keys:
- `healthy` (bool): Overall health status
- `ollama` (bool): Ollama connection status
- `index_loaded` (bool): Whether FAISS index is loaded
- `doc_count` (int): Number of documents
- `chunk_count` (int): Number of chunks
- `config` (dict): Configuration summary

**Example:**
```python
status = memory.get_status()
print(f"Documents: {status['doc_count']}")
print(f"Ollama: {'✓' if status['ollama'] else '✗'}")
```

---

## Utility Functions

### `chunk_markdown(text, filepath, min_chunk_size=50)`

Split markdown by ## headings.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `text` | `str` | Required | Markdown content |
| `filepath` | `str` | Required | Original file path |
| `min_chunk_size` | `int` | `50` | Minimum chunk size in chars |

**Returns:**
`List[ChunkMetadata]` - List of chunk objects

**Example:**
```python
from fmem.fmem import chunk_markdown

text = "## Section 1\nContent...\n## Section 2\nMore..."
chunks = chunk_markdown(text, "file.md")

for chunk in chunks:
    print(f"{chunk.id}: {chunk.heading}")
    print(f"Tokens: {chunk.tokens}")
```

---

## Integration Functions

### `auto_recall(query_text, system=None, top_k=3, chunk_mode='chunk')`

Auto-search with formatted results for agents.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query_text` | `str` | Required | Query to search |
| `system` | `MemoryRetrieval` | `None` | Existing instance or creates new |
| `top_k` | `int` | `3` | Number of results |
| `chunk_mode` | `str` | `"chunk"` | Result mode |

**Returns:**
`List[Dict]` - Search results or empty list

**Example:**
```python
from fmem import auto_recall

results = auto_recall("what were my fitness goals", top_k=3)
for result in results:
    print(f"[{result['score']:.2f}] {result['filepath']}")
```

---

### `should_search(text)`

Check if text contains trigger patterns for memory recall.

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `text` | `str` | Text to analyze |

**Returns:**
`bool` - True if text contains triggers

**Example:**
```python
from fmem import should_search

if should_search("remember my favorite movies"):
    print("Should trigger memory search")
```

**Trigger patterns:** "remember", "recall", "what about", "last week", "previous", "before", "my goals", "my projects", etc.

---

### `format_results(results, max_preview=150)`

Format search results for display.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `results` | `List[Dict]` | Required | Search results from `search()` |
| `max_preview` | `int` | `150` | Maximum preview length |

**Returns:**
`str` - Formatted text for display

**Example:**
```python
from fmem import auto_recall, format_results

results = auto_recall("my projects")
formatted = format_results(results)
print(formatted)
```

---

## ChunkMetadata Class

Represents a document chunk with metadata.

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `id` | `str` | Unique chunk ID (e.g., "file.md#section-name") |
| `parent_file` | `str` | Original file path |
| `heading` | `str` | Section heading text |
| `content` | `str` | Chunk content |
| `keywords` | `List[str]` | Extracted keywords |
| `category` | `str` | Inferred category |
| `tokens` | `int` | Approximate token count |
| `chunk_index` | `int` | Position within parent file |

### Methods

**`to_dict()`**
Convert to dictionary representation.

**`from_dict(data)`** (classmethod)
Create ChunkMetadata from dictionary.

---

## ConfigManager Class

Configuration management with environment variable support.

### Key Settings

| Setting | Description | Default |
|---------|-------------|---------|
| `data_dir` | Storage directory | `~/.openclaw/memory` |
| `ollama_url` | Ollama endpoint | `http://localhost:11434` |
| `VALID_EXTENSIONS` | Allowed file extensions | `.md, .txt, .py, .json, .yaml, .yml, .csv` |
| `MAX_FILE_SIZE` | Maximum file size (bytes) | 50MB |
| `MAX_BATCH_SIZE` | Max batch size for indexing | 100 |
| `additional_dirs` | Extra directories to index | `""` |
| `exclude_dirs` | Directories to exclude | `""` |
| `index_files` | Specific files to index | `""` |

---

## Error Handling

All methods return appropriate types on failure:
- Boolean methods return `False`
- Count methods return `0`
- Search methods return empty list `[]`
- Format methods return empty string `""`

Check logs for detailed error messages:
```python
import logging
logging.getLogger("fmem").setLevel(logging.DEBUG)
```

---

## Rate Limiting

Embedding generation is rate-limited (hardcoded at 10 requests/minute) to prevent Ollama overload. This is automatic and requires no configuration.

---

## Security Features

- Path sanitization prevents directory traversal
- File extension whitelisting
- Symlink validation
- File size limits
- Query length validation
- SQL injection protection (parameterized queries only)

---

**Last Updated:** 2026-02-16  
**Version:** 3.0.0