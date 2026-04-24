# fmem Documentation Audit Findings

**Audit Date:** 2026-04-24  
**Auditor:** Subagent (fmem-doc-audit)  
**Fix Date:** 2026-04-24  
**Scope:** Plugin source code vs. all project documentation + design docs

> **Note:** Many findings in this audit have been addressed. See `doc_fixes_applied.md` for the changes made.

---

## Summary

| Severity | Count |
|----------|-------|
| High     | 5     |
| Medium   | 7     |
| Low      | 6     |

**Key themes:**
1. **Default value mismatch:** `timeoutMs` default is 5000ms in code but documented as 500ms in plugins/README.md
2. **Undocumented features:** Custom trigger overrides via config, `gracefulDegradation` config option, `maxPreview` formatter parameter
3. **Unimplemented features documented as current:** Multi-language triggers, entity extraction, implicit triggers, proactive injection (`get_proactive_context()`)
4. **Outdated API references:** Documentation references Python `should_search()` and `auto_recall()` as current integration, but the plugin uses TypeScript reimplementations
5. **Config structure mismatch:** Main README shows plugin config under a list entry format; actual plugin uses map-key format matching `openclaw.plugin.json`

---

## Detailed Findings

---

### 1. timeoutMs Default Mismatch

- **File:** `plugins/README.md`
- **Section:** Configuration table
- **Claim:** `timeoutMs` default is `500`
- **Reality:** Code default is `5000` (see `fmem-client.ts` line `const timeoutMs = config?.timeoutMs ?? 5000;` and `openclaw.plugin.json` `"default": 5000`)
- **Severity:** **High**
- **Suggested fix:** Change the default value in the plugins/README.md configuration table from `500` to `5000`. Also fix the YAML example which shows `timeoutMs: 500` → `timeoutMs: 5000`.

---

### 2. timeoutMs Default Mismatch (Main README)

- **File:** `README.md` (main project)
- **Section:** OpenClaw Plugin → Plugin Configuration table
- **Claim:** `timeoutMs` default is `5000` (correct) BUT the YAML example shows `timeoutMs: 5000` which is correct
- **Reality:** The main README has the correct default (5000), but the plugins/README.md has the wrong one (500). The main README is internally consistent.
- **Severity:** **Low** (main README is correct; inconsistency is in plugins/README.md)
- **Suggested fix:** No change needed in main README. Fix plugins/README.md as per finding #1.

---

### 3. Plugin Config Format Mismatch

- **File:** `README.md` (main project)
- **Section:** Installation → OpenClaw Plugin / Plugin Configuration
- **Claim:** Plugin should be configured as a list entry:
  ```yaml
  plugins:
    entries:
      - name: fmem-auto
        version: "1.0.0"
        config:
          enabled: true
          topK: 3
          minScore: 0.25
          timeoutMs: 5000
  ```
- **Reality:** The `openclaw.plugin.json` defines the plugin with id `fmem-auto` and a `configSchema`. OpenClaw workspace plugins are typically configured as map entries keyed by plugin id, not list entries with a `name` field. The plugins/README.md shows the map-key format which is more likely correct:
  ```yaml
  plugins:
    entries:
      fmem-auto:
        enabled: true
        topK: 3
  ```
  The main README's list format with `name:`, `version:`, and nested `config:` is likely inaccurate for how OpenClaw resolves workspace plugins.
- **Severity:** **High**
- **Suggested fix:** Align main README plugin configuration section with the map-key format shown in plugins/README.md. Remove the `version:` and `config:` nesting unless OpenClaw explicitly supports that format. Verify against OpenClaw docs.

---

### 4. Unimplemented Feature: Multi-Language Triggers

