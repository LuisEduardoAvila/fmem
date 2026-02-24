# Technical Refactoring Blueprint - fmem v3.1.0

## Overview

This document outlines a structural refactoring of the fmem codebase to improve:
- **Single Responsibility Principle (SRP)** - Separate distinct responsibilities into focused classes
- **Dependency Injection (DI)** - Replace singleton ConfigManager with constructor injection

### CRITICAL CONSTRAINT: Logic Preservation
The refactoring is **purely structural**. All business logic, algorithms, and behavior must remain 100% identical. No optimizations, bug fixes, or feature additions.

---

## Phase 1: ConfigManager Singleton Removal

### Current State
- `ConfigManager` is a global singleton accessed via `CONFIG = ConfigManager()`
- Classes import and use `CONFIG` directly
- Tight coupling makes testing difficult

### Target State
- Constructor-based Dependency Injection
- Each class receives config via constructor
- No global singleton (optional: provide factory for convenience)

### Implementation Plan

#### 1.1 Create Config Data Class
```python
# src/fmem/config.py (new file)
@dataclass
class ConfigData:
    """Immutable configuration data container."""
    data_dir: str
    ollama_url: str
    index_name: str
    metadata_name: str
    sqlite_name: str
    VALID_EXTENSIONS: Set[str]
    MAX_FILE_SIZE: int
    # ... all config fields as dataclass fields
```

#### 1.2 Refactor ConfigManager to ConfigService
```python
# src/fmem/config.py (modified)
class ConfigService:
    """Loads and provides configuration. No longer a singleton."""
    
    def __init__(self, config_path: str = None):
        self._config = self._load_config(config_path)
    
    def get_config(self) -> ConfigData:
        return self._config
    
    # Keep ALL existing loading logic unchanged
    # - Environment variable reading
    # - Config file parsing
    # - Default value handling
```

#### 1.3 Update Class Constructors

| Class | Constructor Change |
|-------|-------------------|
| `MemoryRetrieval` | `__init__(self, config: ConfigService = None)` |
| `FastEmbedClient` | Already accepts parameters, no change needed |
| `RateLimiter` | Already accepts parameters, no change needed |

#### 1.4 Provide Backward Compatibility
```python
# src/fmem/config.py (add to end)
# Global singleton for backward compatibility
_config_service_instance = None

def get_config() -> ConfigData:
    """Backward-compatible global config access."""
    global _config_service_instance
    if _config_service_instance is None:
        _config_service_instance = ConfigService()
    return _config_service_instance.get_config()
```

### Verification - ConfigManager
- [ ] All existing config values are loaded identically
- [ ] Environment variable precedence unchanged
- [ ] Config file parsing unchanged
- [ ] Default values identical
- [ ] Backward compatibility works: `from fmem import CONFIG` still functions

---

## Phase 2: MemoryRetrieval SRP Decomposition

### Current State
`MemoryRetrieval` (~3200 lines) has 7+ distinct responsibilities:

| Responsibility | Current Methods |
|---------------|-----------------|
| Document Management | `add_document()`, `add_documents_batch()` |
| Embedding Operations | `_get_embedding()`, `_generate_embeddings_batch()` |
| FAISS Index Management | `search()`, internal index ops |
| Database Operations | `_store_embedding()`, `_store_chunk_metadata()`, `_init_database()` |
| Search Enhancement | `_enhance_search_results_with_recency()`, `_enhance_search_results_with_location()` |
| Score Calculation | `_calculate_recency_score()`, `_calculate_location_weight()` |
| File Summarization | `_extract_file_summary()`, `_extract_memory_summary()`, `_extract_regular_summary()` |
| Persistence | `persist()`, `reset()` |
| Directory Indexing | `index_directory()`, `index_directory_batched()` |

### Target Architecture

```
MemoryRetrieval (Facade/Orchestrator)
    ├── DocumentManager (document/chunk lifecycle)
    ├── EmbeddingService (embedding generation + caching)
    ├── SearchIndex (FAISS operations)
    ├── DatabaseService (SQLite operations)
    ├── ResultEnhancer (recency + location ranking)
    ├── FileSummarizer (summary extraction)
    └── PersistenceManager (save/load index)
```

### Implementation Plan

