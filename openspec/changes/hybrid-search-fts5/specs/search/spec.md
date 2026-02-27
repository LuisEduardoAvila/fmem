# Specification: Hybrid Search (Semantic + FTS5)

## Requirements

### REQ-001: FTS5 Index Creation
**As a** fmem user  
**I want** text content automatically indexed for keyword search  
**So that** exact matches can be found quickly

#### Scenarios

##### SC-001: Automatic FTS5 Table Creation
**Given** fmem document indexing is enabled  
**When** a new document is processed  
**Then** content is added to both:
- Vector embeddings table (existing)
- FTS5 virtual table (new)

##### SC-002: FTS5 Schema
**Given** chunk content is being indexed  
**Then** FTS5 table stores:
- `chunk_id` (primary key, links to embeddings table)
- `content` (full text for tokenization)
- Indexed fields: `heading`, `filepath`, `content`

**Edge Cases:**
- Empty content: store empty string in FTS5 (ok)
- Very large content: FTS5 handles up to ~1GB per value
- Special characters: FTS5 tokenizer handles them

---

### REQ-002: Keyword Search API
**As a** developer  
**I want** a pure keyword search endpoint  
**So that** I can find exact matches without semantic overhead

#### Scenarios

##### SC-003: Keyword Search Method
**Given** FTS5 index is populated  
**When** `search_keyword(query)` is called  
**Then** return results ranked by FTS5 BM25 scores

```python
# API design
results = memory.search_keyword(
    query="error ECONNREFUSED",
    limit=10
)
# Returns: List[ChunkResult] with relevance scores
```

##### SC-004: FTS5 Query Syntax Support
**Given** advanced queries using FTS5 syntax  
**When** query contains:
- `"exact phrase"` → phrase search
- `term1 AND term2` → conjunctive
- `term1 OR term2` → disjunctive  
**Then** FTS5 interprets accordingly

---

### REQ-003: Hybrid Search (RRF Fusion)
**As a** fmem user  
**I want** semantic and keyword results combined  
**So that** I get both conceptual and exact matches

#### Scenarios

##### SC-005: Hybrid Search Method
**Given** both embeddings and FTS5 indexes exist  
**When** `search(query, mode="hybrid")` is called  
**Then**:
1. Run semantic search → get ranked list A
2. Run FTS5 keyword search → get ranked list B
3. Apply RRF fusion (k=60) to combine A + B
4. Return fused results

```python
results = memory.search(
    query="How do I fix the database connection?",
    mode="hybrid",           # new mode
    hybrid_alpha=0.7,        # semantic weight (0.0-1.0)
    limit=10
)
```

##### SC-006: Hybrid Alpha Configuration
**Given** different query types need different balances  
**When** `hybrid_alpha` is configured  
**Then**:
- `alpha=1.0` → Pure semantic (current behavior)
- `alpha=0.0` → Pure keyword (BM25 only)
- `alpha=0.5` → Balanced fusion
- Default: `0.7` (favor semantic, augment with keyword)

---

### REQ-004: Search Mode Selection
**As a** fmem user  
**I want** to choose search mode per query  
**So that** I can optimize for query type

#### Scenarios

##### SC-007: Mode Parameter
**Given** the search API  
**When** mode is specified  
**Then**:
- `mode="semantic"` → Current vector search only
- `mode="keyword"` → FTS5 search only
- `mode="hybrid"` → RRF fusion of both

##### SC-008: Default Mode
**Given** no mode is specified  
**When** search is called  
**Then** use `config.search.default_mode` (default: "hybrid")

---

### REQ-005: Backward Compatibility
**As a** fmem maintainer  
**I want** existing code to work unchanged  
**So that** upgrades don't break integrations

#### Scenarios

##### SC-009: Existing API Unchanged
**Given** existing `search()` calls without mode parameter  
**When** they execute  
**Then** behavior remains identical to current semantic search

##### SC-010: Config Migration
**Given** existing fmem config without FTS5 settings  
**When** fmem initializes  
**Then**:
- FTS5 tables created on next index operation
- Config defaults applied
- No errors

---

## Configuration Schema

