# Specification: Proactive Context Injection

> ⚠️ **STATUS: NOT IMPLEMENTED** — This specification describes `get_proactive_context()` and `reset_proactive()`, which do not exist in the current codebase. The current plugin uses `before_prompt_build` hook with `shouldSearch()` trigger detection instead.

## Requirements

### REQ-001: Proactive Entry Point
**As a** session  
**I want** context loaded automatically at start  
**So that** relevant memories are available without explicit trigger

#### Scenarios

##### SC-001: First Call Returns Proactive Context
**Given** a new session starts  
**When** `get_proactive_context()` is called  
**Then** `auto_recall()` is called with recency bias  
**And** formatted results are returned  
**And** subsequent calls return empty string

##### SC-002: Reset Allows Proactive Again
**Given** proactive context was returned  
**When** `reset_proactive()` is called  
**Then** next call to `get_proactive_context()` returns context again

**Edge Cases:**
- Empty index → returns empty string (graceful degradation)
- Embedding service unavailable → returns empty string, logs warning

---

### REQ-002: Reuse Existing Functions
**As a** developer  
**I want** proactive injection to reuse existing code  
**So that** there's minimal new code to maintain

#### Implementation

```python
# fmem_integration.py additions

_proactive_done = False

def get_proactive_context(top_k: int = 3) -> str:
    """
    Get proactive context at session start.
    Calls existing auto_recall() with recency bias.
    
    Args:
        top_k: Number of results (default 3)
        
    Returns:
        Formatted context string (empty if already called or no results)
    """
    global _proactive_done
    if _proactive_done:
        return ""
    
    _proactive_done = True
    
    # Reuse existing auto_recall with recency bias
    # (get_search_bias() will detect "recent" and boost recency)
    results = auto_recall(
        message="recent work current projects",
        top_k=top_k,
        chunk_mode="chunk"
    )
    
    # Reuse existing format_results
    return format_results(results) if results else ""

def reset_proactive() -> None:
    """Reset proactive state for new session."""
    global _proactive_done
    _proactive_done = False
```

**What's reused:**
- `auto_recall()` — message parsing, search, deduplication
- `get_search_bias()` — detects "recent" → boosts recency weight
- `format_results()` — adaptive preview, `<retrieved_memory>` tag
- `_session_recalled` — deduplication across proactive + reactive

---

### REQ-003: Integration Point
**As a** OpenClaw integration  
**I want** a function to call at session start  
**So that** proactive context is injected before first response

#### Scenarios

##### SC-003: Called Once Per Session
**Given** OpenClaw session starts  
**When** `assemble` hook fires  
**Then** call `get_proactive_context()` once  
**And** inject result into context  
**And** subsequent calls return empty

##### SC-004: Compacted Session Resets
**Given** session was compacted  
**When** session restarts  
**Then** call `reset_proactive()`  
**And** next `get_proactive_context()` returns context

**Note:** OpenClaw plugin implementation is in multi-language-triggers Phase 7. This spec only provides the `get_proactive_context()` entry point.

---

## Test Cases

### Unit Tests

- [ ] First call returns formatted context
- [ ] Second call returns empty string
- [ ] `reset_proactive()` allows context again
- [ ] Empty index returns empty (no error)
- [ ] Deduplication works with reactive recall

### Integration Tests

- [ ] `get_proactive_context()` → `auto_recall()` → `format_results()` chain works
- [ ] Results are deduplicated against later reactive calls