# Chunking Strategy

## Overview

fmem uses fixed-size chunking based on the embedding model's token limits. The all-minilm:22m model constrains us to ~512 tokens (~800 characters).

## The Real Constraint

**Not hardware RAM - the embedding model's context window.**

**all-minilm:22m specs:**
- Context length: 512 tokens
- Embedding length: 384 dimensions
- Tokens ≈ characters / 4 (roughly)

**Safe limit: 800 characters** to fit within 512 tokens with margin.

## Design Rationale

### Previous Problem (v3.1.x)
1. Hardware-based adaptive chunking (1K/2K/5K) was based on RAM
2. But embedding model only accepts ~512 tokens
3. Large chunks were pointless - they got truncated to ~500 chars anyway
4. **Tables caused 6+ LLM calls per file** for complex markdown

### Current Solution (v3.2.0+)
- **Hybrid Chunking**: Fixed 800 char chunks + table-aware splitting
- Smart boundary detection (keeps semantic structure)
- **Tables treated as atomic units** (no splitting mid-table)
- **Zero LLM calls** - pure Python regex parsing
- Preprocess to ~500 chars for embedding (headings + summary)

## Hybrid Chunking (v3.2.0+)

### The Table Problem

Markdown tables are challenging because:
- They contain structure that shouldn't be split (mid-row breaks meaning)
- `##` headings don't work as boundaries (tables span sections)
- Previous workaround: LLM-based extraction (6+ API calls per file)

### Solution: md2chunks-style Hybrid Splitting

