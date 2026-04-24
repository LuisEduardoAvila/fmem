# Specification: Multi-Language Trigger Detection

> ⚠️ **STATUS: NOT IMPLEMENTED** — This is a specification, not current functionality. The current plugin (`openclaw-fmem-auto`) uses English-only regex patterns in `triggers.ts`. Multi-language support and spaCy-based entity extraction are planned features.

## Overview

This specification defines requirements for two complementary trigger detection mechanisms for fmem auto-recall:

1. **REQ-001: Language-Specific Regex Triggers** - Explicit trigger patterns per language
2. **REQ-002: Language-Agnostic Entity Extraction** - spaCy-based NER for implicit triggers

---

## REQ-001: Language-Specific Regex Triggers

**As a** user speaking multiple languages  
**I want** explicit trigger words to work in my language  
**So that** "remember" (EN) and "lembra" (PT) both trigger memory recall

### Architecture

```
trigger_patterns/
├── __init__.py
├── base.py          # Pattern loader interface
├── en_patterns.py   # English patterns
├── pt_patterns.py   # Portuguese patterns
└── es_patterns.py   # Spanish patterns (future)
```

### Pattern Categories

Each language defines patterns for:

| Category | Purpose | Example (EN) | Example (PT) |
|----------|---------|--------------|--------------|
| `explicit` | Direct memory requests | "remember", "recall" | "lembra", "recordar" |
| `recency` | Time-based references | "last week", "yesterday" | "semana passada", "ontem" |
| `location` | File/path references | "in docs/", "from memory/" | "nos docs/", "da memória" |
| `context` | Personal references | "my projects", "my goals" | "meus projetos", "minhas metas" |
| `interrogative` | Question words | "what did I", "when did" | "o que eu", "quando eu" |

### Scenarios

##### SC-001: English Explicit Trigger

**Given** user message is "What do you remember about distrobox?"  
**When** `should_search()` is called  
**Then** returns `True` with detected language `en`

##### SC-002: Portuguese Explicit Trigger

**Given** user message is "O que você lembra sobre distrobox?"  
**When** `should_search()` is called  
**Then** returns `True` with detected language `pt`

##### SC-003: Mixed Language Content

**Given** user message is "Any updates on the caso trabalhista?"  
**When** `should_search()` is called  
**Then** returns `True` with detected language from first pattern match

##### SC-004: No Trigger Words

**Given** user message is "Hello, how are you?"  
**When** `should_search()` is called without entity detection  
**Then** returns `False`

**Edge Cases:**
- Empty message → `False`
- Only whitespace → `False`
- Very long messages (>1000 chars) → Truncate to first 500 chars for trigger detection

### Pattern Definitions

#### English (en_patterns.py)

```python
EN_PATTERNS = {
    'explicit': [
        r'\b(remember|recall|look up|find|search)\b',
        r'\b(what (did|was|were)|when did)\b',
        r'\b(show me|tell me about)\b',
    ],
    'recency': [
        r'\b(last|recent|previous|earlier)\s+(week|month|day|session)\b',
        r'\b(yesterday|recently|before)\b',
    ],
    'location': [
        r'\b(in|under|from)\s+([\w-]+/[\w-]+)',
        r'\b(docs|projects|notes|memory)\b',
    ],
    'context': [
        r'\b(my|our)\s+(preferences|settings|goals|projects)\b',
        r'\b(workspace|setup)\b',
    ],
    'interrogative': [
        r'\b(what|when|where|which|how)\s+(did|were|was|about)\b',
    ],
}
```

#### Portuguese (pt_patterns.py)

```python
PT_PATTERNS = {
    'explicit': [
        r'\b(lembra|lembrar|recordar|recordo)\b',
        r'\b(procurar|encontrar|buscar)\b',
        r'\b(o que (eu disse|escrevi|mencionei))\b',
    ],
    'recency': [
        r'\b(últim[oa]?|recente|anterior|passad[oa])\b',
        r'\b(semana passada|mês passado|ontem)\b',
        r'\b(anteontem|recentemente)\b',
    ],
    'location': [
        r'\b(em|no|na|de|do|da)\s+(docs|projetos|notas|memória)',
        r'\b(docs|projetos|notas)\b',
    ],
    'context': [
        r'\b(meu[sa]?|noss[oa]s?)\s+(preferências|configurações|metas|projetos)\b',
        r'\b(workspace|configuração)\b',
    ],
    'interrogative': [
        r'\b(o que|quando|onde|qual|como)\s+(eu|você|nós)\b',
    ],
}
```

---

## REQ-002: Language-Agnostic Entity Extraction

**As a** user whose queries may not match trigger patterns  
**I want** interesting entities in my message to trigger memory recall  
**So that** "What's the setup for distrobox?" triggers even without "remember"

### Architecture

```
entity_extractor/
├── __init__.py
├── extractor.py     # Main extraction logic
├── language.py      # Language detection
└── models.py        # spaCy model management
```

### Entity Types

Extract entities that indicate memory-worthy content:

