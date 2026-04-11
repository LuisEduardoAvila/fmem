# Tasks: Query Expansion Service

## Phase 1: Core Service Implementation

- [ ] 1.1 Create `query_expansion_service.py` module
  - Define QueryExpansionService class
  - Implement __init__ with config and llm_client injection
  - Add should_expand() method

- [ ] 1.2 Implement expand_query() method
  - Build LLM prompt for variant generation
  - Handle LiteLLM completion calls
  - Parse JSON response to extract variants

- [ ] 1.3 Add error handling and fallbacks
  - Timeout handling (fallback to original query)
  - JSON parse errors (graceful degradation)
  - LLM API errors (log and continue)

- [ ] 1.4 Write unit tests for QueryExpansionService
  - Test should_expand() word counting
  - Test prompt building
  - Test response parsing (valid and invalid JSON)
  - Test error handling paths

## Phase 2: MemoryRetrieval Integration

- [ ] 2.1 Add `expand_query` parameter to MemoryRetrieval.search()
  - Accept boolean flag
  - Default False (backward compatible)

- [ ] 2.2 Implement query expansion in search flow
  - Check flag and call expansion service
  - Generate list of queries (original + variants)

- [ ] 2.3 Create _fuse_expanded_results() method
  - Search all query variants
  - Group results by filepath
  - Keep highest score per document
  - Sort and limit to top_k

- [ ] 2.4 Optimize multi-query search
  - Batch embedding generation if possible
  - Parallel search for variants (consider asyncio)

- [ ] 2.5 Write integration tests
  - End-to-end test with mocked expansion
  - Test fusion logic with synthetic data
  - Verify deduplication works

## Phase 3: Configuration & Wiring

- [ ] 3.1 Create ExpansionConfig dataclass
  - All configuration options from design
  - Validation (max_variants >= 0, etc.)

- [ ] 3.2 Add expansion config to ConfigService
  - Parse [query_expansion] section from fmem.conf
  - Provide sensible defaults

- [ ] 3.3 Wire QueryExpansionService into MemoryRetrieval
  - Instantiate in MemoryRetrieval.__init__()
  - Inject config

- [ ] 3.4 Update __init__.py exports
  - Export QueryExpansionService
  - Export ExpansionConfig

## Phase 4: Testing & Validation

- [ ] 4.1 Integration tests with LiteLLM
  - Test with local Ollama model
  - Test timeout handling
  - Test token limit enforcement

- [ ] 4.2 Performance tests
  - Measure expansion latency
  - Test multi-variant search overhead
  - Verify memory usage acceptable

- [ ] 4.3 Manual testing
  - Real search with expansion enabled
  - Compare with/without expansion recall
  - Test edge cases (short queries, special chars)

- [ ] 4.4 Error scenario testing
  - Network failure simulation
  - LLM timeout simulation
  - Malformed response handling

## Phase 5: Documentation

- [ ] 5.1 Update API.md
  - Document MemoryRetrieval.search() expand_query parameter
  - Add ExpansionConfig reference
  - Include example usage

- [ ] 5.2 Update README.md
  - Add query expansion to features list
  - Include example configuration
  - Mention QMD inspiration

- [ ] 5.3 Create example fmem.conf
  - Show query_expansion section
  - Include all configuration options

- [ ] 5.4 Write tutorial/guide
  - Step-by-step for enabling expansion
  - Tips for choosing model (local vs cloud)
  - Performance considerations

- [ ] 5.5 Update CHANGELOG.md
  - Document new query expansion feature

## Phase 6: Verification

- [ ] 6.1 Full test suite run
  - All existing tests pass
  - New tests pass
  - No regressions

- [ ] 6.2 Backward compatibility check
  - Existing code without expand_query works unchanged
  - Config without expansion section works

- [ ] 6.3 Performance baseline
  - Document overhead of expansion vs direct search
  - Provide guidance on when to use

- [ ] 6.4 Documentation review
  - All docs updated
  - Examples tested and working
  - No broken links

## Verification Checklist

- [ ] All tasks complete
- [ ] Tests pass (`pytest tests/`)
- [ ] Manual testing completed
- [ ] Documentation updated
- [ ] Example configuration provided
- [ ] CHANGELOG updated
- [ ] Backward compatibility verified
- [ ] Performance characteristics documented
