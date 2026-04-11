# fmem Backlog

**Last Updated:** 2026-04-11  
**Previous backlog archived** — most items were fixed, superseded, or no longer relevant.

---

## 🔴 High Priority

### 1. OpenClaw Plugin: Trigger-Based Auto-Injection

**Goal:** Build fmem into an OpenClaw plugin that injects relevant memory context before the agent sees the prompt — but only when triggers are detected in the incoming message.

**Why:** Current `should_search()` trigger detection works but requires me (the agent) to explicitly call `memory_search`. A plugin using `before_prompt_build` hook would automate this with zero API calls (FAISS search on pre-computed local vectors).

**Architecture:**
- Hook: `before_prompt_build` (same as Active Memory plugin)
- Trigger detection: Reuse `should_search()` patterns from fmem_integration.py
- Search: FAISS IndexFlatIP on pre-computed embeddings (sub-ms, no API call)
- Injection: Format results into context block, prepend to prompt
- Scope: memory/ + notes/ + projects/ + custom dirs (broader than memory-core)

**Key difference from `memory-auto-recall` plugin:**
- Trigger-based, not blanket (no injection on "hi", "ok", etc.)
- Uses fmem's FAISS index (zero API calls, Pi-friendly)
- Broader scope (notes/, projects/, custom dirs)

**Reference:** `openspec/changes/proactive-injection/` and `multi-language-triggers/` have prior design work.

---

## 🟡 Medium Priority

### 2. Further Split fmem.py (1,286 lines → <500)

**Current state:** fmem.py was refactored from ~3,130 → 1,286 lines with 9 service modules extracted. Still the largest file at 48KB.

**Why now:** Plugin work will be easier if the core module is smaller and has clear interfaces.

**Targets for extraction:**
- Session/recall management → `session_service.py`
- Configuration loading → merge into `config.py`
- CLI argument handling → already in `cli.py`, check for residue

---

## 🟢 Low Priority

### 3. Test Coverage Gaps

**Current state:** 17 tests across 3 files (428 lines). Core search and indexing work well.

**Gaps:**
- Edge cases (empty content, single heading, malformed tables)
- Error paths (Ollama failures, DB corruption, disk full)
- Boundary conditions (max file size, query length, empty results)

**Why low:** fmem is production-stable. These are hardening, not features.