#### 2.1 EmbeddingService (New Class)
**Responsibility:** Embedding generation, caching, rate limiting

```python
# src/fmem/embedding_service.py (new file)
class EmbeddingService:
    """Handles embedding generation with caching and rate limiting."""
    
    def __init__(
        self,
        embedding_client: Any,  # FastEmbedClient
        config: ConfigService,
        rate_limiter: RateLimiter = None
    ):
        self._client = embedding_client
        self._config = config
        self._cache = _LRUCache(maxsize=10000, ttl=3600)  # Preserve existing cache
        self._rate_limiter = rate_limiter or RateLimiter(
            max_requests=config.rate_limit_requests,
            window_seconds=config.rate_limit_window_seconds
        )
    
    def get_embedding(self, text: str, heading: str = "") -> Optional[np.ndarray]:
        # COPY logic from MemoryRetrieval._get_embedding()
        # Preserve: preprocessing, caching, rate limiting
    
    def get_embeddings_batch(self, texts: List[str]) -> Optional[np.ndarray]:
        # COPY logic from MemoryRetrieval._generate_embeddings_batch()
    
    def _preprocess_for_embedding(self, content: str, heading: str = "") -> str:
        # COPY unchanged
```

**Verification:**
- [ ] Same embedding client used
- [ ] Same preprocessing logic (`_preprocess_for_embedding`)
- [ ] Same caching behavior (LRU + TTL)
- [ ] Same rate limiting behavior
- [ ] Same hash generation for cache keys

---

#### 2.2 SearchIndex (New Class)
**Responsibility:** FAISS index operations

```python
# src/fmem/search_index.py (new file)
class SearchIndex:
    """Manages FAISS index operations."""
    
    def __init__(self, dimension: int = 384):
        self._index = None
        self._dimension = dimension
        self._chunk_index_map = []  # Preserve exact structure
    
    def add(self, embedding: np.ndarray, metadata: Dict) -> int:
        # COPY FAISS add logic
    
    def search(self, query_embedding: np.ndarray, top_k: int) -> List[Tuple[int, float]]:
        # COPY FAISS search logic
    
    def get_chunk_mapping(self, faiss_idx: int) -> Dict:
        # Preserve exact chunk_index_map lookup
    
    def reset(self):
        # Preserve reset behavior
    
    def load(self, index_path: str):
        # COPY faiss.read_index
    
    def save(self, index_path: str):
        # COPY faiss.write_index
```

**Verification:**
- [ ] Same FAISS index type (IndexFlatIP)
- [ ] Same dimension (384)
- [ ] Same chunk_index_map structure
- [ ] Same search threshold (0.3)
- [ ] Same index persistence logic

---

#### 2.3 DatabaseService (New Class)
**Responsibility:** All SQLite operations

```python
# src/fmem/database_service.py (new file)
class DatabaseService:
    """Handles all SQLite database operations."""
    
    def __init__(self, db_path: str, config: ConfigService):
        self._db_path = db_path
        self._conn = None
        self._init_database()  # COPY unchanged
    
    def store_document(self, metadata: Dict, content: str) -> Optional[int]:
        # COPY from MemoryRetrieval._store_embedding()
    
    def store_chunk(self, chunk: ChunkMetadata) -> bool:
        # COPY from MemoryRetrieval._store_chunk_metadata()
    
    def get_chunks_for_file(self, filepath: str) -> List[ChunkMetadata]:
        # COPY from MemoryRetrieval._get_chunks_for_file()
    
    def get_chunk_by_id(self, chunk_id: str) -> Optional[ChunkMetadata]:
        # COPY from MemoryRetrieval._get_chunk_by_id()
    
    def load_documents(self) -> List[Dict]:
        # COPY from MemoryRetrieval._load_from_database()
    
    def close(self):
        # Preserve connection closing
```

**Verification:**
- [ ] Same table schema (documents, embeddings, chunks)
- [ ] Same index creation
- [ ] Same SQL queries
- [ ] Same error handling

---

#### 2.4 ResultEnhancer (New Class)
**Responsibility:** Search result scoring (recency + location)

