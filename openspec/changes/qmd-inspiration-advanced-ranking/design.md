# Design: QMD-Inspired Advanced Ranking

## Overview

Implement advanced ranking features inspired by QMD's hybrid search pipeline. This change adds RRF fusion, top-rank bonuses, and position-aware blending as configurable alternatives to the current weighted sum approach.

## Architecture

### Component Changes

```
src/fmem/
├── result_enhancer.py          # Modified
│   └── ResultEnhancer
│       ├── _apply_weighted_sum()      # Existing
│       ├── _apply_rrf_fusion()        # NEW
│       ├── _apply_top_rank_bonuses() # NEW
│       └── _apply_position_blending()  # NEW
│
├── config.py                   # Modified
│   └── RankingConfig           # NEW configuration class
│
└── __init__.py                 # Modified
    └── Export RankingConfig
```

### Data Flow

```
Search Results (3 lists)
    ├── Semantic ranked list
    ├── Recency ranked list
    └── Location ranked list
           │
           ▼
    ┌──────────────────┐
    │   RRF Fusion     │  # Σ(1/(k+rank+1))
    │   (k=60)         │
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │  Top-Rank Bonus  │  # +0.05 for #1, +0.02 for #2-3
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │   Sort by Score  │
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │ Position-Aware   │  # Different blends by rank
    │ Blending         │
    └────────┬─────────┘
             │
             ▼
    Final Ranked Results
```

## Implementation Details

### 1. RRF Fusion Algorithm

```python
def reciprocal_rank_fusion(
    ranked_lists: List[List[Dict]],
    k: int = 60
) -> Dict[str, float]:
    """
    Apply RRF to combine multiple ranked lists.
    
    Formula: score = Σ(1 / (k + rank + 1))
    where rank is 1-indexed position in list.
    """
    scores = defaultdict(float)
    
    for ranked_list in ranked_lists:
        for rank, item in enumerate(ranked_list, start=1):
            doc_id = item['filepath']  # or chunk_id
            scores[doc_id] += 1.0 / (k + rank)
    
    return scores
```

### 2. Top-Rank Bonus

```python
def apply_top_rank_bonuses(
    rrf_scores: Dict[str, float],
    ranked_lists: List[List[Dict]],
    top1_bonus: float = 0.05,
    top3_bonus: float = 0.02
) -> Dict[str, float]:
    """Add bonuses for documents ranking #1 or #2-3 in any list."""
    bonuses = defaultdict(float)
    
    for ranked_list in ranked_lists:
        for rank, item in enumerate(ranked_list, start=1):
            doc_id = item['filepath']
            if rank == 1:
                bonuses[doc_id] += top1_bonus
            elif rank <= 3:
                bonuses[doc_id] += top3_bonus
    
    return {doc_id: rrf_scores[doc_id] + bonuses[doc_id] 
            for doc_id in rrf_scores}
```

### 3. Position-Aware Blending

```python
def apply_position_blending(
    results: List[Dict],
    blends: Dict[str, Tuple[float, float]]
) -> List[Dict]:
    """
    Apply different score blends based on result position.
    
    blends = {
        "top3": (0.75, 0.25),   # rank 1-3
        "mid": (0.60, 0.40),    # rank 4-10
        "tail": (0.40, 0.60),   # rank 11+
    }
    """
    for rank, result in enumerate(results, start=1):
        if rank <= 3:
            retrieval_weight, reranker_weight = blends["top3"]
        elif rank <= 10:
            retrieval_weight, reranker_weight = blends["mid"]
        else:
            retrieval_weight, reranker_weight = blends["tail"]
        
        # Apply blending if reranker score exists
        if "reranker_score" in result:
            result["final_score"] = (
                retrieval_weight * result["rrf_score"] +
                reranker_weight * result["reranker_score"]
            )
    
    return results
```

### 4. Configuration Changes

Add to `ConfigService`:

```python
@dataclass
class RankingConfig:
    strategy: str = "weighted_sum"  # or "rrf"
    rrf_k: int = 60
    enable_top_rank_bonus: bool = True
    top1_bonus: float = 0.05
    top3_bonus: float = 0.02
    enable_position_blending: bool = False
    position_blends: dict = field(default_factory=dict)
```

## Migration Strategy

**Brownfield Changes:**
1. Default strategy remains "weighted_sum" (no breaking changes)
2. New features opt-in via configuration
3. Existing clients continue working without changes
4. Documentation updated to describe new options

## Dependencies

No new dependencies required. Pure algorithmic changes using existing Python standard library.

## Testing Strategy

1. Unit tests for `_apply_rrf_fusion()` with known inputs
2. Unit tests for `_apply_top_rank_bonuses()`
3. Unit tests for `_apply_position_blending()`
4. Integration tests comparing weighted_sum vs RRF results
5. Benchmark tests verifying ranking quality improvements

## Open Questions

1. **Q:** Should RRF become the default strategy eventually?  
   **A:** After evaluation period (1-2 weeks), consider default switch if quality is demonstrably better.

2. **Q:** How to expose configuration to users?  
   **A:** Add `[ranking]` section to fmem.conf with strategy selection.

3. **Q:** Position-aware blending requires reranker - implement now or defer?  
   **A:** Implement structure now, but blending only activates if reranker scores present.
