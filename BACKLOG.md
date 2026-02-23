# fmem Backlog

Generated from Pi code review (2026-02-20) - Rating: 7.5/10

---

## 🔴 High Priority

### 1. Fix N+1 Query Pattern in Search Results
- **Location:** Search results enhancement
- **Issue:** Inefficient database access pattern
- **Acceptance:** Single query or batched fetch for related data

### 2. Add Comprehensive Test Coverage
- **Priority:** High
- **Focus areas:**
  - Edge cases (empty content, single heading, malformed tables)
  - Error paths (Ollama failures, DB corruption, disk full)
  - Race conditions (concurrent index ops, cache expiration)
  - Boundary conditions (max file size, query length, empty results)

---

## 🟡 Medium Priority

### 3. Refactor Monolithic `fmem.py`
- **Current size:** ~3,130 lines
- **Issue:** Single class doing too much
- **Options:**
  - Extract chunking logic to separate module
  - Split database operations into repository pattern
  - Separate indexing from search concerns

### 4. Standardize Error Handling
- **Issue:** Inconsistent error patterns across codebase
- **Acceptance:** Uniform error handling strategy with consistent patterns

---

## 🟢 Low Priority

### 5. Add More Type Hints
- **Focus:** Function signatures, return types, complex data structures
- **Benefit:** Better IDE support, documentation

### 6. Move Imports to Top of File
- **Issue:** Some imports inside functions
- **Trade-off:** May be intentional for lazy loading / circular imports handling

---

## ⚠️ Design Concerns

### 7. Hybrid Chunking Detection Logic
- **Current behavior:** md2chunks path only if tables detected
- **Issue:** Creates inconsistent behavior (table files = new chunking, non-table = old)
- **Consider:** Always use md2chunks or make detection configurable
- **Impact:** Two code paths to maintain, potential for divergent behavior

---

## 🧪 Test Coverage Gaps Detail

### Edge Cases
- [ ] Empty content files
- [ ] Single heading with no content
- [ ] Malformed markdown tables

### Error Paths
- [ ] Ollama connection failures
- [ ] Database corruption scenarios
- [ ] Disk full conditions

### Race Conditions
- [ ] Concurrent index operations
- [ ] Cache expiration during use

### Boundary Conditions
- [ ] Maximum file size limits
- [ ] Query length limits
- [ ] Empty search results handling

---

## Summary Stats

| Category | Count | Severity |
|----------|-------|----------|
| Bugs | 4 | 2 Medium, 2 Low |
| Security | 1 | Low |
| Performance | 4 | 2 Medium, 2 Low |
| Code Style | 5 | Low |
| Design | 2 | Low |
| Test Coverage | 3 | Medium |

**Overall:** Production-ready with minor issues. Priority is N+1 query fix and comprehensive tests.