**Inspired by:** [verloop/md2chunks](https://github.com/verloop/md2chunks) approach

**Key innovation:** Treat tables as **atomic units** while using traditional splitting for prose.

```
┌────────────────────────────────────────────────────────────┐
│  Hybrid Chunking Pipeline                                  │
├────────────────────────────────────────────────────────────┤
│  1. Detect tables via regex:                               │
│     ^\|[^\n]+\|\n\|[-:]+\|\n(?:\|[^\n]+\|\n?)+           │
│                                                            │
│  2. Tables become atomic chunks:                           │
│     - Extract all cells (skip `|------|` separators)       │
│     - Join into single line of text                       │
│     - Preserve header context from parent ## sections      │
│                                                            │
│  3. Non-table content split via traditional approach:       │
│     - ## headings → chunks                                │
│     - Paragraph boundaries                                │
│     - 800 char limit with overlap                         │
└────────────────────────────────────────────────────────────┘
```

### Table Detection Regex

```python
# Pattern: header row + separator + data rows
table_pattern = r'(?m)^\|[^\n]+\|\n\|[-:| ]+\|\n(?:\|[^\n]+\|\n?)+'
```

**Matches:**
```markdown
| Col1 | Col2 |
|------|------|
| A    | B    |
| C    | D    |
```

**Extracts as:** `"Col1 Col2 A B C D"` (separator lines removed)

### Performance Comparison

| Metric | Before (LLM) | After (Hybrid) | Change |
|--------|-------------|----------------|--------|
| **LLM calls** | 6-8 per file | **0** | -6 to -8 |
| **Table integrity** | Split mid-row | **Atomic** | Preserved |
| **Cost** | Ollama requests | **Free** | $0 |
| **Chunks (backup.md)** | 13 | **18** | +5 preserved |

### Incremental Indexing Metrics

Tested on 3 files with varying table density:

| File | Size | Tables | Time | Chunks |
|------|------|--------|------|--------|
| backup.md | 6,927 bytes | 5 | 1.430s | 18 |
| 2026-02-22.md | 1,783 bytes | 1 | 0.401s | 6 |
| implementation-plan.md | 14,846 bytes | 5 | 1.842s | 31 |
| **Total** | **23,556 bytes** | **11** | **3.673s** | **55** |

**No LLM calls were made during indexing.**

## Implementation

### Chunk Size

```python
def get_optimal_chunk_size() -> int:
    """Return 800 - based on all-minilm:22m's 512 token limit."""
    return 800
```

Not adaptive by design - the model constrains us, not RAM.

### Boundary Detection

When content exceeds 800 chars, splits intelligently at:

1. **Section boundaries** (`##` headings) - preserves structure
2. **Paragraph boundaries** (blank lines) - maintains flow
3. **Sentence boundaries** (periods) - semantic coherence
4. **Word boundaries** (spaces) - graceful fallback

```python
def chunk_content_adaptively(
    content: str,
    max_chunk_size: int = 800,
    overlap_chars: int = 100
) -> List[str]:
    """Split content at semantic boundaries with overlap."""
```

### Overlap Strategy

Each chunk includes 100 characters of overlap with the previous chunk:

```
Chunk 1: [Content A][Overlap: 100 chars from B]
Chunk 2: [100 chars from A][Content B][Overlap: 100 chars from C]
Chunk 3: [100 chars from B][Content C]
```

This preserves semantic continuity across boundaries.

### Preprocessing for Embedding

Before embedding, content is preprocessed to ~500 characters:

```python
def _preprocess_for_embedding(content: str, heading: str = "") -> str:
    """
    1. Extract ## and ### headings (up to 8)
    2. Create summary from first 180 chars of text
    3. Combine: headings + summary (~500 chars)
    """
```

Full chunk content is stored for retrieval, but only ~500 chars go into the embedding.

## Size Comparison

| Aspect | Size | Purpose |
|--------|------|---------|
| Chunk | 800 chars | Storage unit in FAISS |
| Preprocessed | ~500 chars | What gets embedded |
| Overlap | 100 chars | Semantic continuity |
| Token limit | 512 tokens | all-minilm:22m constraint |

## Integration

### In `chunk_markdown()`

Markdown files are split by `##` headings first. Large sections (\>800 chars) are further subdivided.

```python
chunks = chunk_markdown(content, filepath, adaptive=True)
# Each chunk: max 800 chars with smart boundaries
```

### In `add_document()`

```python
# Index each chunk
for chunk in chunks:
    # Store full content (800 chars)
    # Embed preprocessed version (~500 chars)
    embedding = self._get_embedding(chunk.content, heading=chunk.heading)
```

## When to Use Large vs Small Content

**Works well:**
- Notes with ## sections (~200-800 chars each)
- Documentation with clear structure
- Daily memory logs with headings

**Doesn't matter:**
- Very large tables (will split into multiple chunks)
- Code files (will split at function boundaries)

## Performance

| Aspect | Impact |
|--------|--------|
| Indexing speed | ~same (800 vs 5000) |
| Search quality | Better (no wasted tokens) |
| Memory usage | Lower (smaller embeddings) |
| Disk usage | Same (full content stored) |

## Migration

**No action required** for existing users. Changes are internal.

New behavior:
- Chunk size: Fixed at 800 chars (was hardware-based 1K-5K)
- Embedding: ~500 chars preprocessed (unchanged)
- Search: Same or better quality

## References

### External Projects

**Hybrid chunking approach inspired by:**
- **[verloop/md2chunks](https://github.com/verloop/md2chunks)** - Table-aware markdown splitting
- **[joshuamckenty/advanced-chunking](https://github.com/joshuamckenty/advanced-chunking)** - Semantic merging strategies
- **[dorian-brown/semantic-chunker](https://github.com/dorian-brown/semantic-chunker)** - Embedding-based chunk optimization

### fmem Implementation

- **Code**: `src/fmem/fmem.py` functions:
  - `get_optimal_chunk_size()` - returns 800
  - `chunk_content_adaptively()` - splits at boundaries
  - `_preprocess_for_embedding()` - ~500 chars for embedding
  - `_get_embedding()` - calls preprocessing before embedding
  
- **New Module**: `src/fmem/md2chunks_splitter.py`
  - `extract_tables()` - Table detection via regex
  - `clean_table()` - Convert tables to clean text
  - `get_header_context()` - Preserve parent headings
  - `md2chunks_split()` - Main hybrid splitting logic

---

**Last Updated:** 2026-02-22
**Version:** fmem 3.2.0
**Status:** Production Ready

### Attribution

This implementation combines:
1. **Table handling**: Adapted from md2chunks (verloop/md2chunks)
2. **Semantic splitting**: Fixed-size with boundary detection (fmem original)
3. **Header context**: Parent heading preservation (inspired by md2chunks)

All LLM-based workarounds have been removed. Pure Python implementation.
