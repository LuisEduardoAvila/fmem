# Design: Hybrid Search (Semantic + FTS5)

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                     Search Request                       │
│  query="database connection error", mode="hybrid"       │
└──────────────────────┬──────────────────────────────────┘
                       │
         ┌─────────────┴─────────────┐
         │                           │
    Semantic Path              Keyword Path
         │                           │
┌────────▼────────┐        ┌────────▼────────┐
│  Embed query    │        │  Tokenize query │
│  via Ollama   │        │  via FTS5       │
└────────┬────────┘        └────────┬────────┘
         │                           │
┌────────▼────────┐        ┌────────▼────────┐
│  Vector search  │        │  FTS5 MATCH    │
│  (existing)     │        │  BM25 ranking  │
└────────┬────────┘        └────────┬────────┘
         │                           │
         └─────────────┬─────────────┘
                       │
              ┌────────▼────────┐
              │  RRF Fusion     │
              │  k=60          │
              └────────┬────────┘
                       │
              ┌────────▼────────┐
              │  Hybrid Results │
              │  Sorted +       │
              │  Metadata       │
              └─────────────────┘
```

## Component Design

### 1. FTS5IndexService (New)

Responsibility: Manage FTS5 virtual table and queries.

```python
class FTS5IndexService:
    """Manages FTS5 keyword indexing."""
    
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path)
        self._ensure_fts5_table()
    
    def _ensure_fts5_table(self):
        """Create FTS5 virtual table if not exists."""
        self.conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS chunk_fts USING fts5(
                content,
                heading,
                filepath,
                content='chunks',
                content_rowid='id',
                tokenize='porter'
            )
        """)
        self._create_triggers()
    
    def search(self, query: str, limit: int = 10) -> List[FTS5Result]:
        """Execute FTS5 search with BM25 ranking."""
        sql = """
            SELECT c.id, c.filepath, c.heading, c.content,
                   rank AS bm25_score
            FROM chunk_fts c
            WHERE chunk_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """
        return self.conn.execute(sql, (query, limit)).fetchall()
    
    def index_chunk(self, chunk_id: int, content: str, 
                    heading: str, filepath: str):
        """Add/update chunk in FTS5 index."""
        # Trigger handles this automatically
        pass
```

### 2. Modified SearchIndex (Existing Enhancement)

Add hybrid search capability to existing class.

```python
class SearchIndex:
    """Enhanced with hybrid search support."""
    
    def __init__(self, db_path: str, config: ConfigService):
        self.db_path = db_path
        self.config = config
        self.embedding_service = EmbeddingService(config)
        self.fts5_service = FTS5IndexService(db_path)  # NEW
    
    def search(
        self, 
        query: str,
        mode: str = None,  # "semantic" | "keyword" | "hybrid"
        top_k: int = 10,
        hybrid_alpha: float = None
    ) -> List[SearchResult]:
        """
        Unified search with mode selection.
        """
        mode = mode or self.config.search.default_mode
        
        if mode == "semantic":
            return self._search_semantic(query, top_k)
        elif mode == "keyword":
            return self._search_keyword(query, top_k)
        elif mode == "hybrid":
            return self._search_hybrid(query, top_k, hybrid_alpha)
        else:
            raise ValueError(f"Unknown mode: {mode}")
    
    def _search_semantic(self, query: str, top_k: int):
        """Existing semantic search."""
        query_embedding = self.embedding_service.embed(query)
        return self._vector_search(query_embedding, top_k)
    
    def _search_keyword(self, query: str, top_k: int):
        """Pure FTS5 search."""
        return self.fts5_service.search(query, top_k)
    
    def _search_hybrid(
        self, 
        query: str, 
        top_k: int, 
        alpha: float = None
    ):
        """Hybrid: RRF fusion of semantic + keyword."""
        alpha = alpha or self.config.search.hybrid_alpha
        
        # Get results from both methods
        semantic_results = self._search_semantic(query, top_k * 2)
        keyword_results = self._search_keyword(query, top_k * 2)
        
        # Extract IDs and ranks
        semantic_ranks = {r.id: rank for rank, r in enumerate(semantic_results)}
        keyword_ranks = {r.id: rank for rank, r in enumerate(keyword_results)}
        
        # RRF fusion
        k = self.config.search.rrf_k
        all_ids = set(semantic_ranks.keys()) | set(keyword_ranks.keys())
        
        rrf_scores = {}
        for doc_id in all_ids:
            score = 0.0
            if doc_id in semantic_ranks:
                # Weight semantic by alpha
                rank = semantic_ranks[doc_id]
                score += alpha * (1 / (k + rank + 1))
            if doc_id in keyword_ranks:
                # Weight keyword by (1-alpha)
                rank = keyword_ranks[doc_id]
                score += (1 - alpha) * (1 / (k + rank + 1))
            rrf_scores[doc_id] = score
        
        # Sort and return top_k
        sorted_ids = sorted(rrf_scores.items(), 
                          key=lambda x: x[1], reverse=True)[:top_k]
        
        return self._fetch_chunks_by_ids([id for id, _ in sorted_ids])
```

### 3. Config Updates

```python
# config.py additions
@dataclass
class SearchConfig:
    # Existing fields...
    
    # Hybrid search (NEW)
    default_mode: Literal["semantic", "keyword", "hybrid"] = "semantic"
    hybrid_alpha: float = 0.7
    rrf_k: int = 60
    
    # FTS5 (NEW)
    fts5_enabled: bool = True
    fts5_tokenizer: str = "porter"
```

## Migration Strategy

### Existing Databases
```python
def migrate_add_fts5(db_path: str):
    """
    One-time migration for existing fmem databases.
    """
    conn = sqlite3.connect(db_path)
    
    # Create FTS5 table
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS chunk_fts USING fts5(
            content, heading, filepath,
            content='chunks', content_rowid='id',
            tokenize='porter'
        )
    """)
    
    # Populate with existing chunks
    conn.execute("""
        INSERT INTO chunk_fts(rowid, content, heading, filepath)
        SELECT id, content, 
               COALESCE(json_extract(metadata, '$.heading'), ''),
               COALESCE(json_extract(metadata, '$.filepath'), '')
        FROM chunks
    """)
    
    conn.commit()
    print(f"FTS5 index created: {conn.execute('SELECT COUNT(*) FROM chunk_fts').fetchone()[0]} chunks indexed")
