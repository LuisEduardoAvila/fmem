# fmem Configuration System Review

**Review Date:** 2026-02-16  
**Version:** 3.0.0  
**Scope:** Complete configuration system analysis

---

## Executive Summary

The fmem configuration system has a **3-tier hierarchy**: environment variables → config file → code defaults. While functional, there are several inconsistencies between hardcoded values, config file options, and documentation that need addressing.

**Key Findings:**
- ⚠️ **Rate limiting is hardcoded** (10 requests/60s) - NOT configurable
- ⚠️ **Location weights in config don't match code defaults** (chats: 0.8 vs 0.7)
- ⚠️ **Several "future use" options in config are marked as implemented but not wired**
- ⚠️ **Cache TTL is hardcoded** (1 hour) despite `enable_cache` existing in config
- ✅ **Multi-factor ranking weights are properly configurable**

---

## 1. Complete Config Inventory

### 1.1 Environment Variables (Highest Priority)

| Variable | Purpose | Default | Parsed In |
|----------|---------|---------|-----------|
| `FMEM_DATA_DIR` | Data directory path | `~/.openclaw/memory` | `ConfigManager._load_config()` |
| `FMEM_OLLAMA_URL` | Ollama endpoint | `http://localhost:11434` | `ConfigManager._load_config()` |
| `FMEM_INDEX_NAME` | FAISS index filename | `faiss_index.fai` | `ConfigManager._load_config()` |
| `FMEM_METADATA_NAME` | Metadata JSON filename | `doc_metadata.json` | `ConfigManager._load_config()` |
| `FMEM_SQLITE_NAME` | SQLite DB filename | `documents.db` | `ConfigManager._load_config()` |
| `FMEM_CONFIG` | Path to config file | `$DATA_DIR/fmem.conf` | `ConfigManager._load_config()` |
| `FMEM_DEBUG` | Debug logging level | `false` | `setup_logging()` |

### 1.2 Config File Options (fmem.conf)

#### Core Settings
| Option | Section | Type | Default | Status |
|--------|---------|------|---------|--------|
| `data_dir` | `[settings]` | string | `~/.openclaw/memory/` | ✅ Active |
| `ollama_url` | `[settings]` | string | `http://localhost:11434` | ✅ Active |
| `index_name` | `[settings]` | string | `faiss_index.fai` | ✅ Active |
| `metadata_name` | `[settings]` | string | `doc_metadata.json` | ✅ Active |
| `sqlite_name` | `[settings]` | string | `documents.db` | ✅ Active |

#### Indexing Settings
| Option | Section | Type | Default | Status |
|--------|---------|------|---------|--------|
| `extensions` | `[settings]` | list | `.md, .txt` | ✅ Active |
| `additional_dirs` | `[settings]` | list | (paths) | ✅ Active |
| `exclude_dirs` | `[settings]` | list | `venv,env,...` | ✅ Active |
| `index_files` | `[settings]` | list | (file paths) | ✅ Active |
| `index_memory_md` | `[settings]` | boolean | `true` | ⚠️ Commented out (future use) |
| `index_daily_files` | `[settings]` | boolean | `true` | ⚠️ Commented out (future use) |
| `max_batch_size` | `[settings]` | integer | `100` | ⚠️ Hardcoded in code, config ignored |

#### Ranking Settings
| Option | Section | Type | Default | Status |
|--------|---------|------|---------|--------|
| `enable_recency_ranking` | `[settings]` | boolean | `true` | ✅ Active |
| `recency_weight` | `[settings]` | float | `0.3` | ✅ Active |
| `recency_threshold_days` | `[settings]` | integer | `30` | ✅ Active |
| `min_recency_score` | `[settings]` | float | `0.1` | ✅ Active |
| `enable_location_ranking` | `[settings]` | boolean | `true` | ✅ Active |
| `location_weight` | `[settings]` | float | `0.2` | ✅ Active |
| `ranking_strategy` | `[settings]` | string | `hybrid` | ⚠️ "future use" |
| `show_score_breakdown` | `[settings]` | boolean | `false` | ⚠️ "future use" |
| `prefer_exact_directory_matches` | `[settings]` | boolean | `true` | ⚠️ "future use" |

