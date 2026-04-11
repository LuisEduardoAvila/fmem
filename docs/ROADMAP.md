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

### Positioning
**Low-cost alternative to Active Memory** for resource-constrained environments:

| | Active Memory | fmem Plugin |
|---|---|---|
| Trigger | Every prompt | Pattern-matched only |
| Embedding | API call per prompt (OpenRouter/OpenAI) | Local FAISS (zero API calls) |
| Latency | ~200-500ms per prompt | ~50ms only when triggered |
| Scope | memory-core (MEMORY.md + memory/) | memory/ + notes/ + projects/ + custom |
| Pi-friendly | ❌ (API calls + latency) | ✅ (local search, zero network) |
| Ideal for | Cloud deployments, unlimited budget | Self-hosted, Pi, privacy-first |

### Design Principles
- **Trigger-based, not blanket** — only inject when content matches patterns
- **Zero API calls** — FAISS search on pre-computed local vectors
- **Broader scope than memory-core** — notes/, projects/, custom dirs
- **Portable** — plugin wraps fmem core, doesn't replace it

### Plugin Architecture

**Hook:** `api.on("before_prompt_build", ...)` — same hook used by Active Memory plugin

**Reference implementations:**
- Built-in: `dist/extensions/active-memory/index.js` — uses `api.on("before_prompt_build")` for recall before agent sees context
- Community: `openclaw-memory-auto-recall` — simpler pattern, calls memory-core search then prepends results
- Plugin SDK: https://docs.openclaw.ai/plugins/building-plugins
- Entry points: https://docs.openclaw.ai/plugins/sdk-entrypoints
- Hook API: `api.on(eventName, handler)` with event names from SDK overview

**Plugin structure:**
```
openclaw-fmem/
├── openclaw.plugin.json      # Manifest (id, name, configSchema)
├── package.json               # With openclaw.extensions + compat fields
├── src/
│   └── index.ts               # definePluginEntry + register hook
└── tsconfig.json
```

**Key SDK imports:**
- `openclaw/plugin-sdk/plugin-entry` → `definePluginEntry`
- `openclaw/plugin-sdk/config-schema` → `OpenClawSchema` for config validation

**Config schema** (in `openclaw.plugin.json`):
```json
{
  "id": "fmem",
  "name": "fmem",
  "description": "Trigger-based memory injection via FAISS",
  "configSchema": {
    "type": "object",
    "properties": {
      "maxResults": { "type": "integer", "default": 3 },
      "minScore": { "type": "number", "default": 0.3 },
      "minPromptLength": { "type": "integer", "default": 10 },
      "triggerPatterns": { "type": "array", "items": { "type": "string" } }
    },
    "additionalProperties": false
  }
}
```

**Data flow:**
```
User message
    ↓
before_prompt_build hook fires
    ↓
Plugin: should_search(message)?
    ↓ yes
FAISS search (local, pre-computed, sub-ms)
    ↓
Format results → return { prepend: [content blocks] }
    ↓
Agent sees enriched prompt
```

**Bridge to fmem Python:** The plugin runs in Node.js but fmem is Python. Options:
1. **Subprocess** — `python3 -m fmem search "query" --top-k 3 --format json` (simplest, ~50ms)
2. **HTTP bridge** — fmem starts a lightweight HTTP server, plugin calls it (faster, more complex)
3. **Shared SQLite** — Plugin reads fmem's SQLite+FAISS directly from Node.js (no Python needed, but needs faiss-node)

Recommendation: Start with subprocess (proven pattern, fmem CLI already exists), benchmark on Pi, then optimize if needed.

### Tasks
- [ ] Create `openclaw-fmem` plugin scaffold (openclaw.plugin.json + package.json + src/index.ts)
- [ ] Implement `before_prompt_build` hook with trigger detection
- [ ] Bridge to fmem: subprocess call to `fmem search`
- [ ] Format and inject results into prompt context (return `{ prepend }` blocks)
- [ ] Config: maxResults, minScore, minPromptLength, triggerPatterns
- [ ] Test on Pi (latency, accuracy, trigger hit rate)
- [ ] Publish to clawhub.ai

### Reference Docs
- Plugin building: https://docs.openclaw.ai/plugins/building-plugins
- Plugin SDK overview: https://docs.openclaw.ai/plugins/sdk-overview
- Entry points: https://docs.openclaw.ai/plugins/sdk-entrypoints
- Active Memory plugin source: `dist/extensions/active-memory/index.js` (bundled)
- Community auto-recall plugin: https://github.com/code-yeongyu/openclaw-memory-auto-recall

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
Plugin: should_search(message)?
    ↓ yes
fmem CLI subprocess (python3 -m fmem search)
    ↓
FAISS search (local, pre-computed, sub-ms)
    ↓
Return { prepend: [content blocks] }
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