| Entity Type | spaCy Label | Why Interesting |
|-------------|-------------|-----------------|
| **Named entities** | `ORG`, `PRODUCT`, `PERSON`, `GPE`, `EVENT` | Specific things to look up |
| **Noun chunks** | `nsubj`, `dobj`, `pobj` | Subject/object of sentences |
| **Proper nouns** | `PROPN` | Names, titles, identifiers |

### Interest Threshold

Not all entities are memory-worthy. Filter by:

```python
INTERESTING_DEPS = {"nsubj", "nsubjpass", "dobj", "pobj", "compound"}
INTERESTING_POS = {"NOUN", "PROPN", "VERB"}
MIN_ENTITIES = 2  # At least 2 interesting entities to trigger
```

### Scenarios

##### SC-005: Entity-Based Trigger (No Pattern Match)

**Given** user message is "What's the setup for distrobox?"  
**And** no regex patterns match  
**When** `should_search()` is called with entity detection enabled  
**Then** extracts entities ["distrobox", "setup"]  
**And** returns `True` (>= 2 interesting entities)

##### SC-006: Portuguese Entity Extraction

**Given** user message is "Qual é a configuração do distrobox?"  
**And** Portuguese spaCy model is loaded  
**When** `extract_entities()` is called  
**Then** extracts entities ["configuração", "distrobox"]

##### SC-007: Too Few Entities

**Given** user message is "What time is it?"  
**When** `extract_entities()` is called  
**Then** extracts entities ["it", "time"] (but "it" is filtered as pronoun)  
**And** returns `False` (only 1 interesting entity)

##### SC-008: Entity Quality Filter

**Given** user message is "How do I install that thing?"  
**When** `extract_entities()` is called  
**Then** extracts ["thing"] which is vague  
**And** `is_vague("thing")` returns `True`  
**And** returns `False` (filtered as low-quality entity)

**Edge Cases:**
- Message with only pronouns ("he said she did") → `False`
- Message with only verbs ("run jump play") → `False`
- Message with repeated entity ("distrobox distrobox distrobox") → Dedupe, count as 1

### Language Detection

Two strategies:

##### Option A: Fast Language Detect

```python
from langdetect import detect, LangDetectException

def detect_language(text: str) -> str:
    try:
        return detect(text[:500])  # First 500 chars
    except LangDetectException:
        return 'en'  # Default to English
```

**Pros:** Fast (~2ms), small footprint (~2MB)  
**Cons:** Needs 3+ words to be accurate

##### Option B: Try Both Models

```python
def detect_language(text: str, nlp_en, nlp_pt) -> str:
    # Try English model first (faster)
    doc_en = nlp_en(text)
    if doc_en._.language_score > 0.8:
        return 'en'
    
    # Try Portuguese model
    doc_pt = nlp_pt(text)
    if doc_pt._.language_score > 0.8:
        return 'pt'
    
    return 'en'  # Default
```

**Pros:** No extra dependency  
**Cons:** More RAM (both models loaded)

### Model Management

```python
# Lazy loading - models loaded only when entity detection triggered
_nlp_en = None
_nlp_pt = None

def get_spacy_model(lang: str):
    global _nlp_en, _nlp_pt
    
    if lang == 'pt':
        if _nlp_pt is None:
            import spacy
            _nlp_pt = spacy.load('pt_core_news_sm')
        return _nlp_pt
    else:
        if _nlp_en is None:
            import spacy
            _nlp_en = spacy.load('en_core_web_sm')
        return _nlp_en
```

---

## REQ-003: Hybrid Trigger System

**As a** memory system with limited resources  
**I want** to use lightweight regex first and spaCy only when needed  
**So that** RAM usage stays low for most queries

### Decision Flow

```
User Message
     │
     ▼
┌─────────────────────────────┐
│  Stage 1: Fast Regex Check  │
│  (all loaded languages)     │
└─────────────────────────────┘
     │
     ├── Match found ──────────────────▶ Return True
     │
     ▼ No match
┌─────────────────────────────┐
│  Stage 2: Entity Detection  │
│  (spaCy loaded on demand)   │
└─────────────────────────────┘
     │
     ├── 2+ interesting entities ──────▶ Return True
     │
     ▼ Fewer than 2 entities
┌─────────────────────────────┐
│         Return False        │
└─────────────────────────────┘
```

### Configuration

```python
# In fmem.conf
[triggers]
# Enable entity extraction (stage 2)
entity_extraction = true

# Minimum interesting entities to trigger
min_entities = 2

# Languages to check (affects regex patterns)
languages = en, pt

# Default language when ambiguous
default_language = en

# Vague entities to filter out
vague_entities = thing, stuff, something, anything, it, that
```

### Scenarios

##### SC-009: Regex Fast-Path

**Given** entity extraction is enabled  
**And** user message is "Remember my distrobox setup"  
**When** `should_search()` is called  
**Then** regex matches "remember" in Stage 1  
**And** spaCy model is NOT loaded  
**And** returns `True` in <1ms

##### SC-010: Entity Fallback

**Given** entity extraction is enabled  
**And** user message is "How's the distrobox project?"  
**When** `should_search()` is called  
**Then** no regex match in Stage 1  
**And** spaCy model is loaded  
**And** extracts ["distrobox", "project"]  
**And** returns `True` in ~10ms

