# Solutions for fmem Recency Ranking Limitation

## Executive Summary

**Problem**: fmem uses file-level recency (last modified time), causing outdated information in frequently-updated files (like MEMORY.md) to rank higher than newer information in less-frequently-touched files (like project docs).

**Current Architecture Weaknesses**:
1. Single `last_modified` timestamp per file stored in SQLite `documents` table
2. Chunks table has no timestamp columns - relies on parent file's timestamp
3. No content provenance tracking
4. No distinction between "file was touched" vs "content was actually new"

---

## Solution 1: Section-Level Timestamp Annotation

### Approach
Parse and extract timestamps embedded within section headings or content, treating each section as having its own recency independent of file modification time.

### Implementation

**1.1 Add `chunk_created_at` column to chunks table:**
```sql
ALTER TABLE chunks ADD COLUMN chunk_created_at INTEGER;
ALTER TABLE chunks ADD COLUMN chunk_updated_at INTEGER;
```

**1.2 Timestamp Detection Strategy:**
```python
SECTION_TIMESTAMP_PATTERNS = [
    # Explicit timestamps in headings
    r'## .*?\[(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2})\]',  # ## Heading [2024-01-15T10:30]
    r'## (\d{4}-\d{2}-\d{2})[ :-]',                       # ## 2024-01-15 Session
    r'## .*?(\d{4}-\d{2}-\d{2})',                         # ## Session Notes 2024-01-15
    
    # Session patterns (daily files)
    r'Session (\d{4}-\d{2}-\d{2})',
    r'(\d{4}-\d{2}-\d{2}) Session',
    
    # Git commit style (from git blame integration)
    r'<!-- timestamp: (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z?) -->',
]
```

**1.3 Modified chunk creation with timestamp extraction:**
```python
def chunk_markdown_with_timestamps(content: str, filepath: str, file_mtime: float):
    chunks = chunk_markdown(content, filepath)  # existing function
    
    for chunk in chunks:
        # Try to extract timestamp from heading or content
        chunk_timestamp = extract_timestamp_from_chunk(chunk)
        
        if chunk_timestamp:
            chunk.created_at = chunk_timestamp
        else:
            # Fallback: use file mtime, but mark as "inherited"
            chunk.created_at = file_mtime
            chunk.timestamp_source = 'file_mtime'
    
    return chunks
```

**1.4 Modified recency calculation:**
```python
def _calculate_chunk_recency_score(self, chunk_created_at: float, 
                                    file_modified_at: float) -> float:
    """
    Calculate recency using chunk timestamp when available,
    with confidence weighting based on timestamp source.
    """
    import time
    current_time = time.time()
    
    # Use chunk timestamp (more accurate) weighted higher
    chunk_age_days = (current_time - chunk_created_at) / (24 * 60 * 60)
    chunk_score = max(0.1, 1.0 - (chunk_age_days / self.config.recency_threshold_days))
    
    # Use file timestamp as secondary signal
    file_age_days = (current_time - file_modified_at) / (24 * 60 * 60)
    file_score = max(0.1, 1.0 - (file_age_days / self.config.recency_threshold_days))
    
    # Weighted combination: prefer chunk timestamp (70%) over file (30%)
    return 0.7 * chunk_score + 0.3 * file_score
```

### Pros
- **Non-invasive**: Works with existing markdown patterns (daily session files already have dates)
- **Backward compatible**: Falls back to file mtime when no timestamp found
- **Zero migration**: Existing files work without modification
- **Transparent**: Users can see timestamps in their files

### Cons
- **Inconsistent coverage**: Not all sections have extractable timestamps
- **Manual burden**: Requires users to add timestamps for best results
- **Ambiguity**: Same content copied to MEMORY.md inherits wrong timestamp
- **False positives**: Date patterns in content may be misinterpreted

### Implementation Complexity: **Low-Medium** (2-3 days)
- Database migration: simple column additions
- Parser changes: moderate - regex pattern matching
- Indexer changes: low - pass timestamps during chunk creation
- Search changes: low - use chunk timestamp in recency calculation

