# fmem Development Roadmap

**Version:** 3.2.0  
**Last Updated:** 2026-04-11  
**Status:** Production-stable, plugin phase next

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

---

## Current Phase: OpenClaw Plugin

**Goal:** Make fmem an OpenClaw plugin with trigger-based auto-injection.

### Why
- Current setup requires me (the agent) to explicitly call `memory_search`
- `memory-auto-recall` plugin does blanket injection on every prompt — wasteful on Pi
- fmem already has FAISS (zero API calls) and trigger detection (`should_search()`)
- Just needs wiring into `before_prompt_build` hook

### Design Principles
- **Trigger-based, not blanket** — only inject when content matches patterns
- **Zero API calls** — FAISS search on pre-computed local vectors
- **Broader scope than memory-core** — notes/, projects/, custom dirs
- **Portable** — plugin wraps fmem core, doesn't replace it

### Tasks
- [ ] Create `openclaw-fmem-plugin` package scaffold
- [ ] Implement `before_prompt_build` hook
- [ ] Wire `should_search()` trigger detection into hook
- [ ] Wire FAISS search into hook (reuse existing index)
- [ ] Format and inject results into prompt context
- [ ] Config: maxResults, minScore, minPromptLength, triggerPatterns
- [ ] Test on Pi (latency, accuracy, trigger hit rate)
- [ ] Publish to clawhub.ai

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
| Proactive injection spec | Superseded by this plugin design |

---

## Architecture

```
User message
    ↓
OpenClaw before_prompt_build hook
    ↓
fmem plugin: should_search(message)?
    ↓ yes
FAISS search (local, pre-computed, sub-ms)
    ↓
Format results → inject into prompt
    ↓
Agent sees enriched prompt
```

vs current:

```
User message
    ↓
Agent decides to call memory_search
    ↓
fmem CLI or Python API
    ↓
Agent reads results
```

---

## Review Cadence

**Quarterly** — next review July 2026 or when plugin is complete.