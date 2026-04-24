# Proposal: Proactive Context Injection

> ⚠️ **STATUS: NOT IMPLEMENTED** — This proposal describes `get_proactive_context()` and `reset_proactive()` which do NOT exist in the current codebase. The current plugin uses `before_prompt_build` hook with `shouldSearch()` trigger detection.

## Problem Statement

fmem has `should_search()` trigger detection and `auto_recall()` retrieval, but both are **reactive** — they require explicit keywords like "remember" or "recall". When the agent doesn't call fmem (human error, missed trigger), relevant context stays dormant.

**Example:** User says "Remember trip to Spain" — "remember" is a trigger, but the agent treated it as an attention keyword, not a system trigger. The `should_search()` pattern matched, but `auto_recall()` was never called.

**Why now?** Context hookers are available in OpenClaw, but fmem doesn't use them yet.

## Success Criteria

- [ ] Proactive injection happens at session start without explicit trigger
- [ ] Reuses existing `auto_recall()` and `format_results()`
- [ ] Deduplication works with existing `_session_recalled` cache
- [ ] No new classes or query builders (reuse what exists)

## Out of Scope

- Multi-language trigger detection (multi-language-triggers spec)
- New query construction (use existing `get_search_bias()`)
- Token budget management (use existing adaptive preview)
- Pi compatibility testing (system already works on Pi)
- OpenClaw plugin (Phase 7 of multi-language-triggers handles this)

## Approach

**Minimal change:**

1. **First message detection** — Add flag to `fmem_integration.py` to track if proactive search has run
2. **Proactive entry point** — Add `get_proactive_context()` that calls existing `auto_recall()` with recency bias
3. **Reuse everything** — Same dedupe cache, same format, same token preview logic

**The ONLY new code:**
```python
# In fmem_integration.py

_proactive_done = False  # Track if proactive ran this session

def get_proactive_context(top_k: int = 3) -> str:
    """
    Get proactive context at session start.
    Uses existing auto_recall() with recency bias.
    """
    global _proactive_done
    if _proactive_done:
        return ""
    
    _proactive_done = True
    
    # Use existing function with recency bias
    results = auto_recall(
        message="recent work current projects",
        top_k=top_k,
        chunk_mode="chunk"
    )
    
    return format_results(results) if results else ""

def reset_proactive():
    """Reset for new session."""
    global _proactive_done
    _proactive_done = False
```

## Notes

- Reuses `auto_recall()` which already has recency/location bias support
- Reuses `format_results()` which already does adaptive preview
- Reuses `_session_recalled` deduplication
- OpenClaw hook integration is in multi-language-triggers Phase 7