---

## Solution 2: Content Provenance Fingerprinting

### Approach
Track when specific content first appeared using content hashing. When content is copied between files, it retains its original timestamp, preventing the "copy problem" where MEMORY.md shows outdated info as recent.

### Implementation

**2.1 New provenance table:**
```sql
CREATE TABLE content_provenance (
    content_hash TEXT PRIMARY KEY,  -- SHA256 of normalized content
    first_seen_at INTEGER,          -- When this content first appeared
    source_file TEXT,               -- Original file where content appeared
    source_chunk_id TEXT,           -- Original chunk ID
    appearance_count INTEGER DEFAULT 1,
    last_seen_at INTEGER
);

CREATE INDEX idx_content_hash ON content_provenance(content_hash);
CREATE INDEX idx_first_seen ON content_provenance(first_seen_at);
```

**2.2 Content normalization for hashing:**
```python
def normalize_content_for_hashing(content: str) -> str:
    """
    Normalize content to detect duplicates despite minor edits.
    """
    # Lowercase
    normalized = content.lower()
    
    # Remove punctuation except semantic ones
    normalized = re.sub(r'[^\w\s#-]', '', normalized)
    
    # Normalize whitespace
    normalized = ' '.join(normalized.split())
    
    # Remove timestamps (they change but content doesn't)
    normalized = re.sub(r'\d{4}-\d{2}-\d{2}', '', normalized)
    normalized = re.sub(r'\d{2}:\d{2}(?::\d{2})?', '', normalized)
    
    return normalized

def compute_content_fingerprint(content: str) -> str:
    """Compute hash of normalized content for provenance tracking."""
    normalized = normalize_content_for_hashing(content)
    return hashlib.sha256(normalized.encode()).hexdigest()[:32]
```

**2.3 Modified chunk storage with provenance:**
```python
def _store_chunk_with_provenance(self, chunk: ChunkMetadata, 
                                  file_mtime: float) -> bool:
    """Store chunk with content provenance tracking."""
    
    # Compute content fingerprint
    content_hash = compute_content_fingerprint(chunk.content)
    
    # Check if this content has been seen before
    cursor = self.conn.cursor()
    cursor.execute(
        "SELECT first_seen_at, source_file FROM content_provenance WHERE content_hash = ?",
        (content_hash,)
    )
    row = cursor.fetchone()
    
    if row:
        # Content already exists - use original timestamp
        provenance_time = row['first_seen_at']
        source_file = row['source_file']
        
        # Update appearance count
        cursor.execute(
            """UPDATE content_provenance 
               SET appearance_count = appearance_count + 1,
                   last_seen_at = ?
               WHERE content_hash = ?""",
            (file_mtime, content_hash)
        )
    else:
        # New content - use current file time
        provenance_time = file_mtime
        source_file = chunk.parent_file
        
        # Insert new provenance record
        cursor.execute(
            """INSERT INTO content_provenance 
               (content_hash, first_seen_at, source_file, source_chunk_id, last_seen_at)
               VALUES (?, ?, ?, ?, ?)""",
            (content_hash, file_mtime, chunk.parent_file, chunk.id, file_mtime)
        )
    
    # Store chunk with provenance timestamp
    cursor.execute("""
        INSERT OR REPLACE INTO chunks 
        (chunk_id, parent_file, heading, content, keywords, category, 
         token_count, chunk_index, content_hash, provenance_time, timestamp_source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        chunk.id, chunk.parent_file, chunk.heading, chunk.content,
        ','.join(chunk.keywords), chunk.category, chunk.tokens, chunk.chunk_index,
        content_hash, provenance_time, 'provenance' if row else 'file_mtime'
    ))
    
    self.conn.commit()
    return True
```

