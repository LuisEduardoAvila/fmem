# fmem Development Roadmap

**Version:** 3.2.0  
**Last Updated:** 2026-04-22  
**Status:** Production-stable, plugin complete

---

## Completed Phases

### Phase 1: Core Stability ✅ (2026-02-12 → 02-15)
- FAISS integration with semantic search
- Chunk-level markdown indexing
- Multi-factor ranking (semantic + recency + location)
- SQLite persistence, Ollama embeddings, CLI interface

### Phase 2: Enhanced Features ✅ (2026-02-15 → 03-01)
- AGENTS.md integration with trigger patterns
- Security hardening (4/10 → 8/10)
- Documentation (API, architecture, installation, examples)
- Code refactoring (3,130 → 1,286 lines in fmem.py, 9 service modules)

### Phase 3: Production Hardening ✅ (2026-03 → 04)
- Incremental indexing via cron (every 3h)
- Heading-aware chunking (## sections)
- Broad scope: memory/ + notes/ + projects/ + trips/ + custom dirs
- N+1 query fix (batch operations)
- 17 tests covering core functionality

### Phase 4: OpenClaw Plugin ✅ (2026-04-22)
- **Plugin:** `openclaw-fmem-auto` v1.0.0 — trigger-based auto-recall via `before_prompt_build` hook
- **Runtime:** Uses `@openclaw/plugin-sdk/process-runtime` for `runExec` (subprocess bridge to fmem Python CLI)
- **Features:** Trigger-based auto-recall, session deduplication (no duplicate injections per session), rate limiting
- **Hook:** `before_prompt_build` — same hook as Active Memory, but only fires when content matches trigger patterns
- **CLI enhancements:** `--format json`, `--min-score`, `--max-content`, `--content-mode` (adaptive score-based truncation)
- **Positioning:** Low-cost Pi-friendly alternative to Active Memory (zero API calls, ~50ms latency only when triggered)
- **6 pre-existing test failures** fixed in test_fmem.py

---

## Future Roadmap

### Remaining Plugin Tasks
- [ ] Publish to clawhub.ai
- [ ] Test on Pi (latency, accuracy, trigger hit rate) — real-world validation

### Technical Debt
- [ ] **Refactor adaptive truncation** — `format_results()` in `fmem_integration.py` and `cmd_search()` in `cli.py` duplicate truncation logic (base limits: 400/250/150 by result count). Extract into shared utility in `fmem/truncation.py` with both callers importing from it.

### Potential Future Enhancements
- HTTP bridge instead of subprocess (lower latency, but more complex)
- Shared SQLite + faiss-node (zero Python dependency, but needs faiss-node binding)
- Config UI for triggerPatterns, maxResults, minScore, minPromptLength

---

## Dropped Items

These were in the previous roadmap. Dropped because:

| Item | Why Dropped |
|------|-------------|
| MCP Server | memory-core now has MCP-like search; plugin approach is better |
| Async API | fmem isn't a web service; cron + CLI is fine |
| Reranking (cross-encoder) | Overhead on Pi not worth it |
| BM25 Hybrid Search | memory-core does hybrid search now |
| Self-hosted embeddings | Ollama works fine, no need to replace |
| Query Expansion Service | LLM call per query on Pi = bad idea |
| Multi-language triggers | Nice-to-have, spaCy overhead on Pi |
| Proactive injection spec | Superseded by plugin design |

---

## Architecture

```
User message
    ↓
OpenClaw before_prompt_build hook
    ↓
Plugin: should_search(message)?
    ↓ yes
fmem CLI subprocess via runExec (python3 -m fmem search)
    ↓
FAISS search (local, pre-computed, sub-ms)
    ↓
Return { prepend: [content blocks] }
    ↓
Agent sees enriched prompt
```

---

## Review Cadence

**Quarterly** — next review July 2026.