- **File:** `openspec/changes/archive/multi-language-triggers/design.md`
- **Section:** Entire document
- **Claim:** Describes a two-stage trigger system with regex patterns for English and Portuguese, plus spaCy entity extraction
- **Reality:** None of this is implemented. The current plugin (`triggers.ts`) has English-only regex patterns hardcoded in `DEFAULT_TRIGGERS`. There is no `PatternRegistry`, no `trigger_detector.py`, no `en_patterns.py`/`pt_patterns.py`, no `EntityExtractor`, no spaCy integration. The design doc describes a Python implementation for fmem core, but the plugin is TypeScript and doesn't reference any of these modules.
- **Severity:** **High**
- **Suggested fix:** Add a clear status banner at the top of the design doc: "⚠️ STATUS: NOT IMPLEMENTED — This is a design proposal, not current functionality." Alternatively, move from `archive/` to a more clearly labeled `proposals/` directory. Do not reference this as if it's implemented in any user-facing docs.

---

### 5. Unimplemented Feature: Implicit Triggers / Entity Extraction

- **File:** `notes/fmem-implicit-triggers.md`
- **Section:** Entire document
- **Claim:** Describes implicit trigger detection with 20-minute cooldown, entity/action extraction via regex, `entity-extractor.ts`, `IMPLICIT_COOLDOWN_MS`, `sessionLastImplicitSearch`
- **Reality:** None of this is implemented. The current `index.ts` only has explicit trigger detection via `shouldSearch()`. There is no `entity-extractor.ts` file, no implicit cooldown tracking, no `sessionLastImplicitSearch` Map. The current rate limiting (`MIN_SEARCH_INTERVAL_MS = 1000`) and deduplication (`DEDUPE_TTL_MS = 5 min`) serve different purposes.
- **Severity:** **High**
- **Suggested fix:** Add a status banner: "⚠️ STATUS: PLANNING — Not yet implemented." This is a planning document; treat it as a roadmap item, not documentation of current behavior.

---

### 6. Unimplemented Feature: Proactive Injection

- **File:** `openspec/changes/archive/proactive-injection/specs/injection/spec.md`
- **Section:** Entire document
- **Claim:** Describes `get_proactive_context()` function that injects memory at session start, `reset_proactive()`, and integration with `assemble` hook
- **Reality:** Neither `get_proactive_context()` nor `reset_proactive()` exists anywhere in the codebase. The Python `fmem_integration.py` (if it still exists) may have a different API. The TypeScript plugin has no equivalent. There is no `assemble` hook usage.
- **Severity:** **High**
- **Suggested fix:** Add status banner: "⚠️ STATUS: NOT IMPLEMENTED — Specification only." Move to a clearly labeled proposals directory.

---

### 7. Missing Documentation: Custom Trigger Overrides via Config

- **File:** `README.md` (main project) + `plugins/README.md`
- **Section:** Plugin Configuration / Trigger Types
- **Claim:** Documentation describes four trigger types (explicit, recency, location, context) as built-in behavior with example patterns
- **Reality:** The code supports **custom trigger overrides** via config. `PluginConfig.triggers` allows users to replace any or all trigger categories with their own string patterns (see `triggers.ts` line `const triggers = config?.triggers ?? DEFAULT_TRIGGERS;`). The `openclaw.plugin.json` configSchema documents this with `additionalProperties: false` on the triggers object and string array items. Neither README explains that users can override triggers in config.
- **Severity:** **Medium**
- **Suggested fix:** Add a "Custom Triggers" subsection to the Plugin Configuration section explaining that users can override any trigger category via config, with a YAML example:
  ```yaml
  plugins:
    entries:
      fmem-auto:
        triggers:
          explicit:
            - "look up"
            - "find"
            - "recall"
          recency:
            - "last week"
            - "yesterday"
  ```

---

### 8. Missing Documentation: gracefulDegradation Config Option

- **File:** `README.md` (main project)
- **Section:** Plugin Configuration table
- **Claim:** The main README's plugin configuration table lists only `enabled`, `topK`, `minScore`, and `timeoutMs`
- **Reality:** The `openclaw.plugin.json` and `types.ts` also define `gracefulDegradation` (boolean, default true). This option is documented in `plugins/README.md` but missing from the main README.
- **Severity:** **Medium**
- **Suggested fix:** Add `gracefulDegradation` to the main README's Plugin Configuration table with: Type: boolean, Default: true, Description: "Continue without memory if fmem search fails"

