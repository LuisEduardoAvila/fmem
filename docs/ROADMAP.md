# fmem Development Roadmap

**Version:** 3.0.0  
**Last Updated:** 2026-02-15  
**Status:** Phase 1 Complete, Phase 2 Active  
**Approach:** C = "Document but Don't Prioritize" for non-critical features

---

## Phase 1: Core Stability ✅ COMPLETE

**Timeline:** 2026-02-12 to 2026-02-15  
**Goal:** Production-ready memory search system

### Deliverables
- [x] FAISS integration with semantic search
- [x] Chunk-level markdown indexing
- [x] Multi-factor ranking (semantic + recency + location)
- [x] SQLite persistence for metadata
- [x] Ollama embedding integration
- [x] CLI interface
- [x] OpenClaw integration module
- [x] Security hardening (path validation, input sanitization)
- [x] Comprehensive documentation
- [x] Test suite (chunking, recency, location)

### Achievements
- ✅ Zero external API costs (100% local)
- ✅ Privacy-focused (no data leaves machine)
- ✅ 57% token reduction with chunk-level indexing
- ✅ Production security review passed

---

## Phase 2: Enhanced Features ✅ MOSTLY COMPLETE

**Timeline:** 2026-02-15 to 2026-02-28  
**Goal:** Improved developer experience and robustness  
**Status:** Option 1 ✅ Done, Option B 🔄 Planned, Option C 📋 Future

### 2.1 AGENTS.md Integration (Option 1) ✅ COMPLETE

**Status:** ✅ **IMPLEMENTED** - Working in Production

**Decision:** Option C approach for BM25 - **document but don't prioritize**
- BM25 hybrid search: Documented in Phase 4.1 (not actively developed)
- Ollama is working well, no urgency to migrate
- QMD provides hybrid if user needs it

---

### 2.2 Automatic Hook (Option B) 🔄 PLANNED

**Status:** 🔄 **PLANNED** - Evaluate after 2 weeks Option 1 usage

**Goal:** True automatic memory without explicit triggers

