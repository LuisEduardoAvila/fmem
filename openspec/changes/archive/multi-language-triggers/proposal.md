# Proposal: Multi-Language Trigger Detection

> ⚠️ **STATUS: NOT IMPLEMENTED** — This proposal describes multi-language trigger detection which is NOT in the current plugin. The current `openclaw-fmem-auto` plugin uses English-only regex patterns in `triggers.ts`.

## Problem Statement

fmem's current `should_search()` trigger mechanism uses English-only regex patterns, making it ineffective for non-English queries. The user (Luis) works with Portuguese content (Trabalhista project) and needs memory recall to trigger correctly for Portuguese queries like "O que eu disse sobre distrobox?" or "Lembra do caso trabalhista?"

**Why now?** The Trabalhista workspace is actively used, and memory recall misses relevant context when queries are in Portuguese.

## Success Criteria

- [ ] Portuguese queries trigger memory recall correctly
- [ ] English queries continue to work (backward compatible)
- [ ] Entity extraction works across languages (spaCy or equivalent)
- [ ] Performance remains lightweight (<50ms trigger decision)
- [ ] RAM footprint acceptable for Pi (under 50MB for trigger system)
- [ ] Language detection is automatic or configurable

## Out of Scope

- Full machine translation of queries
- Multi-language indexing (content stays in original language)
- Adding new languages beyond EN/PT (but architecture should allow it)
- OpenClaw plugin implementation (this spec is for fmem core; plugin is separate consideration)

## Deployment Architecture

**Key Decision:** Where does trigger detection live?

| Option | Location | Pros | Cons |
|--------|----------|------|------|
| A. fmem Core | `fmem_integration.py` | Works with any client (Pi, Claude Code, Codex) | OpenClaw must call `should_search()` |
| B. OpenClaw Plugin | `openclaw-fmem-plugin` | Auto-injection via hooks, no AGENTS.md needed | Locks fmem to OpenClaw |
| C. Both | Core triggers + Plugin wrapper | Best of both worlds | More code to maintain |

**Recommendation:** Build in **fmem core** first (this spec). Later, create a thin plugin wrapper that:
```python
# openclaw-fmem-plugin
api.on("before_agent_start", async ({ messages }) => {
    from fmem import should_search, auto_recall
    last_message = messages[-1]
    if should_search(last_message):
        memories = auto_recall(last_message)
        # Inject into context
})
```

This keeps fmem **portable** while allowing **automatic integration** when used with OpenClaw.

### OpenClaw Context Engine Hooks Available

| Hook | When It Fires | Use For |
|------|---------------|---------|
| `bootstrap` | Plugin load | Init models |
| `ingest` | Every incoming message | Auto-index |
| `assemble` | Building context for model | Inject memories (RAG) |
| `compact` | Context exceeds limits | Summarization |
| `afterTurn` | Turn completes | Post-processing |
| `prepareSubagentSpawn` | Before sub-agent | Pass scoped context |
| `onSubagentEnded` | Sub-agent done | Index results |

**Target hook for auto-recall:** `assemble` (injects memories before model sees context)

## Notes

Two complementary approaches identified:

| Approach | RAM | Latency | Language Support |
|----------|-----|---------|------------------|
| Regex patterns | ~0MB | <1ms | Per-language sets |
| spaCy entity extraction | ~13-26MB | 5-10ms | Language-agnostic (via models) |

**Recommendation:** Hybrid approach - regex patterns for explicit triggers, spaCy for implicit entity detection. This gives:
- Zero RAM most of the time (regex fast-path)
- Entity fallback when regex doesn't match but content is interesting
- Language model loaded only when needed

**Key Insight:** Entity extraction works across languages:
- "O que eu disse sobre distrobox?" → extracts ["distrobox"]
- "Lembra do caso trabalhista?" → extracts ["caso", "trabalhista"]
- "Any updates on the trabalhista case?" → extracts ["trabalhista", "case"]