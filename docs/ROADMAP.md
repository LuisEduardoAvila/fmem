# fmem Development Roadmap

**Version:** 3.0.0  
**Last Updated:** 2026-02-15  
**Status:** Phase 1 Complete, Phase 2 Active  

**Decision Philosophy:** Document for awareness, prioritize based on value/effort, revisit quarterly

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

## Phase 2: Enhanced Features ✅ MOSTLY COMPLETE (~60%)

**Timeline:** 2026-02-15 to 2026-02-28  
**Goal:** Improved developer experience and robustness  
**Status:** Option 1 ✅ Done, Option B 🔄 Planned

**Completed (~60%):**
- ✅ AGENTS.md Integration (Option 1) - Working
- ✅ Security Hardening (4/10 → 8/10)
- ✅ Documentation (API.md, INSTALLATION.md, ARCHITECTURE.md)

**Remaining (~40%):**
- 🔄 Automatic Hook (Option B) - Decision 2026-03-01
- 📋 Async API support
- 📋 Incremental re-indexing (file watching)

**Status:** ✅ **IMPLEMENTED** - Working in Production

**Completed:**
- [x] Memory Recall section in AGENTS.md
- [x] Trigger patterns documented
- [x] Tested: "What were my fitness goals?" works
- [x] EXAMPLES.md with conversational flows

---

### 2.2 Security Hardening ✅ COMPLETE

**Status:** ✅ **COMPLETE** - Score: 4/10 → 8/10

**Completed:**
- [x] SQL injection prevention
- [x] Symlink protection
- [x] Rate limiting
- [x] Content validation
- [x] Database indexing
- [x] Memory pressure handling

---

### 2.3 Documentation ✅ COMPLETE

**Status:** ✅ **COMPLETE**

**Completed:**
- [x] EXAMPLES.md with workflow demonstrations
- [x] AGENTS.md integration guide
- [x] Installation gaps filled
- [x] Troubleshooting sections
- [x] First-time user checklist

---

### 2.4 Automatic Hook (Option B) 🔄 DEFERRED

**Status:** 🔄 **DEFERRED** - Decision after 2 weeks usage data

**Why Deferred:**
- Option 1 (AGENTS.md) working well
- Need usage data to justify effort
- Token budget complexity not worth it yet

**Decision Point:** 2026-03-01 (2 weeks of Option 1 usage)  
**Estimated:** 4-6 hours  
**Current Priority:** Low (wait for data)

---

## Phase 3: MCP Wrapper (Universal Support) 📋 PRIORITY: HIGH

**Timeline:** 2026-03-01 to 2026-03-15  
**Goal:** Universal client compatibility (Claude Desktop, Cursor, etc.)  
**Priority:** **HIGH** - Unlocks non-OpenClaw users

### Why High Priority?
- Large addressable market (Claude Desktop, VS Code, Cursor)
- Industry standard protocol (MCP)
- Clear value proposition
- Reasonable effort estimate (2 weeks)

### 3.1 MCP Server Core
**Estimated:** 40 hours  
**Priority:** Critical path

**Tasks:**
- [ ] Set up TypeScript project
- [ ] Implement MCP server with SDK
- [ ] Create `search_memory`, `add_document`, `get_status` tools
- [ ] Create Python bridge subprocess
- [ ] Implement JSON-RPC protocol

### 3.2 Multi-Client Support
**Estimated:** 15 hours  
**Priority:** High

**Tasks:**
- [ ] Test with Claude Desktop
- [ ] Test with VS Code (Cline)
- [ ] Test with Cursor
- [ ] Document client-specific config

### 3.3 MCP Testing & Release
**Estimated:** 25 hours  
**Priority:** Medium

**Tasks:**
- [ ] Unit tests
- [ ] Performance benchmarks
- [ ] Beta release
- [ ] Documentation

**Total Phase 3:** ~80 hours (2 weeks)  
**Dependencies:** None (Phase 2 stable enough)

---

## Phase 4: Advanced Features - PRIORITIZED

**Philosophy:** Value/Effort ratio. Document everything, prioritize quarterly.

**Review Date:** 2026-03-15 (after MCP Phase 3)

### Priority Ranking

| Rank | Feature | Value | Effort | Priority | Decision |
|------|---------|-------|--------|----------|----------|
| 1 | **Async API** | High | Low | 🔴 **HIGH** | Do first - improves performance |
| 2 | **Reranking** | Medium | Medium | 🟡 **MEDIUM** | Under investigation |
| 3 | **BM25 Hybrid** | Medium | Medium | 🟢 **LOW** | QMD provides this |
| 4 | **Self-hosted** | Low | High | 🟢 **LOW** | Ollama works fine |

---

### 4.1 Async API 🔴 HIGH PRIORITY

