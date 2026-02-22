# FMEM Ranking System Issues - Analysis & Fixes

## Summary of Issues Found

### 🔴 CRITICAL: Double Recency Weight Application

**Problem:** Recency weight is applied twice, reducing effective weight from 0.3 to 0.09

**Location:** 
1. `_calculate_recency_score()` line 1577: Returns `recency_score * recency_weight`
2. `_enhance_search_results_with_recency()` line 1616-1617: Multiplies by `recency_weight` again

**Impact:** Recency has only 30% of intended influence on rankings

**Fix:** Remove pre-weighting in `_calculate_recency_score()`:
```python
# Current (BUG):
return max(recency_score * recency_weight, self.config.min_recency_score)

# Fixed:
return max(recency_score, self.config.min_recency_score)
```

---

### 🟡 HIGH: Location Weight First-Match Inconsistency

**Problem:** Path `/projects/docs/` returns 1.3 (projects) not 1.5 (docs)

**Root Cause:** `split(os.sep)` iterates path parts in order, returns first match

**Current Code (line 1657):**
```python
for part in path_parts:
    if part in self.config.location_weights:
        return self.config.location_weights[part]  # Returns FIRST match
```

**Impact:** Nested directories get parent's weight instead of child's weight

**Fix:** Iterate in reverse order:
```python
for part in reversed(path_parts):
    if part in self.config.location_weights:
        return self.config.location_weights[part]  # Returns MOST SPECIFIC match
```

---

### 🟡 HIGH: Lowest Location Weight Contributes Zero

**Problem:** Chats (0.8) normalizes to 0.0 → contributes 0% to final score

**Current Normalization:**
```python
normalized_location = (location_weight - loc_min) / loc_range
# (0.8 - 0.8) / 0.7 = 0.0
```

**Impact:** Low-priority directories get NO location boost whatsoever

**Fix:** Adjust normalization to give minimum contribution:
```python
normalized_location = (location_weight - loc_min) / loc_range
if loc_min < 1.0:
    normalized_location = normalized_location * 0.5 + 0.5  # Map 0.5-1.0 range
```

Or alternatively, use additive scoring instead of multiplicative.

---

### 🟢 MEDIUM: Order-Dependent Enhancement

**Problem:** Location enhancement uses recency-enhanced score as base

**Flow:**
1. FAISS returns: `score = 0.7`
2. Recency enhancement: `score = 0.565` (recency-enhanced)
3. Location enhancement: Uses `result.get('semantic_score', result['score'])`

**Current Code (line 1693):**
```python
semantic_score = result.get('semantic_score', result['score'])
```

**Issue:** If `semantic_score` wasn't set by recency enhancement, it falls back to already-enhanced score

**Fix:** Pass semantic_score through all enhancements explicitly

---

### 🟢 MEDIUM: Missing Score Transparency in Results

**Problem:** User can't see how scores were calculated

**Current:** Results only show final `score`

**Should Show:**
- `semantic_score` (FAISS raw)
- `recency_score` (0-1 based on age)
- `location_weight` (raw weight)
- `location_normalized` (0-1 for scoring)
- `final_score` (combined)

---

## Recommended Fix Order

1. **Fix double recency weight** (critical - affects all rankings)
2. **Fix location first-match** (high - affects nested directories)
3. **Add score debugging** (medium - helps diagnose issues)
4. **Review location normalization** (medium - consider additive approach)

## Test Cases to Add

```python
def test_recency_not_double_weighted():
    # Recency weight 0.3 should contribute 0.3 to final, not 0.09
    pass

def test_nested_directory_weight():
    # /projects/docs/ should use docs weight, not projects
    pass

def test_lowest_weight_not_zero():
    # chats/ should contribute something, not 0%
    pass

def test_semantic_score_preserved():
    # After recency enhancement, semantic_score should remain original FAISS score
    pass
```