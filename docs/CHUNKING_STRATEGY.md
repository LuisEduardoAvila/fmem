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

### Previous Problem
1. Hardware-based adaptive chunking (1K/2K/5K) was based on RAM
2. But embedding model only accepts ~512 tokens
3. Large chunks were pointless - they got truncated to ~500 chars anyway

### Current Solution
- Fixed 800 char chunks (respects model limits)
- Smart boundary detection (keeps semantic structure)
- Preprocess to ~500 chars for embedding (headings + summary)

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

- **Code**: `src/fmem/fmem.py` functions:
  - `get_optimal_chunk_size()` - returns 800
  - `chunk_content_adaptively()` - splits at boundaries
  - `_preprocess_for_embedding()` - ~500 chars for embedding
  - `_get_embedding()` - calls preprocessing before embedding

---

**Last Updated:** 2026-02-19
**Version:** fmem 3.2.0
**Status:** Production Ready
