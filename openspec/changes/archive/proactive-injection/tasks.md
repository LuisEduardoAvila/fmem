# Tasks: Proactive Context Injection

> ⚠️ **STATUS: NOT IMPLEMENTED** — These tasks describe planned work for proactive context injection. The current plugin (`openclaw-fmem-auto`) uses `before_prompt_build` hook with `shouldSearch()` trigger detection instead.

## Phase 1: Proactive Entry Point

### 1.1 Add State Flag

- [ ] Add `_proactive_done = False` global flag in `fmem_integration.py`
- [ ] Add `reset_proactive()` function to reset flag

### 1.2 Add Proactive Function

- [ ] Add `get_proactive_context(top_k=3)` function
- [ ] Check `_proactive_done` flag, return "" if already called
- [ ] Set `_proactive_done = True` after first call
- [ ] Call `auto_recall("recent work current projects", top_k=top_k)`
- [ ] Return `format_results(results)` or "" if no results

## Phase 2: Testing

### 2.1 Unit Tests

- [ ] Test: First call returns formatted context
- [ ] Test: Second call returns empty string
- [ ] Test: `reset_proactive()` allows context again
- [ ] Test: Empty index returns empty (no error)
- [ ] Test: Deduplication works with reactive recall (same `_session_recalled` cache)

### 2.2 Integration Tests

- [ ] Test: `get_proactive_context()` chain works end-to-end
- [ ] Test: Results appear in `<retrieved_memory>` format
- [ ] Test: Proactive results are deduplicated against reactive calls

## Phase 3: Documentation

### 3.1 README Updates

- [ ] Document `get_proactive_context()` usage
- [ ] Document `reset_proactive()` for session resets
- [ ] Add example integration code

### 3.2 API Documentation

- [ ] Document function signature
- [ ] Document return format (same as `format_results()`)
- [ ] Document deduplication behavior

## Verification

- [ ] All tests pass: `pytest tests/test_proactive.py`
- [ ] `get_proactive_context()` returns context on first call
- [ ] `get_proactive_context()` returns "" on second call
- [ ] `reset_proactive()` resets state
- [ ] Proactive results deduplicate against reactive calls