**What Will Be Implemented:**
- [ ] Create `openclaw_agent_hook.py` module
- [ ] Implement automatic `should_search()` on EVERY message
- [ ] Silent recall (don't mention unless relevant)
- [ ] Token budget management (max 500 tokens injected)
- [ ] Smart relevance filtering (score threshold 0.6+)

**Decision Point:** After 2 weeks of Option 1 usage data  
**Estimated:** 4-6 hours  
**Priority:** Medium (gather data first)

---

### 2.3 Security Hardening ✅ COMPLETE

**Status:** ✅ **COMPLETE** - Score improved from 4/10 to 8/10

**Completed:**
- ✅ SQL injection prevention (path validation)
- ✅ Symlink protection (`is_safe_symlink()`)
- ✅ Rate limiting (`RateLimiter` class)
- ✅ Content validation (`MAX_EMBEDDING_SIZE`)
- ✅ Database indexing (`idx_parent_file`)
- ✅ Memory pressure handling (LRU cache TTL)

---

### 2.4 Documentation ✅ COMPLETE

**Status:** ✅ **COMPLETE** - Installation gaps filled

**Completed:**
- ✅ EXAMPLES.md with workflow demonstrations
- ✅ AGENTS.md integration guide
- ✅ Troubleshooting sections
- ✅ First-time user checklist
- ✅ Clear optional vs required steps

---

### 2.3 Integration Improvements - Option C 📋 PLANNED (MCP)

**Status:** 📋 PLANNED - MCP Wrapper

**Goal:** Universal client support (not just OpenClaw)

**What Will Be Implemented (Phase 3):**
- [ ] TypeScript MCP Server
- [ ] Python bridge subprocess
- [ ] Support for Claude Desktop, VS Code, Cursor
- [ ] Standardized tool registration
- [ ] JSON-RPC protocol implementation

**Benefits:**
- ✅ Works with ANY MCP-compatible client
- ✅ Industry standard protocol
- ✅ Future-proof integration

**Timeline:** March 2026 (2 weeks)  
**Documentation:** See `mcp-wrapper/IMPLEMENTATION.md`

---

### 2.4 Security Hardening 🔴 HIGH PRIORITY

**From Security Review (Score: 4/10 - Critical Issues)**

#### SQL Injection Prevention
**Issue:** Path validation inconsistent

**Tasks:**
- [ ] Add path validation in `_get_chunks_for_file()`
- [ ] Ensure `sanitize_path()` called at all entry points
- [ ] Add security test cases

**Estimated:** 2 hours  
**Dependencies:** None

#### Symlink Protection
**Issue:** `Path.resolve()` follows symlinks

**Tasks:**
- [ ] Implement `is_safe_symlink()` validation
- [ ] Check resolved path is within allowed directories
- [ ] Add tests for symlink attacks

**Estimated:** 2 hours  
**Dependencies:** None

#### Rate Limiting
**Issue:** No Ollama API rate limiting

**Tasks:**
- [ ] Implement `RateLimiter` class
- [ ] Add `max_requests` and `window` parameters
- [ ] Integrate with `_get_embedding()`

**Estimated:** 2 hours  
**Dependencies:** None

#### Content Validation
**Issue:** No size check before embedding

**Tasks:**
- [ ] Validate content size in `add_document()`
- [ ] Add `MAX_EMBEDDING_SIZE` constant
- [ ] Raise error for oversized content

**Estimated:** 1 hour  
**Dependencies:** None

### 2.3 Performance Optimization 🟡 MEDIUM PRIORITY

#### Database Indexing
**Issue:** No index on `parent_file` column

**Tasks:**
- [ ] Add `CREATE INDEX idx_parent_file ON chunks(parent_file)`
- [ ] Benchmark query performance
- [ ] Verify improvement

**Estimated:** 1 hour  
**Dependencies:** None

#### Memory Pressure Handling
**Issue:** LRU cache has no memory monitoring

**Tasks:**
- [ ] Add memory usage checks in `_LRUCache`
- [ ] Implement pressure-based eviction
- [ ] Add `psutil` dependency for monitoring

**Estimated:** 3-4 hours  
**Dependencies:** None

#### Batch Processing
**Issue:** `add_document()` doesn't use batch embeddings

**Tasks:**
- [ ] Refactor to use `_generate_embeddings_batch()`
- [ ] Add progress bars for large batches
- [ ] Optimize batch sizes

**Estimated:** 3-4 hours  
**Dependencies:** None

### 2.4 Testing Expansion 🟡 MEDIUM PRIORITY

**Current Coverage: 6/10 (Insufficient)**

#### Security Tests
**Missing:** Path traversal, SQL injection

**Tasks:**
- [ ] Create `tests/test_security.py`
- [ ] Add path traversal attack cases
- [ ] Add SQL injection vectors
- [ ] Test symlink attacks

**Estimated:** 4-6 hours  
**Dependencies:** Security fixes above

#### Integration Tests
**Missing:** OpenClaw integration, Ollama failures

**Tasks:**
- [ ] Create `tests/test_integration.py`
- [ ] Mock Ollama failures
- [ ] Test `fmem_integration.py` functions
- [ ] Test `enhanced_indexer.py`

**Estimated:** 4-6 hours  
**Dependencies:** OpenClaw agent hook

#### Edge Case Tests
**Missing:** Empty files, corrupted data, network failures

**Tasks:**
- [ ] Empty file handling
- [ ] Corrupted database recovery
- [ ] Network timeout scenarios
- [ ] Concurrent access tests

**Estimated:** 4-6 hours  
**Dependencies:** None

### Phase 2 Milestones

| Milestone | Target Date | Deliverables |
|-----------|-------------|--------------|
| Integration Complete | 2026-02-20 | Agent hook, token management, persistent dedupe |
| Security Hardened | 2026-02-22 | All critical issues fixed, tests passing |
| Performance Optimized | 2026-02-25 | Indexes, memory pressure, batch processing |
| Test Coverage 80%+ | 2026-02-28 | Security, integration, edge case tests |

---

## Phase 3: MCP Wrapper (Future) 📋 PLANNED

**Timeline:** March 2026 (2 weeks)  
**Goal:** Universal client compatibility

### 3.1 MCP Server Development

**Approach:** TypeScript MCP Server + Python Bridge

**Architecture:**
```
MCP Client (any) → MCP Server (TS) → Python Bridge → fmem Core
```

**Tasks:**
- [ ] Set up TypeScript project structure
- [ ] Implement MCP server with SDK
- [ ] Create `search_memory`, `add_document`, `get_status` tools
- [ ] Create Python bridge subprocess
- [ ] Implement JSON-RPC protocol
- [ ] Add resource endpoints (`memory://status`, etc.)
- [ ] Add prompt templates

**Estimated:** 40-60 hours  
**Dependencies:** Phase 2 complete

### 3.2 Multi-Client Support

**Clients to Support:**
- [ ] Claude Desktop (primary)
- [ ] VS Code (Cline extension)
- [ ] Cursor
- [ ] OpenClaw (native MCP)
- [ ] Other MCP-compatible clients

**Tasks:**
- [ ] Test with each client
- [ ] Document client-specific configuration
- [ ] Create setup guides

**Estimated:** 10-15 hours  
**Dependencies:** MCP server complete

### 3.3 MCP Testing & Release

**Tasks:**
- [ ] Unit tests for MCP server
- [ ] Integration tests with Claude Desktop
- [ ] Performance benchmarks (overhead < 20%)
- [ ] Beta release to early adopters
- [ ] Documentation (setup, troubleshooting)
- [ ] Full release

**Estimated:** 20-30 hours  
**Dependencies:** Multi-client support

**Documentation:**
- [MCP RATIONALE](../mcp-wrapper/RATIONALE.md)
- [MCP IMPLEMENTATION](../mcp-wrapper/IMPLEMENTATION.md)

---

## Phase 4: Advanced Features (Future) 📋 BACKLOG

**Timeline:** Q2 2026+  
**Goal:** Enterprise-grade capabilities

**Approach:** C = Document but Don't Prioritize
- Features below are **documented** for awareness
- **Not actively developed** unless critical need arises
- Ollama integration works well - no urgency to replace

---

### 4.1 Hybrid Search (BM25 + Vector) 📋 DOCUMENTED (NOT PRIORITIZED)

**Status:** 📋 **OPTION C** - Documented, not prioritized  
**Rationale:** Current semantic search works well; QMD provides hybrid if needed

**What It Would Add:**
- BM25 full-text search for exact keyword matches
- Hybrid merging: `(vector_weight * vector_score) + (text_weight * bm25_score)`
- Better exact matches: IDs, error strings, code symbols

**Implementation Sketch:**
```python
def hybrid_search(query, top_k=5):
    # Vector results
    vector_hits = faiss_search(query_embedding, top_k*4)
    # BM25 results  
    bm25_hits = sqlite_fts5_search(query, top_k*4)
    # Merge with RRF or weighted sum
    return reciprocal_rank_fusion(vector_hits, bm25_hits)
```

**Why Not Prioritized:**
- ✅ Current semantic search adequate  
- ✅ QMD provides hybrid search if needed
- ⚠️ Requires FTS5 or Whoosh dependency
- ⚠️ Re-indexing required

**Decision:** Keep documented; revisit if exact-match needs arise

---

### 4.2 Reranking 🔄 INVESTIGATE

**Status:** 🔄 **Under Investigation**  
**Rationale:** QMD uses reranking effectively; evaluate for fmem

**What It Would Add:**
- Cross-encoder model for final relevance scoring
- Better ordering than just distance/similarity
- Smaller model (e.g., `ms-marco-MiniLM-L-6-v2`)

**Implementation:**
```python
from sentence_transformers import CrossEncoder

reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

def rerank(query, candidates):
    pairs = [(query, doc) for doc in candidates]
    scores = reranker.predict(pairs)
    return sorted(candidates, key=lambda x: scores[x], reverse=True)
```

**Decision:** 
- Research cross-encoder overhead vs benefit
- Compare with current multi-factor ranking
- Decision: Phase 4.5 if promising

---

### 4.3 Self-Hosted Embeddings (No Ollama) 📋 DOCUMENTED (NOT PRIORITIZED)

**Status:** 📋 **OPTION C** - Documented, not prioritized  
**Rationale:** Ollama works well; migration = re-indexing everything

**What It Would Add:**
- Pure Python/Bun embedding (no Ollama daemon)
- Local GGUF models via `llama-cpp-python` or `node-llama-cpp`
- Self-contained like QMD

**Options:**
1. **sentence-transformers**: `all-MiniLM-L6-v2` (~80MB)
2. **llama-cpp-python**: GGUF models (~0.6GB)

**Why Not Prioritized:**
- ✅ Ollama stable and working
- ✅ No external API costs
- ⚠️ Complete re-indexing required
- ⚠️ New dependencies (sentence-transformers or llama-cpp)

**Decision:** Keep documented; revisit if Ollama issues arise

---

### 4.4 Async Support
- [ ] Async/await API for `search()` and `add_document()`
- [ ] Non-blocking embedding generation
- [ ] Concurrent request handling

### 4.5 Hierarchical Indexing
- [ ] Support for `###` and `####` sub-headings
- [ ] Parent-child chunk relationships
- [ ] Tree-based search traversal

### 4.6 Graph-Based Relationships
- [ ] Cross-document chunk linking
- [ ] Related content suggestions
- [ ] Knowledge graph visualization

### 4.7 Automatic Summarization
- [ ] LLM-based chunk summaries
- [ ] Caching of generated summaries
- [ ] Summary-based search

### 4.8 Plugin Architecture
- [ ] Custom ranking functions
- [ ] Custom chunking strategies
- [ ] Custom embedding providers
- [ ] Hook system for extensions

### 4.9 Enterprise Features
- [ ] Multi-user support with access control
- [ ] Audit logging
- [ ] Backup/restore functionality
- [ ] Clustering for distributed deployment

---

## QMD Comparison & Inspiration

**QMD** is OpenClaw's experimental hybrid memory backend. We use it for inspiration:

| Feature | QMD | fmem Status |
|---------|-----|-------------|
| **Hybrid Search** | BM25 + Vector | 📋 Documented (4.1) |
| **Reranking** | Cross-encoder reranker | 🔄 Investigate (4.2) |
| **Self-hosted** | Local GGUF embeddings | 📋 Documented (4.3) |
| **Auto-indexing** | `qmd update` command | ❌ Manual/cron only |

**Key Difference:**
- QMD = Full-featured, opinionated, automatic
- fmem = Focused, controlled, explicit triggers

**Our Stance:**
- Keep fmem simple and working
- Document advanced features for awareness
- Don't chase feature parity - different use cases
- If user needs QMD features, they can use QMD 😄

---

## Technical Debt Tracking

| Issue | Phase | Priority | Owner |
|-------|-------|----------|-------|
| Monolithic MemoryRetrieval class | 2 | Medium | TBD |
| Global CONFIG singleton | 2 | Low | TBD |
| No async support | 4 | Medium | TBD |
| Cache TTL hardcoded | 2 | Low | TBD |
| No schema migration | 2 | Medium | TBD |
| English-only token estimation | 4 | Low | TBD |

---

## Success Metrics

| Metric | Current | Phase 2 Target | Phase 3 Target |
|--------|---------|----------------|----------------|
| Test Coverage | 35% | 80% | 85% |
| Security Score | 4/10 | 8/10 | 9/10 |
| Performance Score | 6.5/10 | 8/10 | 8/10 |
| Documentation Score | 8.8/10 | 9/10 | 9.5/10 |
| Integration Score | 5/10 | 8/10 | 9/10 |
| **Overall** | **6.7/10** | **8.2/10** | **8.8/10** |

---

## Contribution Guidelines

Want to help with the roadmap?

1. **Pick an issue** from the current phase
2. **Create a branch** from `main`
3. **Submit PR** with tests and documentation
4. **Reference this roadmap** in commit messages

See [CONTRIBUTING.md](../../DarthSpud/CONTRIBUTING.md) for details.

---

## Notes

- **Dates are estimates** - may shift based on priorities
- **Dependencies matter** - complete Phase 2 before Phase 3
- **Security is priority** - all security issues must be fixed before production
- **MCP is future** - don't start until Phase 2 complete and stable

**Maintainer:** Luis Eduardo Avila  
**Last Review:** 2026-02-15
