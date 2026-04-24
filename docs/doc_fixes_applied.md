# Documentation Fixes Applied

**Date:** 2026-04-24  
**Task:** Documentation consistency check — align all markdown with actual plugin implementation  
**Source of truth:** `plugins/openclaw-fmem-auto/src/` (index.ts, types.ts, triggers.ts, formatter.ts, fmem-client.ts)

---

## Summary

| Severity | Count |
|----------|-------|
| High     | 6     |
| Medium   | 7     |
| Low      | 5     |

**18 files edited**, 0 files rewritten (all changes were surgical).

---

## Files Edited

### 1. `plugins/README.md` — 5 changes

| # | Change | Severity |
|---|--------|----------|
| 1 | Fixed `timeoutMs` default: `500` → `5000` (YAML example + config table) | High |
| 2 | Fixed trigger descriptions to match actual regex patterns in `triggers.ts`: Explicit ("direct mention" → "user directly asks"), Recency ("recently stored memories surface automatically" → "user references time periods"), Location ("memories tagged with relevant locations" → "user mentions a directory, path, or location category"), Context ("semantic similarity" → "user references personal context patterns") | High |
| 3 | Added "Custom Triggers" section documenting `config.triggers` override capability | Medium |
| 4 | Added message length limit (10,000 chars) and content preview limits (150/400 chars) to Deduplication & Rate Limiting section | Medium |
| 5 | Fixed installation steps: clarified `openclaw plugin install fmem-auto`, OpenClaw loads TS directly (no build step), config file path | Low |

### 2. `README.md` (main project) — 10 changes

| # | Change | Severity |
|---|--------|----------|
| 1 | Fixed trigger type examples: "remember/recall/what about" → "look up/recall/remember/show me"; Location "fitness/movies/work" → "in docs/under projects/from memory/"; Context "we discussed" → "workspace" | Medium |
| 2 | Added `gracefulDegradation` to plugin configuration table | Medium |
| 3 | Removed `About this file: {precomputed_summary} | {dynamic_stats}` from injection format documentation (not in TypeScript formatter) | Medium |
| 4 | Removed `About this file:` lines from the example injection block (both entries) | Medium |
| 5 | Fixed plugin config YAML format: list entry (`- name: fmem-auto`) → map-key format (`fmem-auto:`) matching `openclaw.plugin.json` | High |
| 6 | Clarified `auto_recall()` as "Python integration function (for AGENTS.md triggers)" instead of "Legacy OpenClaw integration function" | Medium |
| 7 | Aligned Development Roadmap with ROADMAP.md: Phase 3 = Production Hardening ✅, Phase 4 = OpenClaw Plugin ✅, Phase 5 = Advanced Features (Planned). Previously Phase 2 listed "OpenClaw plugin" but Phase 3 was MCP Wrapper (Planned) and Phase 4 was Advanced Features (Planned) — misaligned with actual completion status. | High |
| 8 | Added "Custom Triggers" section with YAML example for overriding trigger patterns | Medium |
| 9 | Fixed "Document Type + Location Context" bullet wording | Low |
| 10 | Version already correct (3.3.0), no change needed | — |

### 3. `BACKLOG.md` — 1 change

| # | Change | Severity |
|---|--------|----------|
| 1 | Marked "OpenClaw Plugin: Trigger-Based Auto-Injection" as ✅ Completed (2026-04-22). Previously listed as High Priority active item despite being shipped. | High |

### 4. `docs/ROADMAP.md` — 1 change

| # | Change | Severity |
|---|--------|----------|
| 1 | Updated version: `3.2.0` → `3.3.0`, date to `2026-04-24`, to align with README version | Low |

### 5. `docs/review_core_module.md` — 1 change

| # | Change | Severity |
|---|--------|----------|
| 1 | Fixed "Plugin architecture ❌ Not implemented, Phase 4 planned" → "✅ Implemented (Phase 4), openclaw-fmem-auto v1.0.0 shipped 2026-04-22" | High |

### 6. `docs/INTEGRATION_FLOW.md` — 1 change