**2.4 Search uses provenance time:**
```python
def _get_chunks_for_file_with_provenance(self, filepath: str) -> List[ChunkMetadata]:
    """Retrieve chunks with provenance timestamps."""
    cursor = self.conn.cursor()
    cursor.execute("""
        SELECT c.chunk_id, c.parent_file, c.heading, c.content, c.keywords,
               c.category, c.token_count, c.chunk_index, 
               COALESCE(c.provenance_time, c.chunk_created_at, ?) as recency_time,
               c.timestamp_source,
               p.source_file as original_source,
               p.appearance_count
        FROM chunks c
        LEFT JOIN content_provenance p ON c.content_hash = p.content_hash
        WHERE c.parent_file = ?
        ORDER BY c.chunk_index
    """, (file_mtime, filepath))
    
    # ... build ChunkMetadata with recency_time field
```

### Pros
- **Solves the copy problem**: Copied content retains original timestamp
- **Automatic**: No user action required
- **Detects duplication**: Knows when content is copied vs new
- **Source attribution**: Can show "originally from projects/ai-decision.md"

### Cons
- **Hash collisions**: Different content may normalize to same hash (rare but possible)
- **Edit sensitivity**: Minor edits create new hashes (loses continuity)
- **Storage overhead**: Additional table + hash computation
- **Computation cost**: Hashing every chunk during indexing

### Implementation Complexity: **Medium** (4-5 days)
- Schema changes: new table, indices
- Normalization logic: requires careful tuning
- Indexer changes: moderate - compute and check hashes
- Search changes: moderate - join with provenance table

---

## Solution 3: Multi-Factor Authority Ranking

### Approach
Instead of fighting with timestamps, explicitly weight sources by their authority/"ground truth" status. Project documentation > MEMORY.md for technical facts, regardless of modification time.

### Implementation

**3.1 Authority taxonomy:**
```yaml
# fmem.conf - Authority configuration
[authority_rules]
# Explicit authority levels (higher = more authoritative)
projects/ = 1.5          # Source of truth for technical decisions
docs/ = 1.4              # Formal documentation
decisions/ = 1.4         # Decision records
notes/ = 1.2             # Working notes
memory/ = 0.9            # Aggregated memory (less authoritative)
MEMORY.md = 0.8          # Copied summaries (least authoritative)
daily sessions = 0.9     # Session logs
```

**3.2 Enhanced scoring with authority:**
```python
class AuthorityConfig:
    """Authority-based ranking configuration."""
    
    AUTHORITY_PATTERNS = {
        # Path patterns to authority multipliers
        r'projects/': 1.5,
        r'docs?/': 1.4,
        r'decisions/': 1.4,
        r'notes?/': 1.2,
        r'memory/': 0.9,
        r'MEMORY\.md$': 0.8,
        r'memory/\d{4}-\d{2}-\d{2}\.md$': 0.9,  # Daily session files
    }
    
    # Semantic type authority (detected from content)
    TYPE_AUTHORITY = {
        'decision_record': 1.4,    # "We decided to use PyTorch"
        'implementation': 1.5,     # Code, technical specs
        'requirement': 1.3,        # "Must use PyTorch"
        'discussion': 0.9,         # "I think we should..."
        'summary': 0.8,          # "Last week we used TensorFlow"
    }

def calculate_authority_score(filepath: str, chunk_category: str, content: str) -> float:
    """
    Calculate authority score based on:
    1. File location (projects/ > memory/)
    2. Content type (decisions > discussions)
    3. Semantic signals ("decided", "implemented" > "thought", "considered")
    """
    score = 1.0  # Base
    
    # Location-based authority
    for pattern, weight in AuthorityConfig.AUTHORITY_PATTERNS.items():
        if re.search(pattern, filepath):
            score *= weight
            break
    
    # Content type authority (from chunk category + content analysis)
    if chunk_category in AuthorityConfig.TYPE_AUTHORITY:
        score *= AuthorityConfig.TYPE_AUTHORITY[chunk_category]
    
    # Semantic authority signals
    authority_keywords = ['decided', 'implemented', 'agreed', 'finalized', 'chosen', 'selected']
    discussion_keywords = ['thinking', 'considering', 'maybe', 'might', 'possibly', 'wondering']
    
    authority_count = sum(1 for kw in authority_keywords if kw in content.lower())
    discussion_count = sum(1 for kw in discussion_keywords if kw in content.lower())
    
    if authority_count > discussion_count:
        score *= 1.1
    elif discussion_count > authority_count:
        score *= 0.9
    
    return min(score, 2.0)  # Cap at 2x
```

