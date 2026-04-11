# Specification: Advanced Ranking System

## Requirements

### REQ-001: RRF Fusion Algorithm
**As a** fmem user  
**I want** search results fused using Reciprocal Rank Fusion  
**So that** high-confidence matches from multiple ranking factors are preserved

#### Scenarios

##### SC-001: Basic RRF Calculation
**Given** three ranked lists from different scoring factors (semantic, recency, location)  
**When** RRF fusion is applied with k=60  
**Then** final scores = Σ(1/(k + rank + 1)) for each document across all lists

**Edge Cases:**
- Document appears in only one list: score = 1/(k + rank + 1)
- Document appears in all three lists: score = sum of three RRF scores
- Documents with same rank: handled by natural ordering

---

### REQ-002: Top-Rank Bonus System
**As a** fmem user  
**I want** documents ranking #1 in any factor to receive a score bonus  
**So that** high-confidence exact matches are boosted

#### Scenarios

##### SC-002: #1 Rank Bonus
**Given** a document ranks #1 in the semantic similarity list  
**When** top-rank bonus is applied  
**Then** document receives +0.05 bonus to final score

##### SC-003: #2-3 Rank Bonus
**Given** a document ranks #2 or #3 in any factor list  
**When** top-rank bonus is applied  
**Then** document receives +0.02 bonus to final score

---

### REQ-003: Position-Aware Blending
**As a** fmem user  
**I want** different weight blends based on result position  
**So that** top results preserve high-confidence retrieval signals

#### Scenarios

##### SC-004: Top 1-3 Position Weights
**Given** results ranked 1-3 by RRF  
**When** position-aware blending is applied  
**Then** blend is 75% retrieval score, 25% reranker (or other secondary signal)

##### SC-005: Position 4-10 Weights
**Given** results ranked 4-10 by RRF  
**When** position-aware blending is applied  
**Then** blend is 60% retrieval score, 40% reranker

##### SC-006: Position 11+ Weights
**Given** results ranked 11+ by RRF  
**When** position-aware blending is applied  
**Then** blend is 40% retrieval score, 60% reranker

---

### REQ-004: Backward Compatibility
**As a** fmem maintainer  
**I want** existing weighted sum ranking to remain available  
**So that** existing integrations continue working

#### Scenarios

##### SC-007: Configuration Selection
**Given** existing fmem configuration without ranking_strategy specified  
**When** search is performed  
**Then** weighted sum ranking is used (backward compatible default)

##### SC-008: Explicit RRF Selection
**Given** configuration with `ranking_strategy: "rrf"`  
**When** search is performed  
**Then** RRF fusion is used instead of weighted sum

---

## Configuration Schema

```python
class RankingConfig:
    """Configuration for multi-factor ranking."""
    
    strategy: Literal["weighted_sum", "rrf"] = "weighted_sum"
    """Ranking strategy to use."""
    
    # RRF specific
    rrf_k: int = 60
    """RRF hyperparameter (typically 20-100)."""
    
    # Top-rank bonuses
    top1_bonus: float = 0.05
    """Bonus for #1 rank in any factor."""
    
    top3_bonus: float = 0.02
    """Bonus for #2-3 ranks in any factor."""
    
    # Position-aware blending
    position_blends: Dict[str, Tuple[float, float]] = {
        "top3": (0.75, 0.25),    # (retrieval, reranker)
        "mid": (0.60, 0.40),     # positions 4-10
        "tail": (0.40, 0.60),    # positions 11+
    }
```