#### Location Weights
| Option | Default (Config) | Default (Code) | Match? |
|--------|------------------|----------------|--------|
| `docs_weight` | `1.5` | `1.5` | ✅ |
| `documentation_weight` | `1.5` | `1.5` | ✅ |
| `projects_weight` | `1.3` | `1.3` | ✅ |
| `decisions_weight` | `1.4` | `1.4` | ✅ |
| `formal_weight` | `1.4` | `1.4` | ✅ |
| `work_weight` | `1.2` | `1.2` | ✅ |
| `active_weight` | `1.2` | `1.2` | ✅ |
| `current_weight` | `1.1` | `1.1` | ✅ |
| `notes_weight` | `1.0` | `1.0` | ✅ |
| `memory_weight` | `1.0` | `1.0` | ✅ |
| `chats_weight` | `0.8` | `0.8` | ✅ |
| `conversations_weight` | `0.8` | `0.8` | ✅ |
| `daily_weight` | `0.9` | `0.9` | ✅ |
| `sessions_weight` | `0.9` | `0.9` | ✅ |
| `base_weight` | `1.0` | `1.0` | ✅ |

#### Performance Settings
| Option | Default | Status | Notes |
|--------|---------|--------|-------|
| `ollama_timeout` | `30` | ✅ Active | Used in `OllamaClient` |
| `max_retries` | `3` | ✅ Active | Used in `OllamaClient` |
| `enable_cache` | `true` | ⚠️ Commented | Code comment: "Currently hardcoded ON - cannot be disabled" |

#### File Limit Settings
| Option | Default | Status | Parsed In |
|--------|---------|--------|-----------|
| `max_file_size` | `52428800` (50MB) | ⚠️ Partial | `ConfigManager.MAX_FILE_SIZE` is class constant |
| `max_query_length` | `1000` | ⚠️ Partial | `ConfigManager.MAX_QUERY_LENGTH` is class constant |
| `max_path_length` | `1024` | ⚠️ Partial | `ConfigManager.MAX_PATH_LENGTH` is class constant |

---

## 2. Hardcoded vs Configurable Analysis

### 2.1 Fully Hardcoded (NOT Configurable)

| Setting | Value | Location | Impact |
|---------|-------|----------|--------|
| **Rate limit - max requests** | 10 | `MemoryRetrieval.__init__` | HIGH - Cannot tune API limits |
| **Rate limit - window** | 60 seconds | `MemoryRetrieval.__init__` | HIGH - Fixed window size |
| **Cache TTL** | 3600 seconds (1 hour) | `_LRUCache.__init__` | MEDIUM - Cannot tune cache expiration |
| **Cache max entries** | 10,000 | `_LRUCache.__init__` | MEDIUM - Memory pressure fixed |
| **Embedding dimension** | 768 | `EMBEDDING_DIM` | LOW - Model-dependent |
| **Embedding model** | `nomic-embed-text` | `EMBEDDING_MODEL` | LOW - Model-dependent |
| **MIN_SIMILARITY_SCORE** | 0.3 | `MemoryRetrieval.search` | MEDIUM - Search threshold fixed |
| **append_only_recency_factor** | 0.33 | `ConfigManager.DEFAULT_APPEND_ONLY_RECENCY_FACTOR` | MEDIUM - Daily log weight reduction fixed |
| **MAX_EMBEDDING_SIZE** | 1MB (1024×1024) | `ConfigManager.MAX_EMBEDDING_SIZE` | MEDIUM - Content truncation limit |
| **MAX_BATCH_SIZE** | 100 | `ConfigManager.MAX_BATCH_SIZE` | LOW - Batch processing limit |

### 2.2 Code Defaults vs Config File Defaults

**Mismatches Found:**

| Setting | Config Default | Code Default | Issue |
|---------|----------------|--------------|-------|
| `extensions` | `.md, .txt` | `.md, .txt, .py, .json, .yaml, .yml, .csv` | ⚠️ Config narrows extension list |
| `max_file_size` | `52428800` | `50 * 1024 * 1024` (52428800) | ✅ Match |
| `enable_cache` | (commented) | Hardcoded `True` | ⚠️ Config option ignored |

### 2.3 "Future Use" Options Status

| Option | Config Status | Implementation Status | Recommendation |
|--------|---------------|----------------------|----------------|
| `index_memory_md` | Commented | ⚠️ Partial | `index_daily_files` IS used, but not automatic indexing |
| `index_daily_files` | Commented | ⚠️ Partial | Same as above - manual indexing only |
| `daily_scan_delay` | Commented | ❌ Not implemented | Remove or implement |
| `max_batch_size` | Commented as future | ⚠️ Hardcoded in class | Should be fully config-driven |
| `min_similarity_threshold` | Commented | ❌ Hardcoded `MIN_SIMILARITY_SCORE = 0.3` | Should connect to config |
| `enable_cache` | Commented "Currently hardcoded ON" | ❌ Truly hardcoded | Document as non-configurable |
| `log_file` | Commented | ❌ Not implemented | Either implement or remove |
| `use_enhanced_indexer` | Commented | ⚠️ Partial - enhanced indexer exists but not via config | Wire to config |
| `ranking_strategy` | Commented | ❌ Not implemented | Remove or implement hybrid-only |
| `show_score_breakdown` | Commented | ❌ Not implemented | Useful - should implement |