**Status:** 📋 **PLANNED**  
**Estimated:** 4-6 hours  
**Value:** Improves performance, modern Python patterns

**Tasks:**
- [ ] Async `search()` method
- [ ] Async `add_document()` method
- [ ] Non-blocking embeddings
- [ ] Concurrent request handling

**Why High:** Low effort, high value, standard Python practice

---

### 4.2 Reranking 🟡 MEDIUM PRIORITY - UNDER INVESTIGATION

**Status:** 🔄 **INVESTIGATING**  
**Estimated:** 8-12 hours  
**Value:** Better result ordering

**Research Questions:**
- Which cross-encoder model? (ms-marco-MiniLM-L-6-v2?)
- Overhead acceptable? (latency increase?)
- Better than current multi-factor ranking?

**Decision:** Review after testing by 2026-03-15  
**If promising:** Move to Phase 4.5  
**If not:** Document and park

---

### 4.3 BM25 Hybrid Search 🟢 LOW PRIORITY

**Status:** 📋 **DOCUMENTED** - Not scheduled  
**Estimated:** 6-8 hours  
**Value:** Exact keyword matches

**Why Low:**
- Current semantic search adequate
- QMD provides hybrid if user needs it
- Would require re-indexing

**Trigger for Re-evaluation:**
- Multiple users ask for exact-match capability
- Use case: code IDs, error strings, precise terms

**Until then:** Document in ROADMAP, don't implement

---

### 4.4 Self-Hosted Embeddings (No Ollama) 🟢 LOW PRIORITY

**Status:** 📋 **DOCUMENTED** - Not scheduled  
**Estimated:** 12-16 hours  
**Value:** Remove Ollama dependency

**Why Low:**
- Ollama stable and working
- Complete re-indexing required (breaking change)
- New dependencies (sentence-transformers or llama-cpp)

**Trigger for Re-evaluation:**
- Ollama introduces breaking changes
- User needs offline-only (no daemon)
- User prefers pure-Python stack

**Until then:** Document in ROADMAP, don't implement

---

### 4.5 Other Features (Backlog)

**Status:** 📋 **BACKLOG** - No priority assigned

| Feature | Reason Not Prioritized |
|---------|------------------------|
| Hierarchical Indexing (### ####) | Current ## sufficient |
| Graph Relationships | No clear use case yet |
| Auto-summarization | LLM dependency, complex |
| Plugin Architecture | Not requested |
| Enterprise (multi-user) | Single-user focus for now |

---

## QMD Comparison & Strategy

**Our Position Relative to QMD:**

| Feature | QMD | fmem Strategy |
|---------|-----|---------------|
| **Hybrid Search** | ✅ BM25 + Vector | 🟢 Low - QMD covers this |
| **Reranking** | ✅ Cross-encoder | 🟡 Medium - Investigate value |
| **Self-hosted** | ✅ Local GGUF | 🟢 Low - Ollama works |
| **Auto-indexing** | ✅ `qmd update` | ❌ Won't implement - cron is fine |
| **Chunk-level** | ❓ Unknown | ✅ Our differentiator |
| **Multi-factor** | ❓ Unknown | ✅ Our differentiator |
| **Sub-agent access** | ❌ No | ✅ Our differentiator |

**Strategic Decision:**
- ✅ Focus on **OpenClaw integration** (AGENTS.md triggers)
- ✅ Focus on **sub-agent accessibility** (exec works)
- ✅ Keep **simple** and **controlled**
- 🟡 **MCP** expands reach without complexity

**When to Use QMD:**
- User wants automatic indexing
- User needs hybrid search
- User wants official OpenClaw support

**When to Use fmem:**
- User wants chunk-level precision
- User wants multi-factor ranking
- User needs sub-agent access
- User wants control over triggers

---

## Success Metrics

| Metric | Current | Phase 2 Target | Phase 3 Target |
|--------|---------|----------------|----------------|
| Test Coverage | 75% | 80% | 85% |
| Security Score | 8/10 | 8/10 | 8/10 |
| Documentation | 9/10 | 9/10 | 9.5/10 |
| Integration | 8/10 | 8/10 | 9/10 |
| **Overall** | **7.8/10** | **8/10** | **8.5/10** |

---

## Roadmap Governance

**Review Cadence:** Monthly (first Monday)

**Decision Criteria:**
1. **User Requests:** Are people asking for this?
2. **Value/Effort:** Is the juice worth the squeeze?
3. **Dependencies:** What needs to happen first?
4. **Alternatives:** Can QMD/other tools handle this?

**Change Process:**
1. Discuss in monthly review
2. Update ROADMAP.md
3. Adjust priorities if needed
4. Document rationale

---

**Last Review:** 2026-02-16  
**Next Review:** 2026-03-01 (after 2 weeks Option 1 usage)