---

### 9. Outdated Reference: AGENTS.md Integration as Primary

- **File:** `README.md` (main project)
- **Section:** Comparison table / Migration from AGENTS.md
- **Claim:** The comparison table and migration section describe AGENTS.md triggers as a working alternative, including references to `auto_recall()` as "Legacy OpenClaw integration function" in the Components table
- **Reality:** The `auto_recall()` function is Python (`fmem_integration.py`) and is not part of the TypeScript plugin. The plugin does not use or reference `auto_recall()`. The AGENTS.md integration path may still work independently via OpenClaw's agent-level memory tools, but it's a completely separate code path from the plugin. The Components table lists `auto_recall()` as a component but it's in a different language/codebase entirely.
- **Severity:** **Medium**
- **Suggested fix:** Clarify in the Components table that `auto_recall()` is a Python function in fmem core (for AGENTS.md-based integration), not part of the TypeScript plugin. Make it clear these are two distinct integration paths, not components of the same system.

---

### 10. Undocumented Hardcoded Values

- **File:** N/A (code audit → documentation gap)
- **Section:** N/A
- **Claim:** Documentation doesn't mention several hardcoded constants that affect behavior
- **Reality:** The following hardcoded values exist in the code but aren't documented as configurable or noted:
  - `DEDUPE_TTL_MS = 5 * 60 * 1000` (5 min dedup window) — mentioned in plugins/README.md but not in main README
  - `MIN_SEARCH_INTERVAL_MS = 1000` (1s rate limit) — mentioned in plugins/README.md but not in main README
  - `MAX_MESSAGE_LENGTH = 10000` (DoS protection) — not documented anywhere
  - `maxPreview = 150` (formatter, adaptive up to 400 for single results) — not documented
  - `FMEM_CLI = 'fmem'` (CLI command name) — not documented as configurable
  - `INJECTED_PATTERNS` (5 regex patterns for filtering OpenClaw metadata) — not documented
- **Severity:** **Medium**
- **Suggested fix:** Add an "Internal Constants" or "Behavior Constants" section to plugins/README.md documenting: `MAX_MESSAGE_LENGTH` (10,000 chars), `maxPreview` (150 chars, adaptive), and `FMEM_CLI` command name. The main README should at minimum mention `MAX_MESSAGE_LENGTH` as a DoS protection measure.

---

### 11. Trigger Description Mismatch: Recency Triggers

- **File:** `plugins/README.md`
- **Section:** Triggers table
- **Claim:** Recency triggers description: "Recently stored memories surface automatically"
- **Reality:** The recency triggers in `triggers.ts` are **text pattern matchers** (e.g., `/(last|recent|previous|earlier)\s+(week|month|day|session|conversation)/i`), not automatic surfacing based on memory recency. The description implies memories are proactively recalled based on their storage timestamp, but in reality the trigger only fires when the user's message contains recency-related *words*. This is a significant semantic difference.
- **Severity:** **Medium**
- **Suggested fix:** Change description to: "User references time periods in their message (e.g., 'last week', 'recently', 'yesterday')". Similarly update the main README's trigger table.

---

### 12. Trigger Description Mismatch: Location Triggers

- **File:** `plugins/README.md`
- **Section:** Triggers table
- **Claim:** Location triggers description: "Memories tagged with relevant locations or contexts"
- **Reality:** Location triggers in `triggers.ts` are text patterns matching path-like references (`/(in|under|from)\s+([\w-]+\/[\w-]+)/i`) and directory names (`/docs|projects|notes|memory|personas/`). They detect when the user *mentions* a location in their message, not when memories are "tagged" with locations.
- **Severity:** **Medium**
- **Suggested fix:** Change description to: "User mentions a directory, path, or location category (e.g., 'in docs', 'under projects/')". Similarly update main README.

---

### 13. Trigger Description Mismatch: Context Triggers