```python
class HybridSearchConfig:
    """Configuration for hybrid search."""
    
    # Default search mode
    default_mode: Literal["semantic", "keyword", "hybrid"] = "semantic"
    """
    Default search mode. Use "semantic" for backward compatibility,
    "hybrid" for best results.
    """
    
    # Hybrid fusion settings
    hybrid_alpha: float = 0.7
    """
    Weight for semantic vs keyword (0.0-1.0).
    0.7 = 70% semantic, 30% keyword influence via RRF.
    """
    
    # RRF parameter
    rrf_k: int = 60
    """RRF constant (typically 20-100)."""
    
    # FTS5 settings
    fts5_tokenizer: str = "porter"
    """Tokenizer: porter (stemming), unicode61, ascii"""
    
    fts5_content_table: str = "chunks"
    """Table to shadow for content."""


class SearchOptions:
    """Per-query search options."""
    
    mode: Optional[Literal["semantic", "keyword", "hybrid"]] = None
    """Override default mode for this query."""
    
    hybrid_alpha: Optional[float] = None
    """Override alpha for this query."""
    
    filters: Optional[Dict] = None
    """Additional filters (filepath, date range, etc)."""
```

---

## Database Schema

### FTS5 Virtual Table
```sql
-- FTS5 table for keyword search
CREATE VIRTUAL TABLE chunk_fts USING fts5(
    content,
    heading,
    filepath,
    content='chunks',
    content_rowid='id',
    tokenize='porter'
);

-- Triggers to keep FTS5 in sync
CREATE TRIGGER chunks_fts_insert AFTER INSERT ON chunks BEGIN
    INSERT INTO chunk_fts(rowid, content, heading, filepath)
    VALUES (new.id, new.content, new.heading, new.filepath);
END;

CREATE TRIGGER chunks_fts_delete AFTER DELETE ON chunks BEGIN
    INSERT INTO chunk_fts(chunk_fts, rowid, content, heading, filepath)
    VALUES ('delete', old.id, old.content, old.heading, old.filepath);
END;

CREATE TRIGGER chunks_fts_update AFTER UPDATE ON chunks BEGIN
    INSERT INTO chunk_fts(chunk_fts, rowid, content, heading, filepath)
    VALUES ('delete', old.id, old.content, old.heading, old.filepath);
    INSERT INTO chunk_fts(rowid, content, heading, filepath)
    VALUES (new.id, new.content, new.heading, new.filepath);
END;
```

---

## Implementation Notes

### Dependencies
- **SQLite FTS5**: Built into SQLite since 3.9.0 (2015), widely available
- **No Python deps required**: Uses sqlite3 built-in FTS5 support

### Performance Considerations
- FTS5 queries are ~10-100x faster than full semantic search
- Hybrid adds 1 FTS5 query overhead (minimal)
- FTS5 index size: ~20-30% of original content size

### RRF Fusion Algorithm (for hybrid)
```python
def rrf_fusion(semantic_ranked: List, keyword_ranked: List, k: int = 60) -> List:
    """
    Reciprocal Rank Fusion for combining semantic and keyword results.
    """
    scores = defaultdict(float)
    
    # Semantic scores (using existing semantic rank)
    for rank, result in enumerate(semantic_ranked):
        scores[result.chunk_id] += 1 / (k + rank + 1)
    
    # Keyword scores (using FTS5 rank)
    for rank, result in enumerate(keyword_ranked):
        scores[result.chunk_id] += 1 / (k + rank + 1)
    
    # Sort by combined score
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

---

## Comparison: claude-mem vs fmem hybrid

| Feature | claude-mem | Proposed fmem |
|---------|-----------|---------------|
| Semantic DB | Chroma | Ollama (existing) |
| Keyword DB | SQLite FTS5 | SQLite FTS5 (same!) |
| Fusion | Internal Chroma | RRF (our implementation) |
| Progressive Disclosure | Yes (3 layers) | No (direct results) |
| UI | Web viewer localhost:37777 | CLI only |

**Key insight:** claude-mem proves FTS5 + vector works. fmem can achieve similar results with simpler architecture (no Chroma dependency).