**3.3 Three-factor scoring:**
```python
def _calculate_enhanced_score(self, result: Dict) -> float:
    """
    Combined scoring: Semantic + Recency + Authority
    """
    semantic_score = result['semantic_score']
    recency_score = result['recency_score']
    authority_score = result.get('authority_score', 1.0)
    
    # Weight configuration (must sum to 1.0)
    w_semantic = 0.5   # Base relevance
    w_recency = 0.25   # Temporal relevance
    w_authority = 0.25 # Source reliability
    
    # Authority acts as a multiplier on semantic score
    # A highly authoritative result with medium semantic match beats
    # a low-authority result with high semantic match
    adjusted_semantic = semantic_score * authority_score
    
    final_score = (
        adjusted_semantic * w_semantic +
        recency_score * w_recency +
        authority_score * w_authority
    )
    
    return final_score
```

### Pros
- **Solves semantic conflict**: Project docs naturally outrank MEMORY.md
- **Explicit priorities**: Clear rules about what sources matter
- **Configurable**: Users can adjust authority weights
- **No timestamp fighting**: Authority is orthogonal to recency
- **Handles stale MEMORY.md**: Old summaries rank lower by authority

### Cons
- **Manual configuration**: Requires setting up authority rules
- **Context dependent**: "Use PyTorch" might be outdated even in projects/
- **Binary nature**: Still doesn't capture "this specific section is outdated"
- **Overlaps location ranking**: Similar to existing location_weight feature

### Implementation Complexity: **Low-Medium** (2-3 days)
- Config changes: add authority patterns to fmem.conf
- Scoring changes: add authority calculation, adjust weighting formula
- Content analysis: optional - keyword matching for semantic signals
- Minimal database changes

---

## Solution 4: Temporal Knowledge Graph

### Approach
Architectural redesign: Instead of documents/chunks, model entities ("AI framework", "PyTorch", "TensorFlow") with temporal properties. Track when facts were asserted, modified, or superseded.

### Implementation

**4.1 Graph schema:**
```sql
-- Entities (concepts, not chunks)
CREATE TABLE entities (
    entity_id TEXT PRIMARY KEY,
    canonical_name TEXT,
    entity_type TEXT,  -- 'technology', 'decision', 'person', 'project'
    first_mentioned_at INTEGER,
    last_mentioned_at INTEGER
);

-- Facts/assertions about entities (temporal)
CREATE TABLE facts (
    fact_id TEXT PRIMARY KEY,
    entity_id TEXT,
    attribute TEXT,        -- "uses", "decided", "preferred"
    value TEXT,            -- "PyTorch", "TensorFlow"
    asserted_at INTEGER,     -- When this fact was first stated
    source_file TEXT,
    source_chunk_id TEXT,
    superseded_by TEXT,    -- fact_id that replaces this (NULL if current)
    confidence REAL,       -- 0.0-1.0 based on authority signals
    FOREIGN KEY (entity_id) REFERENCES entities(entity_id),
    FOREIGN KEY (superseded_by) REFERENCES facts(fact_id)
);

-- Entity mentions in chunks (links back to chunks)
CREATE TABLE entity_mentions (
    mention_id INTEGER PRIMARY KEY,
    entity_id TEXT,
    chunk_id TEXT,
    mention_type TEXT,  -- 'explicit', 'inferred', 'coreference'
    FOREIGN KEY (entity_id) REFERENCES entities(entity_id),
    FOREIGN KEY (chunk_id) REFERENCES chunks(chunk_id)
);
```

