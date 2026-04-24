# Design: Multi-Language Trigger Detection

> ⚠️ **STATUS: NOT IMPLEMENTED** — This is a design proposal, not current functionality. The current plugin (`openclaw-fmem-auto`) uses English-only regex patterns in `triggers.ts`. See `plugins/openclaw-fmem-auto/src/triggers.ts` for the actual implementation.

## Overview

Hybrid two-stage trigger system: regex patterns (fast, language-specific) → entity extraction (slower, language-agnostic). This architecture prioritizes the common case (regex match) while providing intelligent fallback for implicit triggers.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     fmem_integration.py                      │
│                    (existing entry point)                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     trigger_detector.py                      │
│                   (NEW - orchestrator)                       │
│                                                              │
│  ┌────────────────┐         ┌────────────────────────────┐  │
│  │ Regex Matcher  │────────▶│ Entity Extractor (lazy)    │  │
│  │ (all languages)│         │ (spaCy on demand)          │  │
│  │                │         │                            │  │
│  │ en_patterns.py │         │ en_core_web_sm (~13MB)     │  │
│  │ pt_patterns.py │         │ pt_core_news_sm (~13MB)    │  │
│  │ es_patterns.py │         │                            │  │
│  └────────────────┘         └────────────────────────────┘  │
│                                                              │
│  ShouldSearchResult:                                         │
│  - triggered: bool                                           │
│  - trigger_type: "regex" | "entity" | None                  │
│  - entities: List[str]                                       │
│  - language: str                                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              fmem_integration.auto_recall()                  │
│                    (existing flow)                           │
└─────────────────────────────────────────────────────────────┘
```

## Component Design

### 1. Pattern Registry (trigger_patterns/)

**Purpose:** Load and manage regex patterns for multiple languages.

```python
# trigger_patterns/base.py
from typing import Dict, List
from dataclasses import dataclass
import re

@dataclass
class PatternSet:
    """Regex patterns for a single language."""
    language: str
    explicit: List[re.Pattern]
    recency: List[re.Pattern]
    location: List[re.Pattern]
    context: List[re.Pattern]
    interrogative: List[re.Pattern]

class PatternRegistry:
    """Manages patterns for all configured languages."""
    
    def __init__(self, languages: List[str] = ['en', 'pt']):
        self._patterns: Dict[str, PatternSet] = {}
        self._load_patterns(languages)
    
    def _load_patterns(self, languages: List[str]):
        for lang in languages:
            if lang == 'en':
                from .en_patterns import EN_PATTERNS
                self._patterns[lang] = self._compile(EN_PATTERNS, lang)
            elif lang == 'pt':
                from .pt_patterns import PT_PATTERNS
                self._patterns[lang] = self._compile(PT_PATTERNS, lang)
    
    def _compile(self, patterns: Dict, lang: str) -> PatternSet:
        """Compile regex strings to Pattern objects."""
        return PatternSet(
            language=lang,
            explicit=[re.compile(p, re.I) for p in patterns.get('explicit', [])],
            recency=[re.compile(p, re.I) for p in patterns.get('recency', [])],
            location=[re.compile(p, re.I) for p in patterns.get('location', [])],
            context=[re.compile(p, re.I) for p in patterns.get('context', [])],
            interrogative=[re.compile(p, re.I) for p in patterns.get('interrogative', [])],
        )
    
    def match_any(self, text: str) -> tuple[bool, str]:
        """Check if text matches any pattern in any language.
        
        Returns: (matched, language)
        """
        for lang, pattern_set in self._patterns.items():
            for pattern in pattern_set.explicit + pattern_set.recency + pattern_set.location + pattern_set.context + pattern_set.interrogative:
                if pattern.search(text):
                    return True, lang
        return False, ''
```

**Memory Footprint:** ~10KB per language (compiled regex objects)

### 2. Entity Extractor (entity_extractor/)

**Purpose:** Extract interesting entities using spaCy, loading models on demand.

```python
# entity_extractor/extractor.py
from typing import List, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class EntityMatch:
    text: str
    label: str
    source: str  # 'ner' or 'dep' (dependency parse)

