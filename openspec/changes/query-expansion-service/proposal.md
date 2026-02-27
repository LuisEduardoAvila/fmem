# Proposal: Query Expansion Service

## Problem Statement

fmem search relies on semantic similarity which works well for direct matches but struggles with:

1. **Terminology variance**: User searches "deploy" but documents use "release", "push", "ship"
2. **Abbreviations**: "auth" vs "authentication", "db" vs "database"
3. **Conceptual matches**: "error handling" vs "exception management"
4. **Language variants**: "colour" vs "color", "organise" vs "organize"

QMD solves this with a fine-tuned LLM that generates query variants, then searches all variants and fuses results. This significantly improves recall without sacrificing precision.

## Success Criteria

- [ ] Create QueryExpansionService as new module
- [ ] Implement LLM-based query variant generation
- [ ] Support configurable number of variants (default: 1-2)
- [ ] Integrate with MemoryRetrieval.search() to search multiple variants
- [ ] Add result deduplication (same doc from multiple variants)
- [ ] Make expansion optional/configurable per search
- [ ] Add cost/performance controls (token budget, timeout)
- [ ] Document API and configuration options
- [ ] Write comprehensive tests

## Out of Scope

- Training custom query expansion models (use existing LLMs)
- Persistent caching of query expansions (can be added later)
- User feedback on expansion quality
- Multi-language support beyond English (Phase 2)

## Notes

**Inspiration Source:** QMD uses `qmd-query-expansion-1.7B-q4_k_m` GGUF model via node-llama-cpp. For fmem, we can use:
- LiteLLM proxy (existing integration)
- Ollama local models (qwen3, gemma3)
- OpenAI/Anthropic APIs (if user opts in)

**Efficiency Consideration:** Query expansion adds latency (~200-500ms per LLM call). Mitigate with:
- Only expand on multi-word queries
- Skip for very short queries (<3 words)
- Make opt-in per search via `expand_query=True` parameter

**Cost Consideration:** Local models (Ollama) = $0, Cloud APIs = ~$0.001 per query. Support both modes.

**Risk:** Medium - requires LLM integration which adds complexity and potential failure modes.

**Effort Estimate:** 1-2 days for full implementation + testing.