```python
# src/fmem/result_enhancer.py (new file)
class ResultEnhancer:
    """Applies recency and location-based ranking to search results."""
    
    def __init__(self, config: ConfigService):
        self._config = config
    
    def enhance(self, results: List[Dict], doc_metadata: Dict[str, Dict]) -> List[Dict]:
        # Combine recency and location enhancement
        # COPY exactly: _enhance_search_results_with_recency()
        # COPY exactly: _enhance_search_results_with_location()
    
    def _calculate_recency_score(self, last_modified: float, filepath: str = None) -> float:
        # COPY unchanged from MemoryRetrieval
    
    def _calculate_location_weight(self, filepath: str) -> float:
        # COPY unchanged from MemoryRetrieval
    
    def _is_append_only_file(self, filepath: str) -> bool:
        # COPY unchanged from MemoryRetrieval
```

**Verification:**
- [ ] Same recency scoring formula
- [ ] Same location weight mapping
- [ ] Same append-only file detection
- [ ] Same weight normalization logic
- [ ] Same enhancement order (recency then location)

---

#### 2.5 FileSummarizer (New Class)
**Responsibility:** Extract file summaries for context

```python
# src/fmem/file_summarizer.py (new file)
class FileSummarizer:
    """Extracts summaries from files for context injection."""
    
    def summarize(self, content: str, filepath: str) -> str:
        # Dispatch to appropriate summarizer
        # COPY from MemoryRetrieval._extract_file_summary()
    
    def _extract_memory_summary(self, content: str, filepath: str) -> str:
        # COPY unchanged
    
    def _extract_regular_summary(self, content: str, filepath: str) -> str:
        # COPY unchanged
```

**Verification:**
- [ ] Same memory file detection (regex patterns)
- [ ] Same heading extraction
- [ ] Same status keyword detection
- [ ] Same summary format

---

#### 2.6 DocumentManager (New Class)
**Responsibility:** Document lifecycle (add, index, chunk)

```python
# src/fmem/document_manager.py (new file)
class DocumentManager:
    """Manages document indexing and chunking."""
    
    def __init__(
        self,
        embedding_service: EmbeddingService,
        search_index: SearchIndex,
        database_service: DatabaseService,
        file_summarizer: FileSummarizer,
        config: ConfigService
    ):
        self._embedding_service = embedding_service
        self._search_index = search_index
        self._db = database_service
        self._summarizer = file_summarizer
        self._config = config
        self._doc_metadata = []  # Preserve structure
    
    def add_document(self, filepath: str, content: str = None) -> bool:
        # COPY add_document logic
        # - Path validation (sanitize_path)
        # - Symlink check
        # - File reading
        # - Chunking (chunk_markdown)
        # - Embedding generation
        # - FAISS index update
        # - Database storage
    
    def index_directory(self, directory: str, ...) -> int:
        # COPY index_directory logic
    
    def index_directory_batched(self, directory: str, ...) -> int:
        # COPY batched indexing logic
    
    def get_document_count(self) -> int:
        # Preserve
    
    def get_document_paths(self) -> List[str]:
        # Preserve
```

**Verification:**
- [ ] Same path sanitization
- [ ] Same symlink validation
- [ ] Same file extension checking
- [ ] Same chunking (chunk_markdown)
- [ ] Same mtime-based change detection
- [ ] Same batch processing logic

---

#### 2.7 PersistenceManager (New Class)
**Responsibility:** Save/load index and metadata

```python
# src/fmem/persistence_manager.py (new file)
class PersistenceManager:
    """Handles saving and loading index and metadata."""
    
    def __init__(self, config: ConfigService):
        self._config = config
    
    def save(self, doc_metadata: List[Dict], chunk_index_map: List[Dict]) -> bool:
        # COPY MemoryRetrieval.persist()
        # - Save FAISS index
        # - Save metadata JSON
        # - Save chunk_index_map JSON
    
    def load(self) -> Tuple[faiss.Index, List[Dict], List[Dict]]:
        # COPY MemoryRetrieval._load_index()
```

**Verification:**
- [ ] Same file paths (index_path, metadata_path, chunk_index_map.json)
- [ ] Same JSON format
- [ ] Same error handling

---

#### 2.8 MemoryRetrieval Facade (Refactored)

