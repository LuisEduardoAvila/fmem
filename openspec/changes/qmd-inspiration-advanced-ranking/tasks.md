# Tasks: QMD-Inspired Advanced Ranking

## Phase 1: RRF Fusion Implementation

- [ ] 1.1 Create `_apply_rrf_fusion()` method in ResultEnhancer
  - Implement RRF formula: score = Σ(1/(k+rank+1))
  - Handle document deduplication across lists
  - Add k parameter (default 60)

- [ ] 1.2 Add RankingConfig dataclass to config.py
  - strategy: "weighted_sum" | "rrf"
  - rrf_k: int (default 60)

- [ ] 1.3 Modify ResultEnhancer.enhance() to support strategy selection
  - Branch based on config.ranking.strategy
  - Call either _apply_weighted_sum() or _apply_rrf_fusion()

- [ ] 1.4 Write unit tests for RRF fusion
  - Test with 2-3 ranked lists
  - Verify formula correctness
  - Test edge cases (empty lists, single item, etc.)

## Phase 2: Top-Rank Bonus System

- [ ] 2.1 Create `_apply_top_rank_bonuses()` method
  - Detect #1 ranks across all lists
  - Detect #2-3 ranks across all lists
  - Apply configurable bonuses

- [ ] 2.2 Add bonus configuration to RankingConfig
  - enable_top_rank_bonus: bool
  - top1_bonus: float (0.05)
  - top3_bonus: float (0.02)

- [ ] 2.3 Integrate bonuses into ResultEnhancer flow
  - Apply after RRF or weighted sum
  - Conditional on config flag

- [ ] 2.4 Write unit tests for top-rank bonuses
  - Test #1 bonus application
  - Test #2-3 bonus application
  - Test multiple bonuses accumulating

## Phase 3: Position-Aware Blending

- [ ] 3.1 Create `_apply_position_blending()` method
  - Accept different blend weights for top3/mid/tail
  - Apply based on result rank

- [ ] 3.2 Add position blending configuration
  - enable_position_blending: bool
  - position_blends: Dict[str, Tuple[float, float]]

- [ ] 3.3 Integration with ResultEnhancer
  - Only apply if secondary scores exist
  - Graceful fallback if no reranker scores

- [ ] 3.4 Write unit tests for position blending
  - Test each tier boundary (1-3, 4-10, 11+)
  - Verify weight application

## Phase 4: Configuration & Integration

- [ ] 4.1 Update ConfigService to load ranking config from fmem.conf
  - Parse [ranking] section
  - Instantiate RankingConfig

- [ ] 4.2 Update EnhancerConfig in result_enhancer.py
  - Accept RankingConfig parameter
  - Pass through to ResultEnhancer

- [ ] 4.3 Update __init__.py exports
  - Export RankingConfig for external use

- [ ] 4.4 Write integration tests
  - End-to-end test with config file
  - Verify strategy switching works

## Phase 5: Documentation

- [ ] 5.1 Update API.md
  - Document RankingConfig options
  - Add example configurations
  - Explain RRF vs weighted_sum tradeoffs

- [ ] 5.2 Update README.md
  - Add section on advanced ranking
  - Link to QMD inspiration

- [ ] 5.3 Create example configuration
  - fmem.conf.example with ranking section

- [ ] 5.4 Update CHANGELOG.md
  - Document new ranking features

## Phase 6: Verification

- [ ] 6.1 Run full test suite
  - All existing tests pass
  - New tests pass

- [ ] 6.2 Manual testing
  - Test with real memory files
  - Compare weighted_sum vs RRF results
  - Verify backward compatibility

- [ ] 6.3 Benchmark
  - Compare ranking quality (precision@k)
  - Measure performance overhead

## Verification Checklist

- [ ] All tasks complete
- [ ] Tests pass (`pytest tests/test_integration.py`)
- [ ] Manual testing completed
- [ ] Documentation updated
- [ ] Backward compatibility verified
- [ ] Example configuration provided
- [ ] CHANGELOG updated