class EntityExtractor:
    """Language-agnostic entity extraction using spaCy."""
    
    VAGUE_ENTITIES = {
        'thing', 'stuff', 'something', 'anything', 'it', 'that',
        'this', 'one', 'some', 'thing', 'coisa', 'algo', 'isso', 'aquilo'
    }
    
    INTERESTING_DEPS = {'nsubj', 'nsubjpass', 'dobj', 'pobj', 'compound'}
    INTERESTING_POS = {'NOUN', 'PROPN', 'VERB'}
    
    def __init__(self, min_entities: int = 2):
        self._nlp_cache = {}
        self.min_entities = min_entities
    
    def _get_model(self, lang: str):
        """Lazy-load spaCy model."""
        if lang not in self._nlp_cache:
            try:
                import spacy
                if lang == 'pt':
                    self._nlp_cache[lang] = spacy.load('pt_core_news_sm')
                else:
                    self._nlp_cache[lang] = spacy.load('en_core_web_sm')
                logger.info(f"Loaded spaCy model for {lang}")
            except ImportError:
                logger.warning("spaCy not installed, entity extraction disabled")
                return None
            except OSError as e:
                logger.warning(f"spaCy model not found for {lang}: {e}")
                return None
        return self._nlp_cache[lang]
    
    def extract(self, text: str, lang: str = 'en') -> List[EntityMatch]:
        """Extract interesting entities from text."""
        nlp = self._get_model(lang)
        if nlp is None:
            return []
        
        doc = nlp(text)
        entities = []
        
        # Named entities (NER)
        for ent in doc.ents:
            if ent.label_ in {'ORG', 'PRODUCT', 'PERSON', 'GPE', 'EVENT', 'WORK_OF_ART'}:
                if ent.text.lower() not in self.VAGUE_ENTITIES:
                    entities.append(EntityMatch(ent.text, ent.label_, 'ner'))
        
        # Dependency-based extraction (subjects, objects)
        for token in doc:
            if token.dep_ in self.INTERESTING_DEPS and token.pos_ in self.INTERESTING_POS:
                if token.text.lower() not in self.VAGUE_ENTITIES:
                    entities.append(EntityMatch(token.text, token.pos_, 'dep'))
        
        # Dedupe by text (case-insensitive)
        seen = set()
        unique = []
        for e in entities:
            lower = e.text.lower()
            if lower not in seen:
                seen.add(lower)
                unique.append(e)
        
        return unique
    
    def is_interesting(self, text: str, lang: str = 'en') -> Tuple[bool, List[str]]:
        """Check if text has enough interesting entities to trigger.
        
        Returns: (is_interesting, entity_texts)
        """
        entities = self.extract(text, lang)
        entity_texts = [e.text for e in entities]
        return len(entities) >= self.min_entities, entity_texts
```

**Memory Footprint:**
- ~13MB per spaCy model (small models)
- Models loaded on demand, not at import time
- Can disable in config to keep 0MB footprint

### 3. Trigger Detector (orchestrator)

**Purpose:** Coordinate regex and entity detection with configuration.

```python
# trigger_detector.py
from typing import Tuple, Optional
from dataclasses import dataclass
import logging

from .trigger_patterns.base import PatternRegistry
from .entity_extractor.extractor import EntityExtractor

logger = logging.getLogger(__name__)

@dataclass
class TriggerResult:
    """Result of trigger detection."""
    triggered: bool
    trigger_type: Optional[str]  # 'regex', 'entity', or None
    language: Optional[str]
    entities: list
    latency_ms: float

class TriggerDetector:
    """Two-stage trigger detection: regex → entity extraction."""
    
    def __init__(self, config: dict = None):
        config = config or {}
        
        # Get configuration
        self.languages = config.get('languages', ['en', 'pt'])
        self.default_lang = config.get('default_language', 'en')
        entity_enabled = config.get('entity_extraction', True)
        min_entities = config.get('min_entities', 2)
        
        # Initialize components
        self.patterns = PatternRegistry(self.languages)
        self.entity_extractor = EntityExtractor(min_entities) if entity_enabled else None
    
    def should_search(self, message: str) -> TriggerResult:
        """Determine if message should trigger memory search.
        
        Two-stage process:
        1. Fast regex check (all configured languages)
        2. Entity extraction (if regex doesn't match and enabled)
        """
        import time
        start = time.perf_counter()
        
        # Normalize and truncate
        text = message.strip()[:500]
        if not text:
            return TriggerResult(False, None, None, [], 0)
        
        # Stage 1: Regex patterns (fast)
        matched, lang = self.patterns.match_any(text)
        if matched:
            latency = (time.perf_counter() - start) * 1000
            return TriggerResult(True, 'regex', lang, [], latency)
        
        # Stage 2: Entity extraction (if enabled)
        if self.entity_extractor:
            # Detect language for entity extraction
            detected_lang = self._detect_language(text)
            is_interesting, entities = self.entity_extractor.is_interesting(text, detected_lang)
            
            if is_interesting:
                latency = (time.perf_counter() - start) * 1000
                return TriggerResult(True, 'entity', detected_lang, entities, latency)
        
        latency = (time.perf_counter() - start) * 1000
        return TriggerResult(False, None, None, [], latency)
    
    def _detect_language(self, text: str) -> str:
        """Simple language detection for entity extraction.
        
        Uses character heuristics for speed, falls back to default.
        """
        # Count Portuguese-specific characters
        pt_chars = sum(1 for c in text.lower() if c in 'àáâãéêíóôõúç')
        
        # Count Portuguese-specific words
        pt_words = len([w for w in text.lower().split() if w in {
            'de', 'da', 'do', 'que', 'não', 'uma', 'um', 'para', 'como', 'mais',
            'se', 'você', 'ele', 'ela', 'isso', 'são', 'está', 'tem', 'sobre'
        }])
        
        # Portuguese if significant markers
        if pt_chars > 0 or pt_words >= 2:
            return 'pt'
        
        return self.default_lang
```

### 4. Integration with fmem_integration.py

**Purpose:** Replace existing `should_search()` with new `TriggerDetector`.

```python
# fmem_integration.py (modifications)