---

## 3. Missing from Documentation

### 3.1 Not in README.md

| Setting | Where It Is | Should Be Documented? |
|---------|-------------|-----------------------|
| `ollama_timeout` | Config + Code | ✅ Yes - performance tuning |
| `max_retries` | Config + Code | ✅ Yes - reliability |
| `append_only_recency_factor` | Code only | ✅ Yes - important for daily log ranking |
| `exclude_dirs` | Config + Code | ✅ Yes - important for avoiding venv indexing |
| `index_files` | Config + Code | ✅ Yes - alternative to `additional_dirs` |
| Location weight specifics | ARCHITECTURE only | ✅ Yes - README should summarize |
| `FMEM_*` environment variables | Code only | ⚠️ Advanced users only |

### 3.2 Not in ARCHITECTURE.md

| Setting | Where It Is | Note |
|---------|-------------|------|
| `exclude_dirs` | Config + Code | Security/performance feature not mentioned |
| `index_files` | Config + Code | Alternative indexing method not documented |
| Location weight specifics (code vs config) | Config has more detail | Config file is more accurate than ARCHITECTURE |
| Rate limiting internals | Code only | Security feature worth mentioning |
| Cache TTL configuration | Hardcoded | Architecture says "configurable" but isn't |

---

## 4. Recommendations

### 4.1 High Priority

1. **Implement rate limiting configuration**
   ```ini
   [settings]
   rate_limit_requests = 10
   rate_limit_window_seconds = 60
   ```
   Update `RateLimiter.__init__` to read from config.

2. **Fix `min_similarity_threshold` wiring**
   - Currently hardcoded as `MIN_SIMILARITY_SCORE = 0.3` in `search()`
   - Should use `self.config.getfloat('settings', 'min_similarity_threshold', fallback=0.3)`

3. **Standardize extension defaults**
   - Either update config template to match code defaults
   - Or document that config overrides code defaults (narrower list)

### 4.2 Medium Priority

4. **Implement `show_score_breakdown`**
   - Useful for debugging ranking behavior
   - Add to search results metadata when enabled

5. **Document `exclude_dirs` best practices**
   - Add to README: "Important: Always exclude venv, __pycache__, node_modules"
   - Current default excludes are good but not documented

6. **Clarify `index_files` vs `additional_dirs`**
   - `additional_dirs`: Directories to recursively index
   - `index_files`: Specific files to index (e.g., project READMEs)
   - Both serve different use cases

### 4.3 Low Priority

7. **Remove or implement unused "future use" options**
   - `ranking_strategy`: Remove (hybrid is only working strategy)
   - `log_file`: Implement or remove
   - `daily_scan_delay`: Remove (no auto-scanning implemented)

8. **Consider making cache configurable**
   - `cache_ttl`, `cache_max_entries` could be useful tunables
   - Currently hardcoded but could be exposed

### 4.4 Config Template Updates

**Current issues with fmem.conf:**

```ini
# SHOULD BE ADDED:
rate_limit_requests = 10
rate_limit_window_seconds = 60
min_similarity_threshold = 0.3

# SHOULD BE REMOVED (not implemented):
# ranking_strategy = hybrid
# show_score_breakdown = false  
# daily_scan_delay = 1800

# SHOULD BE DOCUMENTED BETTER:
# The extensions list OVERRIDES code defaults, not extends them
# Code defaults: .md, .txt, .py, .json, .yaml, .yml, .csv
# To use code defaults, comment out or omit this line
extensions = .md, .txt, .py, .json, .yaml, .yml, .csv
```

---

## 5. Configuration Hierarchy Visualization

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: Environment Variables (Highest Priority)          │
│  • FMEM_DATA_DIR, FMEM_OLLAMA_URL, FMEM_CONFIG, etc.       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 2: Config File (~/.openclaw/memory/fmem.conf)        │
│  • [settings] section parsed by ConfigManager               │
│  • Optional - falls back to defaults if missing             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 3: Code Defaults (Lowest Priority)                   │
│  • ConfigManager class constants                            │
│  • MemoryRetrieval hardcoded values                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. Summary Table: All Configurable Options