**4.2 Entity extraction (simplified):**
```python
def extract_entities_and_facts(content: str, timestamp: float, 
                                source: str) -> Tuple[List[Entity], List[Fact]]:
    """
    Extract entities and temporal facts from content.
    Uses simple patterns + LLM for complex cases.
    """
    
    # Pattern-based fact extraction
    fact_patterns = [
        # "We decided to use X"
        (r'(?:decided|chose|selected|agreed)\s+(?:to\s+)?(?:use|adopt|implement)\s+([A-Za-z]+)',
         'decision', 'uses'),
        
        # "We are using X"
        (r'(?:we are|we're|currently|now)\s+(?:using|running|on)\s+([A-Za-z]+)',
         'current_state', 'uses'),
        
        # "Switched from X to Y"
        (r'switched\s+from\s+(\w+)\s+to\s+(\w+)',
         'transition', None),
    ]
    
    entities = []
    facts = []
    
    for pattern, fact_type, attribute in fact_patterns:
        for match in re.finditer(pattern, content, re.IGNORECASE):
            if fact_type == 'transition':
                old_tech = match.group(1)
                new_tech = match.group(2)
                
                # Mark old fact as superseded
                entities.append(Entity(name=old_tech, type='technology'))
                entities.append(Entity(name=new_tech, type='technology'))
                
                facts.append(Fact(
                    entity_name=old_tech,
                    attribute='uses',
                    value=old_tech,
                    asserted_at=timestamp - 86400,  # Yesterday
                    superseded=True
                ))
                facts.append(Fact(
                    entity_name=new_tech,
                    attribute='uses',
                    value=new_tech,
                    asserted_at=timestamp,
                    current=True
                ))
            else:
                value = match.group(1)
                entities.append(Entity(name=value, type='inferred'))
                facts.append(Fact(
                    entity_name=value,
                    attribute=attribute or 'related',
                    value=value,
                    asserted_at=timestamp,
                    source=source
                ))
    
    return entities, facts
```

**4.3 Search with temporal reasoning:**
```python
def search_with_temporal_reasoning(query: str, top_k: int = 5) -> List[Dict]:
    """
    Search that understands temporal relationships between facts.
    """
    
    # Step 1: Extract query entities
    query_entities = extract_entities(query)
    
    # Step 2: Find current facts about these entities
    cursor = conn.cursor()
    cursor.execute("""
        SELECT f.*, e.canonical_name
        FROM facts f
        JOIN entities e ON f.entity_id = e.entity_id
        WHERE e.canonical_name IN (%s)
          AND f.superseded_by IS NULL  -- Only current facts
        ORDER BY f.asserted_at DESC
    """, [e.name for e in query_entities])
    
    # Step 3: For conflicting facts, use most recent
    current_facts = {}
    for row in cursor.fetchall():
        entity = row['canonical_name']
        if entity not in current_facts:
            current_facts[entity] = row
        else:
            # Keep most recent assertion
            if row['asserted_at'] > current_facts[entity]['asserted_at']:
                current_facts[entity] = row
    
    # Step 4: Find chunks containing current facts
    results = []
    for entity, fact in current_facts.items():
        cursor.execute("""
            SELECT c.*, f.confidence
            FROM chunks c
            JOIN entity_mentions em ON c.chunk_id = em.chunk_id
            JOIN facts f ON em.entity_id = f.entity_id
            WHERE f.fact_id = ?
            ORDER BY f.confidence DESC, c.chunk_created_at DESC
        """, (fact['fact_id'],))
        
        for row in cursor.fetchall():
            results.append({
                'chunk': row,
                'fact': fact,
                'entity': entity,
                'confidence': fact['confidence'],
                'recency': normalize_timestamp(fact['asserted_at'])
            })
    
    # Step 5: Rank by semantic + confidence + recency
    return rank_results(results)
```

### Pros
- **Fundamental solution**: Tracks facts through time, not just file timestamps
- **Conflict resolution**: "Use PyTorch" (yesterday) beats "Use TensorFlow" (last week)
- **Source transparency**: Shows fact provenance and when it was asserted
- **Inference capable**: Can answer "When did we switch from TensorFlow to PyTorch?"