##### SC-011: Entity Extraction Disabled

**Given** entity extraction is disabled in config  
**And** user message is "How's the distrobox project?"  
**When** `should_search()` is called  
**Then** no regex match in Stage 1  
**And** spaCy model is NOT loaded  
**And** returns `False` (entity detection skipped)

##### SC-012: Performance Under Load

**Given** 100 sequential user messages  
**And** 90 match regex patterns, 10 need entity detection  
**When** processed  
**Then** average latency <5ms per message  
**And** peak RAM <50MB (one spaCy model loaded at a time)

---

## REQ-004: Backward Compatibility

**As a** user with existing workflows  
**I want** existing English queries to continue working  
**So that** no changes to my habits are needed

### Migration Path

1. **Phase 1:** Add regex patterns for Portuguese alongside English
2. **Phase 2:** Add entity extraction as opt-in feature
3. **Phase 3:** Enable entity extraction by default after testing

### Scenarios

##### SC-013: Existing English Query

**Given** user message is "What about my fitness goals?"  
**When** `should_search()` is called with new system  
**Then** returns same result as before (True)  
**And** no breaking changes

##### SC-014: Config Flag for Entity Detection

**Given** `entity_extraction = false` in config  
**When** fmem starts  
**Then** only regex patterns are used  
**And** behavior matches pre-change system

---

---

## REQ-005: Deployment Architecture

**As a** user of multiple AI clients (OpenClaw, Pi, Claude Code)  
**I want** trigger detection to work everywhere  
**So that** I don't need different integrations per client

### Design Principle

**fmem stays portable.** Trigger detection lives in fmem core, callable from any client. OpenClaw-specific integration is a thin wrapper.

### Integration Options

| Option | Location | Auto-Injection | Portability |
|--------|----------|----------------|-------------|
| A. fmem Core | `fmem_integration.py` | ❌ Manual call | ✅ Works everywhere |
| B. OpenClaw Plugin | `openclaw-fmem-plugin` | ✅ Via hooks | ❌ OpenClaw only |
| C. Both | Core + Plugin wrapper | ✅ In OpenClaw | ✅ Works everywhere |

**Chosen:** Option C - Build in fmem core, add plugin wrapper later.

### fmem Core API (This Spec)

```python
# Current (manual trigger in AGENTS.md)
from fmem import should_search, auto_recall
if should_search(message):
    results = auto_recall(message)
    context += format_results(results)
```

```python
# New TriggerResult with debugging info
from fmem import TriggerDetector
detector = TriggerDetector(config)
result = detector.should_search(message)
# result.triggered, result.trigger_type, result.entities, result.latency_ms
```

### OpenClaw Plugin (Future Work)

```python
# openclaw-fmem-plugin (separate project)
api.on("assemble", async ({ messages }) => {
    from fmem import TriggerDetector, auto_recall, format_results
    
    last_message = messages[-1].content
    result = detector.should_search(last_message)
    
    if result.triggered:
        memories = auto_recall(last_message)
        return format_results(memories)
})
```

### OpenClaw Context Engine Hooks (Reference)

For future plugin implementation:

| Hook | When It Fires | Use For Triggers |
|------|---------------|------------------|
| `assemble` | Building context for model | **Primary** - inject memories before model |
| `ingest` | Every incoming message | Index message for future recall |
| `afterTurn` | Turn completes | Batch index captured conversations |

### Client Compatibility Matrix

| Client | Integration Method | Trigger Location |
|--------|-------------------|------------------|
| OpenClaw | AGENTS.md or Plugin | fmem core (via import) |
| Pi (coding agent) | Direct import | fmem core |
| Claude Code | Direct import | fmem core |
| Codex | Direct import | fmem core |
| MCP clients | MCP server wrapper | fmem core |

### Scenarios

##### SC-015: Direct Import from Pi

**Given** Pi coding agent is running  
**When** Pi imports `from fmem import should_search, auto_recall`  
**Then** trigger detection works with Portuguese patterns  
**And** no OpenClaw dependency required

##### SC-016: OpenClaw Plugin Auto-Injection

**Given** openclaw-fmem-plugin is installed and enabled  
**When** user sends message "Lembra do caso trabalhista?"  
**Then** `assemble` hook calls `should_search()` automatically  
**And** memories are injected into context before model sees them  
**And** user doesn't need AGENTS.md trigger instructions

##### SC-017: No OpenClaw (Standalone CLI)

**Given** fmem is used from standalone CLI  
**When** user runs `fmem search "what about distrobox"`  
**Then** search works without any trigger detection (explicit command)  
**And** trigger detection code is available but not invoked

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Portuguese trigger rate | >90% of equivalent English queries | Test suite |
| Latency (regex path) | <1ms | Benchmark |
| Latency (entity path) | <50ms | Benchmark |
| RAM (regex only) | <1MB | Memory profiling |
| RAM (entity loaded) | <50MB | Memory profiling |
| Backward compatibility | 100% existing tests pass | Test suite |
| Client portability | Works in Pi, Claude Code, Codex | Manual test |