| # | Change | Severity |
|---|--------|----------|
| 1 | Fixed "before the LLM prompt is assembled" → "via the `before_prompt_build` hook" (avoiding "assembled" terminology from the old `assemble` hook proposal) | Low |

### 7. `docs/ARCHITECTURE.md` — 2 changes

| # | Change | Severity |
|---|--------|----------|
| 1 | Fixed "before the LLM prompt is assembled" → "before the LLM prompt is built" | Low |
| 2 | Fixed "OpenClaw assembles" → "OpenClaw builds" in architecture diagram | Low |

### 8. `docs/doc_audit_findings.md` — 1 change

| # | Change | Severity |
|---|--------|----------|
| 1 | Added Fix Date and reference to `doc_fixes_applied.md` at top | Low |

### 9. `CONTRIBUTING.md` — 1 change

| # | Change | Severity |
|---|--------|----------|
| 1 | Added TypeScript plugin typecheck testing note (`npm run typecheck` in `plugins/openclaw-fmem-auto/`) | Low |

### 10. `REF_PLAN.md` — 1 change

| # | Change | Severity |
|---|--------|----------|
| 1 | Added status banner noting the refactoring was completed (fmem.py reduced from ~3,130 to ~1,286 lines with 9 service modules) | Low |

### 11–18. Archived design/spec documents — Status banners added

| File | Banner Added |
|------|-------------|
| `openspec/changes/archive/multi-language-triggers/design.md` | ⚠️ NOT IMPLEMENTED — current plugin uses English-only regex in triggers.ts |
| `openspec/changes/archive/multi-language-triggers/specs/triggers/spec.md` | ⚠️ NOT IMPLEMENTED — spec only, current plugin uses English-only regex |
| `openspec/changes/archive/multi-language-triggers/proposal.md` | ⚠️ NOT IMPLEMENTED — proposal only |
| `openspec/changes/archive/multi-language-triggers/tasks.md` | ⚠️ NOT IMPLEMENTED — tasks for planned feature |
| `openspec/changes/archive/proactive-injection/specs/injection/spec.md` | ⚠️ NOT IMPLEMENTED — get_proactive_context() doesn't exist |
| `openspec/changes/archive/proactive-injection/proposal.md` | ⚠️ NOT IMPLEMENTED — proactive injection not implemented |
| `openspec/changes/archive/proactive-injection/tasks.md` | ⚠️ NOT IMPLEMENTED — tasks for planned feature |
| `notes/fmem-implicit-triggers.md` | ⚠️ NOT IMPLEMENTED — planning document, only shouldSearch() exists |

---

## Issues NOT Fixed (intentional)

| Issue | Reason |
|-------|--------|
| `interrogative` trigger type in archived multi-language-triggers docs | These are archived design proposals (in `archive/`), not current documentation. Status banners added instead of content edits. |
| `assemble` hook references in archived proactive-injection docs | Same — archived proposals. Status banners added. |
| `review_core_module.md` — other "Phase 4 planned" items (cross-document relationships, hierarchical indexing, etc.) | These remain accurate — those features ARE still not implemented. Only "Plugin architecture" was wrong. |
| Hardcoded "Luis" in `triggers.ts` DEFAULT_TRIGGERS | Code change, not documentation. Noted in audit but not in scope. |
| `doc_fixes_summary.md` (Feb 2026) | Historical record — not updated. |

---

## Verification Checklist

- [x] All `timeoutMs` references match code default (5000ms)
- [x] All hook names reference `before_prompt_build` (not `assemble` or `on_prompt`)
- [x] All trigger type descriptions match actual regex behavior in `triggers.ts`
- [x] No `interrogative` trigger type claimed as implemented
- [x] No `get_proactive_context()` or `reset_proactive()` claimed as implemented
- [x] No implicit triggers / entity extraction claimed as implemented
- [x] Plugin config format uses map-key format (not list entry)
- [x] `gracefulDegradation` documented in both README.md and plugins/README.md
- [x] Custom trigger overrides documented
- [x] Context injection format matches actual `formatter.ts` output (no `About this file:` line)
- [x] Development roadmap phases aligned with ROADMAP.md
- [x] BACKLOG.md plugin item marked complete
- [x] Archived design docs have NOT IMPLEMENTED status banners