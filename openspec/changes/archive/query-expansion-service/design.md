# Design: Query Expansion Service

## Overview

Create a new QueryExpansionService that generates semantically equivalent query variants using LLMs, then integrates with MemoryRetrieval to search all variants and fuse results.

## Architecture

### Component Structure

```
src/fmem/
├── query_expansion_service.py    # NEW
│   └── QueryExpansionService
│       ├── __init__(self, config, llm_client)
│       ├── expand_query(query: str, max_variants: int) -> List[str]
│       └── should_expand(query: str) -> bool
│
├── memory_retrieval.py           # Modified
│   └── MemoryRetrieval
│       └── search()              # Modified to support expand_query parameter
│
├── config.py                     # Modified
│   └── ExpansionConfig            # NEW
│
└── __init__.py                   # Modified
    └── Export QueryExpansionService
```

### Integration Flow

```
User Query
    │
    ▼
┌──────────────────────┐
│ MemoryRetrieval      │
│   .search()          │
└──────────┬───────────┘
           │
    ┌──────┴──────┐
    │             │
    ▼             ▼
┌───────────┐ ┌─────────┐
│ Direct    │ │Expand?  │
│ Search    │ │         │
│ (fallback)│ └────┬────┘
└───────────┘      │
                   ▼
          ┌─────────────────┐
          │ QueryExpansion  │
          │   .expand()     │
          └────────┬────────┘
                   │
                   ▼
          ┌─────────────────┐
          │  [variant1]     │
          │  [variant2]     │
          │  ...            │
          └────────┬────────┘
                   │
                   ▼
          ┌─────────────────┐
          │ Search All      │
          │ Variants        │
          └────────┬────────┘
                   │
                   ▼
          ┌─────────────────┐
          │ Fuse Results    │
          │ + Deduplicate   │
          └────────┬────────┘
                   │
                   ▼
          Final Results
```

## Implementation Details

### 1. QueryExpansionService Class

```python
class QueryExpansionService:
    """
    Generate semantic query variants using LLMs.
    
    Inspired by QMD's query expansion with fine-tuned models.
    Uses LiteLLM/Ollama for local/cloud flexibility.
    """
    
    def __init__(
        self,
        config: ExpansionConfig,
        llm_client: Optional[LiteLLMClient] = None
    ):
        self.config = config
        self.llm = llm_client or get_default_llm()
    
    def should_expand(self, query: str) -> bool:
        """Check if query should be expanded."""
        words = query.split()
        
        # Skip short queries
        if len(words) < self.config.min_word_count:
            return False
        
        # Skip if disabled in config
        if not self.config.enabled:
            return False
        
        return True
    
    def expand_query(
        self,
        query: str,
        max_variants: Optional[int] = None
    ) -> List[str]:
        """
        Generate query variants.
        
        Returns: [original_query] + [variant1, variant2, ...]
        """
        if not self.should_expand(query):
            return [query]
        
        max_v = max_variants or self.config.max_variants
        
        prompt = self._build_prompt(query, max_v)
        
        try:
            # Call LLM with timeout
            response = self.llm.completion(
                model=self.config.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.config.token_limit,
                timeout=self.config.timeout
            )
            
            variants = self._parse_response(response)
            return [query] + variants[:max_v]
            
        except TimeoutError:
            logger.warning(f"Query expansion timeout for: {query}")
            return [query]
            
        except Exception as e:
            logger.error(f"Query expansion failed: {e}")
            return [query]  # Fallback to original
    
    def _build_prompt(self, query: str, n: int) -> str:
        """Build LLM prompt for variant generation."""
        return f"""Generate {n} semantically equivalent variants for the search query.

Original: "{query}"

Rules:
- Use synonyms and alternative phrasing
- Preserve technical meaning
- Keep variants concise (3-8 words)

Respond with JSON array only: ["variant1", "variant2", ...]"""
    
    def _parse_response(self, response: str) -> List[str]:
        """Parse LLM response to extract variants."""
        # Extract JSON array from response
        # Handle various formats: markdown code blocks, raw JSON, etc.
        try:
            # Strip markdown if present
            if "```" in response:
                response = response.split("```")[1].strip()
            
            variants = json.loads(response)
            return [v.strip() for v in variants if isinstance(v, str)]
            
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse expansion response: {response}")
            return []