- **File:** `plugins/README.md`
- **Section:** Triggers table
- **Claim:** Context triggers description: "Semantic similarity between the prompt and stored memories"
- **Reality:** Context triggers in `triggers.ts` are simple regex patterns matching phrases like "my preferences", "my settings", "my goals", "my projects", and hardcoded names like "Luis", "workspace", "setup". This is keyword matching, not semantic similarity.
- **Severity:** **Medium**
- **Suggested fix:** Change description to: "User references personal context patterns (e.g., 'my preferences', 'my goals', hardcoded workspace terms)". Similarly update main README.

---

### 14. Main README Trigger Table: Wrong Examples

- **File:** `README.md` (main project)
- **Section:** Trigger Types table
- **Claim:** Explicit trigger examples: "remember", "recall", "what about". Location trigger examples: "fitness", "movies", "projects", "work". Context trigger examples: "my goals", "my preferences", "we discussed".
- **Reality:** 
  - "what about" is NOT a trigger pattern in the code. The explicit patterns are: `look up`, `find`, `search`, `recall`, `remember`, `what did/was/were`, `when did`, `show me`, `tell me about`.
  - "fitness", "movies", "work" are NOT location trigger patterns. The actual location patterns match `in|under|from` + path-like segments, or the exact words `docs|projects|notes|memory|personas`.
  - "we discussed" is NOT a context trigger pattern. Actual context patterns: `my|our` + `preferences|settings|goals|projects`, and hardcoded words `Luis|workspace|setup`.
- **Severity:** **Medium**
- **Suggested fix:** Replace examples with actual trigger patterns from the code:
  - Explicit: "look up", "find", "recall", "remember", "show me", "tell me about"
  - Location: "in docs", "in projects", "under memory/personas"
  - Context: "my preferences", "my goals", "my projects", "Luis", "workspace"

---

### 15. Stale Backlog Entry: OpenClaw Plugin

- **File:** `BACKLOG.md`
- **Section:** High Priority → Item 1: "OpenClaw Plugin: Trigger-Based Auto-Injection"
- **Claim:** Describes building the fmem-auto plugin as a backlog item with architecture notes and comparison to `memory-auto-recall`
- **Reality:** The plugin is already built and shipped (v1.0.0 in package.json, code exists in `plugins/openclaw-fmem-auto/`). This backlog item should be marked as complete or removed.
- **Severity:** **Low**
- **Suggested fix:** Add ✅ completion marker and date, or move to an "Archive/Completed" section. Update the description to note the plugin was implemented as `openclaw-fmem-auto` v1.0.0.

---

### 16. REF_PLAN.md: Outdated Architecture

- **File:** `REF_PLAN.md`
- **Section:** Entire document
- **Claim:** Describes refactoring plan for Python `MemoryRetrieval` class (~3200 lines), creating `EmbeddingService`, `SearchIndex`, `DatabaseService`, `ResultEnhancer`, `FileSummarizer`, `DocumentManager`, `PersistenceManager`
- **Reality:** The REF_PLAN describes Python fmem core refactoring that may or may not have been completed. The document has no status marker indicating whether it was implemented. The plan references `src/fmem/fmem.py` as the main file to refactor, but the document doesn't note the current state of that refactoring.
- **Severity:** **Low**
- **Suggested fix:** Add a status banner at the top indicating whether this refactoring was completed, partially completed, or abandoned. If completed, note the date and which modules were extracted.

---

### 17. plugins/README.md: Installation Steps Incomplete

- **File:** `plugins/README.md`
- **Section:** Installation
- **Claim:** "1. Copy the `openclaw-fmem-auto` plugin directory to your OpenClaw plugins path"
- **Reality:** The plugin uses `"main": "./src/index.ts"` and `"type": "module"` in package.json with TypeScript source. There's no build step defined that produces JS output (the `build` script is just `tsc --noEmit` for type-checking). OpenClaw appears to load the TypeScript source directly. The installation steps should clarify whether OpenClaw handles TS natively or if a build step is needed.
- **Severity:** **Low**
- **Suggested fix:** Clarify that OpenClaw loads TypeScript plugins directly (no build/compile step required), or add a build step if one is needed. Also clarify what "OpenClaw plugins path" means — is it the `plugins/` directory in the workspace, or a global location?