```

## Testing Strategy

### Unit Tests
```python
def test_fts5_keyword_search():
    """Test pure keyword search."""
    results = memory.search("error handling", mode="keyword")
    assert all("error" in r.content.lower() or "handling" in r.content.lower() 
               for r in results)

def test_hybrid_outperforms_semantic_on_exact_terms():
    """Hybrid should find exact matches better than pure semantic."""
    semantic_results = memory.search("ECONNREFUSED", mode="semantic")
    hybrid_results = memory.search("ECONNREFUSED", mode="hybrid")
    
    # Hybrid should rank exact matches higher
    assert hybrid_results[0].score >= semantic_results[0].score

def test_hybrid_alpha_weights():
    """Test alpha parameter influences results."""
    r1 = memory.search("query", mode="hybrid", hybrid_alpha=0.9)
    r2 = memory.search("query", mode="hybrid", hybrid_alpha=0.1)
    
    # High alpha should favor semantic results
    # Low alpha should favor keyword results
    assert r1 != r2  # Different rankings expected
```

### Benchmark
```python
def benchmark_hybrid_vs_semantic():
    """Compare performance on keyword-heavy queries."""
    keyword_queries = [
        "def get_user_by_id",
        "ImportError: No module named",
        "git push origin main",
    ]
    
    for query in keyword_queries:
        semantic = memory.search(query, mode="semantic", limit=5)
        hybrid = memory.search(query, mode="hybrid", limit=5)
        
        # Hybrid should have better precision for technical terms
        print(f"Query: {query}")
        print(f"  Semantic top: {semantic[0].filepath}")
        print(f"  Hybrid top:   {hybrid[0].filepath}")
```

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| FTS5 not available | High | Check SQLite version at startup, fallback to semantic-only |
| Index size grows | Medium | FTS5 is ~20-30% overhead, acceptable |
| Query syntax conflicts | Low | Sanitize queries before FTS5 MATCH |
| Migration slows startup | Medium | Run migration async, show progress |

## Dependencies

```python
# requirements.txt (no changes!)
# FTS5 is built into sqlite3 since Python 3.8+
# No additional dependencies required
```

## Success Metrics

- [ ] FTS5 index created without errors
- [ ] Keyword search finds exact matches in <50ms
- [ ] Hybrid search improves precision on technical queries by >20%
- [ ] No regression on semantic search performance
- [ ] Existing tests pass without modification
