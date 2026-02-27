# Tasks: Hybrid Search (Semantic + FTS5)

## Phase 1: Foundation (Day 1)

### Database Layer
- [ ] **Task 1.1**: Create FTS5 virtual table schema
  - File: `src/fmem/database_service.py`
  - Add `chunk_fts` virtual table creation
  - Add trigger creation for sync
  - Estimated: 2 hours

- [ ] **Task 1.2**: Add FTS5 migration for existing databases
  - File: `src/fmem/database_service.py`
  - One-time migration function
  - Populate FTS5 from existing chunks
  - Estimated: 1.5 hours

- [ ] **Task 1.3**: Test FTS5 availability detection
  - File: `src/fmem/utils.py`
  - Check SQLite version (need 3.9.0+)
  - Test FTS5 pragma support
  - Estimated: 1 hour

### FTS5IndexService
- [ ] **Task 1.4**: Implement FTS5IndexService class
  - File: `src/fmem/fts5_service.py` (new)
  - `search()` method with BM25 ranking
  - `index_chunk()` method
  - `delete_chunk()` method
  - Estimated: 3 hours

- [ ] **Task 1.5**: Add FTS5 triggers for automatic sync
  - File: `src/fmem/database_service.py`
  - INSERT trigger
  - UPDATE trigger  
  - DELETE trigger
  - Estimated: 1 hour

**Phase 1 Total: ~8.5 hours**

---

## Phase 2: Search Enhancement (Day 2)

### SearchIndex Integration
- [ ] **Task 2.1**: Add hybrid search modes to SearchIndex
  - File: `src/fmem/search_index.py`
  - `_search_keyword()` method
  - `_search_hybrid()` method with RRF
  - Update `search()` to accept mode parameter
  - Estimated: 3 hours

- [ ] **Task 2.2**: Implement weighted RRF fusion
  - File: `src/fmem/search_index.py`
  - Alpha-weighted semantic vs keyword
  - Shared with Advanced Ranking proposal
  - Estimated: 1.5 hours

- [ ] **Task 2.3**: Add search mode configuration
  - File: `src/fmem/config.py`
  - `default_mode` setting
  - `hybrid_alpha` setting
  - `rrf_k` setting
  - Estimated: 1 hour

### MemoryRetrieval Updates
- [ ] **Task 2.4**: Expose hybrid search in public API
  - File: `src/fmem/memory_retrieval.py`
  - Add mode parameter to `search()`
  - Add `search_keyword()` convenience method
  - Update docstrings
  - Estimated: 1.5 hours

- [ ] **Task 2.5**: Update auto_recall to use hybrid mode
  - File: `src/fmem/memory_retrieval.py`
  - Default to hybrid when appropriate
  - Keep semantic default for compatibility
  - Estimated: 0.5 hours

**Phase 2 Total: ~7.5 hours**

---

## Phase 3: Integration & Testing (Day 3)

### Testing
- [ ] **Task 3.1**: Write FTS5 unit tests
  - File: `tests/test_fts5.py` (new)
  - Test keyword search
  - Test edge cases (empty content, special chars)
  - Test trigger sync
  - Estimated: 2 hours

- [ ] **Task 3.2**: Write hybrid search tests
  - File: `tests/test_hybrid_search.py` (new)
  - Test RRF fusion correctness
  - Test alpha weighting
  - Test mode switching
  - Estimated: 2 hours

- [ ] **Task 3.3**: Benchmark hybrid vs semantic
  - File: `benchmarks/hybrid_benchmark.py`
  - Create test corpus with technical terms
  - Measure precision/recall
  - Document results
  - Estimated: 2 hours

- [ ] **Task 3.4**: Migration testing
  - Test on existing fmem database
  - Verify FTS5 population
  - Check no data loss
  - Estimated: 1 hour

### Documentation
- [ ] **Task 3.5**: Update API.md with hybrid search
  - Document new modes
  - Add configuration examples
  - Estimated: 1 hour

- [ ] **Task 3.6**: Update README.md
  - Mention hybrid search feature
  - Add usage example
  - Estimated: 0.5 hours

**Phase 3 Total: ~8.5 hours**

---

## Phase 4: Optimization (Optional - Day 4)

### Performance
- [ ] **Task 4.1**: Add FTS5 index optimization
  - `INSERT INTO chunk_fts(chunk_fts) VALUES('optimize')`
  - Run periodically or on demand
  - Estimated: 1 hour

- [ ] **Task 4.2**: Parallel search execution
  - Run semantic and keyword queries concurrently
  - Use asyncio or threading
  - Estimated: 2 hours

- [ ] **Task 4.3**: Query result caching
  - Cache FTS5 results for identical queries
  - TTL-based expiration
  - Estimated: 2 hours

**Phase 4 Total: ~5 hours (optional)**

---

## Summary

| Phase | Hours | Deliverables |
|-------|-------|--------------|
| Phase 1: Foundation | 8.5h | FTS5 table, triggers, FTS5IndexService |
| Phase 2: Integration | 7.5h | Hybrid search API, config, RRF fusion |
| Phase 3: Testing | 8.5h | Tests, benchmarks, documentation |
| Phase 4: Optimization | 5h | (Optional) Caching, parallel search |
| **Total (required)** | **24.5h** | **~3 days** |
| **Total (with optional)** | **29.5h** | **~4 days** |

---

## Dependencies

- **Blocks:** None (standalone feature)
- **Blocked by:** None
- **Related to:** 
  - `qmd-inspiration-advanced-ranking` (shares RRF fusion logic)
  - Can share RRF implementation between proposals

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| SQLite without FTS5 | Low | High | Check at startup, graceful fallback |
| Migration too slow | Medium | Medium | Run async, show progress bar |
| API breaking changes | Low | High | Comprehensive tests for backward compat |

---

## Acceptance Criteria

- [ ] All Phase 1-3 tasks complete
- [ ] Tests pass (`pytest tests/test_fts5.py tests/test_hybrid_search.py`)
- [ ] Benchmark shows >20% improvement on technical keyword queries
- [ ] No breaking changes to existing `search()` behavior
- [ ] Documentation updated (API.md, README.md)
- [ ] Migration tested on existing database

---

## Notes

- FTS5 is **built into SQLite since 3.9.0** (2015) — widely available
- No new Python dependencies required
- RRF fusion logic can be shared with `qmd-inspiration-advanced-ranking` proposal
- Consider extracting RRF to shared utility module if both proposals implemented