```

### 2. MemoryRetrieval Integration

Modify `MemoryRetrieval.search()`:

```python
def search(
    self,
    query: str,
    top_k: int = 5,
    expand_query: bool = False,  # NEW parameter
    **kwargs
) -> List[Dict]:
    """
    Search memory with optional query expansion.
    """
    # Expand query if requested
    if expand_query and self._expansion_service:
        queries = self._expansion_service.expand_query(query)
    else:
        queries = [query]
    
    # Search all variants
    all_results = []
    for q in queries:
        results = self._search_single(q, top_k=top_k * 2, **kwargs)  # Get more for fusion
        all_results.extend(results)
    
    # Deduplicate and fuse
    if len(queries) > 1:
        return self._fuse_expanded_results(all_results, top_k)
    else:
        return all_results[:top_k]

def _fuse_expanded_results(
    self,
    results: List[Dict],
    top_k: int
) -> List[Dict]:
    """
    Fuse results from multiple query variants.
    
    Strategy: Keep highest score per document across all variants.
    """
    # Group by filepath
    by_doc: Dict[str, List[Dict]] = defaultdict(list)
    for r in results:
        by_doc[r['filepath']].append(r)
    
    # Take best score per document
    fused = []
    for filepath, variants in by_doc.items():
        best = max(variants, key=lambda x: x.get('score', 0))
        fused.append(best)
    
    # Sort by score and limit
    fused.sort(key=lambda x: x.get('score', 0), reverse=True)
    return fused[:top_k]
```

### 3. Configuration Schema

```python
@dataclass
class ExpansionConfig:
    """Configuration for query expansion."""
    
    enabled: bool = False
    """Master switch for query expansion."""
    
    max_variants: int = 1
    """Number of variants to generate (in addition to original)."""
    
    min_word_count: int = 3
    """Minimum words for query to be expanded."""
    
    model: str = "gemma3:4b-cloud"  # Default local model
    """LLM model for expansion (via LiteLLM)."""
    
    token_limit: int = 150
    """Max tokens for expansion response."""
    
    timeout: float = 3.0
    """Timeout in seconds for LLM call."""
    
    cost_limit_per_day: Optional[int] = None
    """Optional daily token budget for expansion."""
```

### 4. LiteLLM Integration

Use existing LiteLLM infrastructure (already configured in TOOLS.md):

```python
class LiteLLMClient:
    """Wrapper for LiteLLM completion calls."""
    
    def completion(self, model, messages, max_tokens, timeout):
        response = litellm.completion(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            timeout=timeout,
            api_base="http://localhost:4000"  # LiteLLM proxy
        )
        return response.choices[0].message.content
```

## Dependencies

- **Existing:** LiteLLM integration (already in TOOLS.md)
- **Optional:** Local Ollama models (gemma3, qwen3)
- **New:** None (uses existing LLMClient pattern)

## Migration Strategy

**Brownfield:**
1. QueryExpansionService is additive - no breaking changes
2. Expansion is opt-in via `expand_query=True` parameter
3. Existing searches work unchanged
4. New capability available for interested users

## Testing Strategy

1. Unit tests for QueryExpansionService prompt building
2. Mock LLM client for testing without API calls
3. Integration tests with real LiteLLM calls (optional)
4. Performance tests (timeout handling, token limits)
5. Edge case tests (parsing malformed responses)

## Open Questions

1. **Q:** Should expansion be automatic or explicit?  
   **A:** Start explicit (`expand_query=True`), consider auto after evaluation.

2. **Q:** What models to support?  
   **A:** Any LiteLLM-compatible. Recommend: local (gemma3:4b-cloud) for zero cost, cloud for quality.

3. **Q:** Cache expansions for repeated queries?  
   **A:** Nice-to-have for Phase 2. Not required for initial implementation.

4. **Q:** How to handle expansion failures?  
   **A:** Graceful fallback to original query only, log warning.