```python
# src/fmem/memory_retrieval.py (refactored)
class MemoryRetrieval:
    """Facade orchestrating all services. Public API unchanged."""
    
    def __init__(
        self,
        db_path: str = None,
        config: ConfigService = None,
        embedding_client: Any = None
    ):
        # Initialize config
        self._config = config or get_config_service()
        
        # Initialize services (DI)
        self._embedding_service = EmbeddingService(
            embedding_client or FastEmbedClient(),
            self._config
        )
        self._search_index = SearchIndex()
        self._db = DatabaseService(db_path, self._config)
        self._enhancer = ResultEnhancer(self._config)
        self._summarizer = FileSummarizer()
        self._document_manager = DocumentManager(
            self._embedding_service,
            self._search_index,
            self._db,
            self._summarizer,
            self._config
        )
        self._persistence = PersistenceManager(self._config)
        
        # Load existing state
        self._load_state()
    
    def search(self, query: str, top_k: int = 5, chunk_mode: str = "chunk") -> List[Dict]:
        """Public API - behavior unchanged."""
        # 1. Validate query
        # 2. Generate query embedding
        # 3. Search FAISS
        # 4. Build results with chunk lookup
        # 5. Apply result enhancement
        # 6. Return
    
    # Delegate other methods to appropriate services
    def add_document(self, filepath: str, content: str = None) -> bool:
        return self._document_manager.add_document(filepath, content)
    
    def persist(self) -> bool:
        return self._persistence.save(self._doc_metadata, self._search_index.get_chunk_map())
```

---

## Phase 3: Module Structure

### New Directory Layout
```
src/fmem/
    __init__.py          # Updated exports
    __main__.py          # Unchanged
    cli.py               # Unchanged
    fmem_integration.py  # Unchanged
    
    # New modular structure
    config.py            # ConfigService + ConfigData
    embedding_service.py # EmbeddingService
    search_index.py      # SearchIndex
    database_service.py  # DatabaseService
    result_enhancer.py   # ResultEnhancer
    file_summarizer.py   # FileSummarizer
    document_manager.py  # DocumentManager
    persistence.py       # PersistenceManager
    
    # Original (to be removed after refactor)
    fmem.py              # Remove after migration
    
    # Unchanged
    md2chunks_splitter.py
    memory_utils.py
```

---

## Phase 4: Backward Compatibility

### __init__.py Updates
```python
# src/fmem/__init__.py
from .config import ConfigService, get_config_service, get_config
from .memory_retrieval import MemoryRetrieval
from .embedding_service import EmbeddingService
# ... other exports

# Backward compatibility
CONFIG = get_config()  # Returns ConfigData
MemoryRetrieval = MemoryRetrieval  # Works as before
```

### Migration Path
1. Create new modular structure
2. Update imports in `__init__.py`
3. Keep old `fmem.py` with deprecation warnings
4. Run test suite to verify behavior
5. Remove old `fmem.py` after transition period

---

## Verification Checklist

### General
- [ ] All existing tests pass without modification
- [ ] CLI commands produce identical output
- [ ] Same error messages for invalid inputs
- [ ] Same logging behavior

### ConfigManager
- [ ] Environment variables override config file
- [ ] Same default values
- [ ] Same validation logic

### MemoryRetrieval
- [ ] Same search results for same queries
- [ ] Same chunking behavior
- [ ] Same recency scoring
- [ ] Same location weighting
- [ ] Same persistence format
- [ ] Same database schema

### Performance
- [ ] Same throughput (no regression)
- [ ] Same memory usage
- [ ] Same caching behavior

---

## Implementation Order

1. **ConfigService** - Foundation for all other changes
2. **EmbeddingService** - Isolated, easy to test
3. **SearchIndex** - FAISS operations
4. **DatabaseService** - SQLite operations
5. **ResultEnhancer** - Scoring logic
6. **FileSummarizer** - Summary extraction
7. **DocumentManager** - Complex orchestration
8. **PersistenceManager** - Save/load
9. **MemoryRetrieval Facade** - Wire everything together
10. **Update __init__.py** - Exports and compatibility

---

## Notes

- Preserve all private methods (starting with `_`) - they contain logic
- Keep all regex patterns identical
- Keep all constant values unchanged
- Document any slight differences in this plan
- Run integration tests after each phase
