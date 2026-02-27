# Hybrid Search: Semantic + FTS5 (claude-mem inspired)

**Status:** Proposed  
**Effort:** 2-3 days  
**Risk:** Low-Medium  
**Priority:** Medium

## Problem Statement

fmem currently relies **exclusively on semantic search** via Ollama embeddings. While powerful for conceptual queries, it struggles with:

- **Exact keyword matches** (e.g., specific function names, error codes)
- **Rare / technical terms** not well-represented in embedding models
- **Boolean/structured queries** (AND/OR/phrase matching)
- **Typo tolerance** (embeddings handle this, exact search doesn't — trade-off)

Users want **hybrid search** combining the best of both worlds: semantic understanding + exact keyword matching.

## Proposed Solution

Add **FTS5 (Full-Text Search)** alongside semantic embeddings, inspired by claude-mem's hybrid approach:
- **SQLite FTS5** for fast keyword indexing
- **RRF fusion** to combine FTS5 + semantic rankings
- **Configurable hybrid ratio** per query

## Success Criteria

- [ ] FTS5 index created automatically alongside vector index
- [ ] Hybrid search API: `search(query, mode="hybrid", alpha=0.7)` where alpha = semantic weight
- [ ] RRF fusion between FTS5 rank and semantic similarity
- [ ] Query mode: `semantic` | `keyword` | `hybrid` (default: hybrid)
- [ ] No breaking changes to existing `search()` API
- [ ] Benchmark: hybrid outperforms standalone semantic on keyword-heavy queries

## Out of Scope

- Complex query syntax (AND/OR/NOT) — FTS5 supports it, but not exposed in initial API
- Stemming/language-specific tokenization — use FTS5 defaults initially
- Reindexing existing databases — apply to new indexes only (document migration)

## References

- claude-mem: https://github.com/thedotmack/claude-mem (Chroma + FTS5 hybrid)
- SQLite FTS5: https://sqlite.org/fts5.html
- Complementary to: `qmd-inspiration-advanced-ranking` (RRF fusion shared)