### Cons
- **High complexity**: Major architectural change
- **Entity extraction**: Requires NLP/LLM for good accuracy
- **Maintenance burden**: Graph consistency, coreference resolution
- **Overkill for simple use case**: May be too sophisticated for current needs

### Implementation Complexity: **High** (3-4 weeks)
- Schema design: complex relational graph
- Entity extraction: requires LLM integration or complex NLP
- Inference engine: temporal reasoning logic
- Migration: complete data model change

---

## Solution 5: Semantic Disambiguation with Cross-Reference Validation

### Approach
When search finds similar content across multiple files, cross-reference to find contradictions and use temporal + source signals to determine which is "true".

### Implementation

**5.1 Cross-reference index:**
```python
class CrossReferenceIndex:
    """Index that tracks similar content across files."""
    
    def __init__(self):
        self.semantic_groups = {}  # embedding_hash -> [chunk_refs]
    
    def find_similar_chunks(self, chunk_embedding: np.ndarray, 
                            threshold: float = 0.85) -> List[ChunkRef]:
        """Find chunks with similar semantic meaning."""
        # Use FAISS to find near-duplicates
        D, I = self.index.search(chunk_embedding, k=10)
        return [self.chunks[i] for i, d in zip(I[0], D[0]) if d > threshold]
    
    def detect_contradictions(self, chunks: List[ChunkRef]) -> List[Contradiction]:
        """Detect when similar chunks have conflicting information."""
        contradictions = []
        
        # Look for chunks about same entity but with different values
        for i, chunk_a in enumerate(chunks):
            for chunk_b in chunks[i+1:]:
                if self.are_contradictory(chunk_a, chunk_b):
                    contradictions.append(Contradiction(
                        chunk_a=chunk_a,
                        chunk_b=chunk_b,
                        entity=extract_common_entity(chunk_a, chunk_b),
                        resolution=self.resolve_contradiction(chunk_a, chunk_b)
                    ))
        
        return contradictions
    
    def resolve_contradiction(self, chunk_a: ChunkRef, chunk_b: ChunkRef) -> ChunkRef:
        """
        Resolve which chunk to prefer when contradiction detected.
        Priority: Recency > Authority > Location
        """
        score_a = self._calculate_trust_score(chunk_a)
        score_b = self._calculate_trust_score(chunk_b)
        
        return chunk_a if score_a > score_b else chunk_b
    
    def _calculate_trust_score(self, chunk: ChunkRef) -> float:
        """Calculate trust score for a chunk."""
        scores = {
            'recency': chunk.recency_score * 0.3,
            'authority': chunk.authority_score * 0.3,
            'source_quality': chunk.source_quality * 0.2,
            'explicity': 0.2 if chunk.has_explicit_timestamp else 0.0
        }
        return sum(scores.values())
```

**5.2 Contradiction-aware search:**
```python
def search_with_validation(query: str, top_k: int = 5) -> List[Dict]:
    """
    Search that validates results against potential contradictions.
    """
    # Step 1: Get initial results
    initial_results = self._semantic_search(query, top_k=top_k*2)
    
    # Step 2: Group by semantic similarity
    groups = group_by_semantic_similarity(initial_results)
    
    # Step 3: For each group, check for contradictions
    validated_results = []
    
    for group in groups:
        if len(group) == 1:
            validated_results.append(group[0])
        else:
            # Multiple similar results - resolve contradictions
            contradictions = self.cross_ref.detect_contradictions(group)
            
            if contradictions:
                # Pick the "winning" version based on resolution
                winner = contradictions[0].resolution
                
                # Add metadata about the conflict
                winner['conflict_detected'] = True
                winner['alternative_sources'] = [
                    c.chunk_b.to_dict() for c in contradictions
                ]
                winner['resolution_reason'] = contradictions[0].resolution_reason
                
                validated_results.append(winner)
            else:
                # No contradiction, pick most recent
                validated_results.append(max(group, key=lambda x: x['recency_score']))
    
    return validated_results[:top_k]
```

