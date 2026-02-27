# Proposal: QMD-Inspired Advanced Ranking

## Problem Statement

Current fmem search uses a simple weighted sum for multi-factor ranking (semantic × 0.5 + recency × 0.3 + location × 0.2). While functional, this approach has limitations:

1. **Dilution of exact matches**: High-confidence exact matches can be buried by weighted averaging
2. **No rank awareness**: Fixed weights regardless of result position don't preserve high-confidence top results
3. **Limited fusion strategy**: Weighted sum is less sophisticated than modern fusion approaches like RRF

QMD demonstrates superior ranking through RRF (Reciprocal Rank Fusion) with position-aware blending and top-rank bonuses.

## Success Criteria

- [ ] Implement RRF fusion as alternative ranking strategy
- [ ] Add top-rank bonus system (+0.05 for #1, +0.02 for #2-3)
- [ ] Implement position-aware blending (different weights for top 1-3 vs 4-10 vs 11+)
- [ ] Maintain backward compatibility with existing weighted sum approach
- [ ] Update ResultEnhancer to support configurable ranking strategies
- [ ] Add comprehensive tests for new ranking features
- [ ] Update API.md with new ranking configuration options

## Out of Scope

- Query expansion (separate proposal)
- LLM-based reranking (separate proposal)
- MCP server implementation (separate proposal)
- Changes to embedding generation or chunking logic
- Database schema changes

## Notes

**Inspiration Source:** QMD's hybrid search pipeline uses RRF with k=60, position-aware blending, and top-rank bonuses to preserve exact matches while leveraging multiple retrieval signals.

**Key Insight:** RRF performs better than weighted sum when combining multiple ranked lists because it respects the confidence encoded in rank positions.

**Risk:** Low - pure algorithmic change, no storage or API breaking changes.

**Effort Estimate:** 4-6 hours for implementation + testing.
