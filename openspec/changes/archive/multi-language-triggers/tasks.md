# Tasks: Multi-Language Trigger Detection

## Phase 1: Regex Pattern System

### 1.1 Create Pattern Infrastructure

- [ ] Create `trigger_patterns/` directory structure
- [ ] Implement `base.py` with `PatternSet` and `PatternRegistry` classes
- [ ] Add pattern compilation with case-insensitive regex
- [ ] Add `match_any()` method for multi-language matching

### 1.2 English Patterns

- [ ] Create `en_patterns.py` with all English patterns
- [ ] Port existing patterns from `fmem_integration.py`
- [ ] Add new `interrogative` category
- [ ] Test against existing test cases

### 1.3 Portuguese Patterns

- [ ] Create `pt_patterns.py` with Portuguese patterns
- [ ] Translate pattern categories:
  - [ ] `explicit`: lembra, lembrar, recordar, procurar, encontrar
  - [ ] `recency`: última, recente, anterior, semana passada, ontem
  - [ ] `location`: em/no/na + directory names
  - [ ] `context`: meu/minha + preferences/settings/goals
  - [ ] `interrogative`: o que, quando, onde, qual, como
- [ ] Test against Portuguese query samples

### 1.4 Pattern Registry Integration

- [ ] Load patterns based on config `languages` setting
- [ ] Support dynamic language addition
- [ ] Add unit tests for pattern registry

## Phase 2: Entity Extraction System

### 2.1 Create Entity Extractor Infrastructure

- [ ] Create `entity_extractor/` directory structure
- [ ] Implement `extractor.py` with `EntityExtractor` class
- [ ] Add lazy model loading to avoid startup overhead
- [ ] Implement entity filtering (vague entities, pronouns)

### 2.2 SpaCy Integration

- [ ] Add spaCy as optional dependency (`[entity]` extra)
- [ ] Add model download instructions to README
- [ ] Implement graceful fallback if spaCy not installed
- [ ] Add language detection for model selection

### 2.3 Entity Quality Filtering

- [ ] Define `VAGUE_ENTITIES` set (English + Portuguese)
- [ ] Define `INTERESTING_DEPS` and `INTERESTING_POS` sets
- [ ] Implement `is_interesting()` with configurable threshold
- [ ] Add deduplication logic (case-insensitive)

### 2.4 Model Management

- [ ] Implement model caching (don't reload on each call)
- [ ] Add `models.py` with download/check helpers
- [ ] Add config option to disable entity extraction
- [ ] Document model installation in INSTALLATION.md

## Phase 3: Trigger Detector Orchestrator

### 3.1 Core Implementation

- [ ] Create `trigger_detector.py`
- [ ] Implement `TriggerDetector` class
- [ ] Implement two-stage detection flow:
  1. [ ] Stage 1: Regex pattern check
  2. [ ] Stage 2: Entity extraction (if enabled and no regex match)
- [ ] Implement `TriggerResult` dataclass

### 3.2 Language Detection

- [ ] Implement simple heuristic-based detection
- [ ] Count Portuguese-specific characters (à, á, ã, etc.)
- [ ] Count Portuguese-specific words (de, da, que, etc.)
- [ ] Add fallback to default language

### 3.3 Integration with fmem_integration.py

- [ ] Replace existing `should_search()` implementation
- [ ] Add `_get_detector()` singleton pattern
- [ ] Maintain backward-compatible `should_search()` signature
- [ ] Add logging for trigger type and latency

## Phase 4: Configuration

### 4.1 Config File Updates

- [ ] Add `[triggers]` section to `fmem.conf`
- [ ] Add config options:
  - [ ] `entity_extraction` (bool)
  - [ ] `min_entities` (int)
  - [ ] `languages` (comma-separated)
  - [ ] `default_language` (str)
  - [ ] `vague_entities` (comma-separated)
- [ ] Update config schema documentation

### 4.2 Config Parser Updates

- [ ] Add `get_triggers_config()` to ConfigService
- [ ] Add validation for config values
- [ ] Add defaults for missing config options

## Phase 5: Testing

### 5.1 Unit Tests

- [ ] Test: English patterns match correctly
- [ ] Test: Portuguese patterns match correctly
- [ ] Test: Mixed language queries
- [ ] Test: No false positives on casual chat
- [ ] Test: Entity extraction disabled mode
- [ ] Test: Vague entity filtering
- [ ] Test: Entity threshold (min_entities)
- [ ] Test: Language detection heuristics

### 5.2 Integration Tests

- [ ] Test: `should_search()` backward compatibility
- [ ] Test: End-to-end trigger → auto_recall
- [ ] Test: Performance (latency targets)
- [ ] Test: Memory footprint (RAM targets)

### 5.3 Real-World Testing

- [ ] Test with actual Portuguese queries from Trabalhista workspace
- [ ] Test with mixed EN/PT messages
- [ ] Test with edge cases (empty, very long, special chars)

## Phase 6: Documentation

### 6.1 README Updates

- [ ] Add multi-language trigger section
- [ ] Add entity extraction setup instructions
- [ ] Add configuration examples

### 6.2 API Documentation

- [ ] Document `TriggerDetector` class
- [ ] Document `TriggerResult` dataclass
- [ ] Document pattern format
- [ ] Document entity extraction behavior

### 6.3 Migration Guide

- [ ] Document backward compatibility
- [ ] Document new config options
- [ ] Document optional dependencies

### 6.4 Deployment Architecture Docs

- [ ] Document fmem core as portable trigger system
- [ ] Document OpenClaw plugin as separate future project
- [ ] Add client compatibility matrix (Pi, Claude Code, Codex)
- [ ] Note that AGENTS.md integration still works

## Phase 7: OpenClaw Plugin (Future - Separate Project)

**Note:** This phase is documented for planning but NOT part of this spec.

### 7.1 Plugin Scaffold

- [ ] Create `openclaw-fmem-plugin` repository
- [ ] Implement `api.on("assemble")` hook
- [ ] Call `TriggerDetector.should_search()` on incoming messages
- [ ] Inject `format_results()` into context

### 7.2 Plugin Configuration

- [ ] Add plugin config for enable/disable auto-recall
- [ ] Add plugin config for enable/disable auto-index
- [ ] Add trigger threshold configuration

### 7.3 Plugin Publishing

- [ ] Package as OpenClaw plugin
- [ ] Document installation in fmem README
- [ ] Add to ClawHub (optional)

## Verification

How to verify this change is complete:

- [ ] All unit tests pass: `pytest tests/test_triggers.py`
- [ ] Integration tests pass: `pytest tests/test_integration.py`
- [ ] Portuguese query "Lembra do caso trabalhista?" triggers recall
- [ ] English query "Remember my distrobox setup?" still works
- [ ] Entity-only query "What's the distrobox config?" triggers
- [ ] Casual "Hello world" does NOT trigger
- [ ] Latency under 50ms for entity path
- [ ] Latency under 1ms for regex path
- [ ] Memory under 50MB with spaCy loaded
- [ ] Documentation updated and reviewed