### Pros
- **Detects the problem**: Finds when MEMORY.md contradicts projects/
- **Automatic resolution**: Picks "correct" version without user intervention
- **Transparency**: Shows when conflicts were detected and how resolved
- **Builds on existing**: Uses current chunking + scoring

### Cons
- **False positives**: May flag non-contradictions as conflicts
- **Computational cost**: Double search + contradiction detection
- **Complexity**: Requires sophisticated contradiction detection
- **Edge cases**: Ambiguous statements hard to classify as contradictory

### Implementation Complexity: **Medium-High** (5-7 days)
- Similarity detection: FAISS-based near-duplicate finding
- Contradiction detection: requires NLP/LLM for semantic understanding
- Resolution logic: moderate complexity
- UI changes: display conflict information

---

## Recommendation: Hybrid Approach (Solutions 1 + 3 + 5)

### Why This Combination?

The recency problem has multiple dimensions that require different solutions:

1. **Content-level timestamps** (Solution 1) solve the easy cases where timestamps are explicit
2. **Authority ranking** (Solution 3) handles the semantic hierarchy (projects > memory)
3. **Cross-reference validation** (Solution 5) catches contradictions the other methods miss

### Phased Implementation

**Phase 1: Section-Level Timestamps + Authority (1 week)**
- Add `chunk_created_at` column to chunks table
- Implement timestamp extraction from headings
- Add authority configuration to fmem.conf
- Modify scoring to use chunk timestamps when available

**Phase 2: Content Provenance (1 week)**
- Add content fingerprinting for copy detection
- Track original source when content is copied
- Store provenance metadata

**Phase 3: Cross-Reference Validation (1 week)**
- Implement semantic similarity grouping
- Add contradiction detection for high-similarity chunks
- Show conflict warnings in search results

### Final Architecture

```
Search Query
    ↓
Semantic Search (FAISS) → Candidate Chunks
    ↓
Temporal Scoring
    ├─ Use chunk timestamp (if explicit in heading)
    ├─ Use provenance time (if content copied)
    └─ Fallback to file mtime
    ↓
Authority Scoring
    ├─ Location-based (projects/ > memory/)
    ├─ Content-type (decisions > discussions)
    └─ Semantic signals ("decided" > "thinking")
    ↓
Cross-Reference Validation
    ├─ Group similar chunks
    ├─ Detect contradictions
    └─ Resolve using temporal + authority signals
    ↓
Final Ranking
    ├─ Score = Semantic * 0.4 + Temporal * 0.3 + Authority * 0.3
    └─ Deduplicate by content hash
    ↓
Results with Metadata
    ├─ Show: source file, timestamp, authority
    └─ Optional: conflict warnings
```

### If Building From Scratch

For a greenfield implementation, I'd design around **Solution 4 (Temporal Knowledge Graph)** but with pragmatic simplifications:

1. **Entity-centric model**: Track "facts" not "chunks"
2. **Lightweight extraction**: Pattern-based entity/fact extraction, not full NLP
3. **Temporal integrity**: Every fact has an asserted timestamp and superseded relationship
4. **Source provenance**: Track origin of every fact
5. **Query-time resolution**: When query matches multiple facts about same entity, return most recent non-superseded

This avoids the "file as unit of recency" problem entirely by making the fact the atomic unit with its own temporal properties.

---

## Summary Comparison

| Solution | Solves Core Problem | Complexity | Migration Effort | User Burden | Recommendation |
|----------|---------------------|------------|------------------|-------------|----------------|
| 1. Section Timestamps | Partial (explicit only) | Low-Medium | Low | Low | **Implement First** |
| 2. Content Provenance | Yes (copies) | Medium | Medium | None | **Phase 2** |
| 3. Authority Ranking | Yes (hierarchy) | Low | Low | Low | **Implement First** |
| 4. Temporal Graph | Yes (fundamental) | High | High | None | Long-term vision |
| 5. Cross-Reference | Yes (detection) | Medium-High | Medium | None | **Phase 3** |

**Immediate Recommendation**: Implement **Solution 1 + Solution 3** together for maximum impact with minimal complexity.
