# Specification: Query Expansion Service

## Requirements

### REQ-001: Query Variant Generation
**As a** fmem user  
**I want** search queries expanded with semantically equivalent variants  
**So that** I find documents using different terminology

#### Scenarios

##### SC-001: Basic Expansion
**Given** user query "how to deploy"  
**When** QueryExpansionService generates variants  
**Then** returns ["how to deploy", "how to release application", "deployment process"]

##### SC-002: Terminology Expansion
**Given** user query "auth error"  
**When** QueryExpansionService generates variants  
**Then** returns variants including "authentication error", "login problem", "sign-in failure"

##### SC-003: Conceptual Expansion
**Given** user query "error handling"  
**When** QueryExpansionService generates variants  
**Then** returns variants including "exception management", "fault tolerance", "error recovery"

---

### REQ-002: Configurable Expansion Count
**As a** fmem maintainer  
**I want** configurable number of query variants  
**So that** users can balance recall vs performance

#### Scenarios

##### SC-004: Minimal Expansion
**Given** configuration with `max_variants: 1`  
**When** query expansion runs  
**Then** only 1 variant generated (2 total queries including original)

##### SC-005: Aggressive Expansion
**Given** configuration with `max_variants: 3`  
**When** query expansion runs  
**Then** up to 3 variants generated (4 total queries)

---

### REQ-003: Smart Query Detection
**As a** fmem user  
**I want** short/simple queries skipped automatically  
**So that** unnecessary LLM calls are avoided

#### Scenarios

##### SC-006: Short Query Skip
**Given** user query "meeting" (single word)  
**When** query expansion check runs  
**Then** expansion skipped, original query used only

##### SC-007: Long Query Expand
**Given** user query "deployment process for staging environment" (4+ words)  
**When** query expansion check runs  
**Then** expansion proceeds with variant generation

---

### REQ-004: Cost and Performance Controls
**As a** fmem admin  
**I want** token budgets and timeouts for expansion  
**So that** runaway costs or hangs are prevented

#### Scenarios

##### SC-008: Token Budget
**Given** configuration with `expansion_token_limit: 100`  
**When** variant generation exceeds 100 tokens  
**Then** request cancelled, fallback to original query only

##### SC-009: Timeout Protection
**Given** configuration with `expansion_timeout: 2.0` seconds  
**When** LLM response takes >2 seconds  
**Then** timeout triggered, fallback to original query

---

### REQ-005: Result Deduplication
**As a** fmem user  
**I want** documents found from multiple variants appear once  
**So that** results aren't cluttered with duplicates

#### Scenarios

##### SC-010: Duplicate Handling
**Given** document found from both original query and variant 1  
**When** results are fused  
**Then** document appears once with highest score across all queries

##### SC-011: Score Aggregation
**Given** document scores 0.9 from original query, 0.7 from variant  
**When** deduplication runs  
**Then** document retains score 0.9 (highest)

---

## LLM Prompt Schema

```
You are a query expansion assistant. Given a search query, generate {n} semantically 
equivalent variants that might be used to find the same information.

Original query: "{query}"

Rules:
- Preserve original meaning
- Use synonyms and alternative phrasing
- Include relevant technical terms if applicable
- Each variant should be 3-10 words

Output format: JSON array of strings only.

{examples}

Response:
```

**Example Few-Shot:**
```json
{
  "examples": [
    {"original": "how to deploy", "variants": ["application release process", "deployment guide"]},
    {"original": "auth error", "variants": ["authentication failure", "login problem"]}
  ]
}
```