| Option | Type | Configurable | Default | Used In |
|--------|------|--------------|---------|---------|
| data_dir | path | ✅ Yes | `~/.openclaw/memory` | ConfigManager |
| ollama_url | URL | ✅ Yes | `http://localhost:11434` | OllamaClient |
| index_name | filename | ✅ Yes | `faiss_index.fai` | ConfigManager |
| metadata_name | filename | ✅ Yes | `doc_metadata.json` | ConfigManager |
| sqlite_name | filename | ✅ Yes | `documents.db` | ConfigManager |
| extensions | list | ✅ Yes | `.md, .txt` | ConfigManager |
| additional_dirs | list | ✅ Yes | (empty) | enhanced_indexer.py |
| exclude_dirs | list | ✅ Yes | venv, env, etc. | MemoryRetrieval.index_directory |
| index_files | list | ✅ Yes | (empty) | enhanced_indexer.py |
| enable_recency_ranking | bool | ✅ Yes | `true` | MemoryRetrieval |
| recency_weight | float | ✅ Yes | `0.3` | MemoryRetrieval |
| recency_threshold_days | int | ✅ Yes | `30` | MemoryRetrieval |
| min_recency_score | float | ✅ Yes | `0.1` | MemoryRetrieval |
| enable_location_ranking | bool | ✅ Yes | `true` | MemoryRetrieval |
| location_weight | float | ✅ Yes | `0.2` | MemoryRetrieval |
| docs_weight | float | ✅ Yes | `1.5` | MemoryRetrieval |
| documentation_weight | float | ✅ Yes | `1.5` | MemoryRetrieval |
| projects_weight | float | ✅ Yes | `1.3` | MemoryRetrieval |
| decisions_weight | float | ✅ Yes | `1.4` | MemoryRetrieval |
| formal_weight | float | ✅ Yes | `1.4` | MemoryRetrieval |
| work_weight | float | ✅ Yes | `1.2` | MemoryRetrieval |
| active_weight | float | ✅ Yes | `1.2` | MemoryRetrieval |
| current_weight | float | ✅ Yes | `1.1` | MemoryRetrieval |
| notes_weight | float | ✅ Yes | `1.0` | MemoryRetrieval |
| memory_weight | float | ✅ Yes | `1.0` | MemoryRetrieval |
| chats_weight | float | ✅ Yes | `0.8` | MemoryRetrieval |
| conversations_weight | float | ✅ Yes | `0.8` | MemoryRetrieval |
| daily_weight | float | ✅ Yes | `0.9` | MemoryRetrieval |
| sessions_weight | float | ✅ Yes | `0.9` | MemoryRetrieval |
| base_weight | float | ✅ Yes | `1.0` | MemoryRetrieval |
| ollama_timeout | int | ✅ Yes | `30` | OllamaClient |
| max_retries | int | ✅ Yes | `3` | OllamaClient |
| debug | bool | ✅ Yes | `false` | setup_logging |
| **rate_limit_requests** | int | ❌ **No** | `10` | RateLimiter (hardcoded) |
| **rate_limit_window** | int | ❌ **No** | `60` | RateLimiter (hardcoded) |
| **cache_ttl** | int | ❌ **No** | `3600` | _LRUCache (hardcoded) |
| **cache_maxsize** | int | ❌ **No** | `10000` | _LRUCache (hardcoded) |
| **min_similarity_threshold** | float | ❌ **No** | `0.3` | search() (hardcoded) |
| **max_file_size** | int | ⚠️ Partial | `52428800` | Class constant |
| **max_query_length** | int | ⚠️ Partial | `1000` | Class constant |
| **max_path_length** | int | ⚠️ Partial | `1024` | Class constant |

---

## 7. Action Items

| Priority | Item | File(s) Affected |
|----------|------|------------------|
| 🔴 High | Add rate limit config options | `fmem.py`, `fmem.conf` |
| 🔴 High | Wire `min_similarity_threshold` to config | `fmem.py` |
| 🔴 High | Sync extension defaults between code and config | `fmem.py`, `fmem.conf` |
| 🟡 Medium | Document `exclude_dirs` in README | `README.md` |
| 🟡 Medium | Document `index_files` usage | `README.md`, `ARCHITECTURE.md` |
| 🟡 Medium | Implement `show_score_breakdown` | `fmem.py` |
| 🟢 Low | Clean up unused "future use" options | `fmem.conf` |
| 🟢 Low | Consider cache configurability | `fmem.py` |

---

## Appendix: Code References

### Rate Limiting (Hardcoded)
```python
# fmem.py, line ~1075
self.rate_limiter = RateLimiter(max_requests=10, window_seconds=60)
```

### Similarity Threshold (Hardcoded)
```python
# fmem.py, line ~1150 in search()
MIN_SIMILARITY_SCORE = 0.3
```

### Cache Settings (Hardcoded)
```python
# fmem.py, line ~550 in _LRUCache.__init__
def __init__(self, maxsize: int = 10000, ttl: int = 3600):
```

### Extension Defaults (Code vs Config)
```python
# fmem.py, line ~425 (ConfigManager class constant)
VALID_EXTENSIONS = {'.md', '.txt', '.py', '.json', '.yaml', '.yml', '.csv'}

# fmem.conf (overrides with narrower list)
extensions = .md, .txt
```

---

*End of Configuration Review Report*