---

### 18. Main README: Context Injection Format Example Doesn't Match Code Output

- **File:** `README.md` (main project)
- **Section:** Context Injection Format → Example Injection
- **Claim:** The example shows `About this file: {precomputed_summary} | {dynamic_stats}` fields in the output
- **Reality:** The formatter (`formatter.ts`) does NOT include `About this file:` with precomputed summaries or dynamic stats. The actual output format from `formatResults()` is:
  ```
  [1] Most relevant: {docType} from {dirname}/{filename}
     Source: {filepath}
     
     Under '{heading}':
     {content_preview}
     [relevance: XX%]
  ```
  There is no `About this file:` line. This field was apparently part of a Python formatter that hasn't been ported to the TypeScript plugin.
- **Severity:** **Medium**
- **Suggested fix:** Remove the `About this file: {precomputed_summary} | {dynamic_stats}` line from the injection format documentation and the example, OR implement it in the TypeScript formatter if the feature is desired. The XML tag structure and relevance ranking format are correct.

---

### 19. Contributing Guide: Test Command Incorrect for Plugin

- **File:** `CONTRIBUTING.md`
- **Section:** Testing
- **Claim:** `python tests/test_fmem.py`
- **Reality:** This only covers the Python fmem core tests. The TypeScript plugin has no test files and no test command is documented. The plugin's package.json has `"build": "tsc --noEmit"` and `"typecheck": "tsc --noEmit"` but no test script.
- **Severity:** **Low**
- **Suggested fix:** Add a note about plugin testing (even if just `npm run typecheck`), or acknowledge that plugin tests are not yet available.

---

### 20. Hardcoded Username "Luis" in Trigger Patterns

- **File:** Code: `triggers.ts`
- **Section:** `DEFAULT_TRIGGERS.context`
- **Claim:** N/A (this is a code finding, not a doc claim)
- **Reality:** The context trigger patterns include `/\b(Luis|workspace|setup)\b/i` which hardcodes the username "Luis" as a trigger word. This is user-specific and shouldn't be in a published plugin's default triggers. It means anyone else using this plugin would have "Luis" as a memory trigger, which is nonsensical for them.
- **Severity:** **Low** (documentation gap — should be documented or removed)
- **Suggested fix:** Either: (1) Remove "Luis" from default triggers and make it configurable via `config.triggers.context`, or (2) Document in plugins/README.md that default triggers include the workspace owner's name and explain how to customize.

---

## Appendix: Source Code Summary

### Files Audited (Source)
| File | Lines | Key Content |
|------|-------|-------------|
| `index.ts` | 203 | Main plugin entry, hook handler, session cache, rate limiting |
| `types.ts` | 50 | PluginConfig, Event, Context, Result types |
| `triggers.ts` | 140 | `shouldSearch()`, `extractSearchQuery()`, DEFAULT_TRIGGERS |
| `fmem-client.ts` | 95 | `isFmemAvailable()`, `fmemSearch()`, CLI wrapper |
| `formatter.ts` | 150 | `formatResults()`, `getDocType()`, `cleanForLLm()` |
| `sdk-stub.ts` | 60 | Type stubs for @openclaw/plugin-sdk |
| `package.json` | 30 | Plugin metadata, deps |
| `openclaw.plugin.json` | 60 | Config schema definition |

### Files Audited (Documentation)
| File | Key Content |
|------|-------------|
| `plugins/README.md` | Plugin-specific docs, config, triggers |
| `README.md` | Full project README, architecture, CLI, plugin section |
| `BACKLOG.md` | Development backlog (3 items) |
| `CONTRIBUTING.md` | Contributing guide |
| `REF_PLAN.md` | Python refactoring blueprint |

### Files Audited (Design Docs)
| File | Status |
|------|--------|
| `notes/fmem-implicit-triggers.md` | Planning doc — NOT implemented |
| `openspec/.../multi-language-triggers/design.md` | Design proposal — NOT implemented |
| `openspec/.../proactive-injection/specs/injection/spec.md` | Spec only — NOT implemented |