# ... existing imports ...

from .trigger_detector import TriggerDetector

# ... existing SEARCH_TRIGGERS removed ...

# Global detector instance
_detector = None

def _get_detector() -> TriggerDetector:
    """Get or create trigger detector with config."""
    global _detector
    if _detector is None:
        # Load config from fmem.conf
        from .config import ConfigService
        config_service = ConfigService()
        trigger_config = config_service.get('triggers', {})
        _detector = TriggerDetector(trigger_config)
    return _detector

def should_search(message: str) -> bool:
    """Determine if a message should trigger memory search.
    
    DEPRECATED: Use TriggerDetector.should_search() for rich result.
    This function maintained for backward compatibility.
    """
    detector = _get_detector()
    result = detector.should_search(message)
    
    # Log for debugging
    if result.triggered:
        logger.debug(f"Trigger: {result.trigger_type} ({result.language}) - {result.latency_ms:.1f}ms")
        if result.entities:
            logger.debug(f"Entities: {result.entities}")
    
    return result.triggered
```

## File Structure

```
src/fmem/
├── __init__.py              # Updated exports
├── fmem_integration.py      # Modified (use TriggerDetector)
├── trigger_detector.py      # NEW - orchestrator
├── trigger_patterns/        # NEW - regex patterns
│   ├── __init__.py
│   ├── base.py              # PatternRegistry, PatternSet
│   ├── en_patterns.py       # English patterns
│   └── pt_patterns.py       # Portuguese patterns
└── entity_extractor/        # NEW - spaCy extraction
    ├── __init__.py
    ├── extractor.py         # EntityExtractor
    └── models.py            # Model management helpers
```

## Dependencies

### Required (existing)
- Python 3.10+
- No new required dependencies for regex-only mode

### Optional (entity extraction)
- `spacy>=3.6.0` - NLP library
- `en_core_web_sm` - English model (~13MB)
- `pt_core_news_sm` - Portuguese model (~13MB)

### Installation

```bash
# Core (regex patterns only)
pip install fmem  # No new dependencies

# With entity extraction
pip install fmem[entity]
# OR
pip install spacy
python -m spacy download en_core_web_sm
python -m spacy download pt_core_news_sm
```

## Configuration

```ini
# ~/.openclaw/memory/fmem.conf

[triggers]
# Enable two-stage detection (regex + entity)
entity_extraction = true

# Minimum interesting entities to trigger
min_entities = 2

# Languages for regex patterns (comma-separated)
languages = en, pt

# Default language when ambiguous
default_language = en

# Vague entities to filter out (comma-separated, optional)
vague_entities = thing, stuff, something, anything, it, that, coisa, algo, isso
```

## Performance Targets

| Scenario | Latency | RAM |
|----------|---------|-----|
| Regex match (Stage 1) | <1ms | <1MB |
| No match, entity extraction (Stage 2) | <50ms | ~26MB |
| Entity extraction disabled | <1ms | <1MB |
| 100 messages (90% regex) | <10ms avg | ~26MB peak |

## Testing Strategy

```python
# tests/test_triggers.py

class TestRegexPatterns:
    """Test regex triggers for all languages."""
    
    def test_english_explicit(self):
        result = detector.should_search("Remember my distrobox setup")
        assert result.triggered is True
        assert result.trigger_type == 'regex'
        assert result.language == 'en'
    
    def test_portuguese_explicit(self):
        result = detector.should_search("Lembra do caso trabalhista?")
        assert result.triggered is True
        assert result.trigger_type == 'regex'
        assert result.language == 'pt'
    
    def test_no_match(self):
        result = detector.should_search("Hello world")
        assert result.triggered is False

class TestEntityExtraction:
    """Test entity-based triggers."""
    
    def test_entity_trigger_en(self):
        result = detector.should_search("What's the setup for distrobox?")
        assert result.triggered is True
        assert result.trigger_type == 'entity'
        assert 'distrobox' in result.entities
    
    def test_entity_trigger_pt(self):
        result = detector.should_search("Qual é a configuração do distrobox?")
        assert result.triggered is True
        assert result.trigger_type == 'entity'
    
    def test_too_few_entities(self):
        result = detector.should_search("What time is it?")
        assert result.triggered is False
    
    def test_vague_entity_filtered(self):
        result = detector.should_search("How do I install that thing?")
        assert result.triggered is False  # "thing" filtered as vague

class TestBackwardCompatibility:
    """Ensure existing behavior unchanged."""
    
    def test_existing_should_search(self):
        assert should_search("remember distrobox") is True
        assert should_search("hello world") is False
```

## Open Questions

1. **Language detection:** Should we use `langdetect` for more accuracy, or is the heuristic sufficient?
   - **Recommendation:** Start with heuristic, add `langdetect` if needed

2. **Model selection:** Should we load both spaCy models at startup, or strictly lazy?
   - **Recommendation:** Strictly lazy (load on first entity detection)

3. **Fallback behavior:** If spaCy fails to load, should we:
   - Disable entity extraction silently?
   - Log warning and continue?
   - **Recommendation:** Log warning, continue with regex-only mode