# fmem Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              User Interface                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │  OpenClaw    │  │    CLI       │  │   Python API │  │  MCP Server │ │
│  │  Plugin      │  │  (fmem.cli)  │  │  (import)    │  │  (future)   │ │
│  │  (fmem-auto) │  │              │  │              │  │             │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘ │
└─────────┼──────────────────┼──────────────────┼──────────────────┼───────┘
          │                  │                  │                  │
          └──────────────────┴──────────────────┴──────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                            MemoryRetrieval Class                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────────┐ │
│  │   Config    │  │   Chunking  │  │   Search    │  │  Persistence   │ │
│  │   Manager   │  │  (Markdown) │  │  (FAISS)    │  │ (SQLite/FAISS) │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           Embedding Layer                                │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                     FastEmbed (Local ONNX)                          │ │
│  │         Model: sentence-transformers/all-MiniLM-L6-v2          │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. MemoryRetrieval Class

**Responsibility:** Central orchestrator for all memory operations

**Key Methods:**
- `add_document(filepath, content, chunk_by_sections)` - Index documents with chunking
- `search(query, top_k, chunk_mode)` - Semantic search with ranking
- `persist()` - Save index and metadata to disk
- `reset()` - Clear all data

**Architecture Pattern:** Facade - provides simplified interface to complex subsystem

### 2. Chunking System

**Responsibility:** Split documents into semantic sections

**Algorithm:**
1. Parse markdown by `##` headings
2. Create unique chunk IDs: `{filename}#{heading-slug}`
3. Extract keywords (top 5 words, 4+ chars)
4. Infer category from heading text
5. Count tokens (4 chars ≈ 1 token)

**Output:** `ChunkMetadata` objects with:
- `id`: Unique identifier
- `heading`: Section title
- `content`: Section text
- `keywords`: Extracted terms
- `category`: Inferred type
- `processed_content`: Preprocessed content for embedding (headings + summary, ~500 chars)
- `tokens`: Estimated count

### Chunk Size Constraint

**Model:** `all-minilm:22m`
- **Context length:** 512 tokens
- **Embedding dimension:** 384
- **Max content for embedding:** ~800 characters (~500 tokens safe)

**Processing:**
- Full chunk stored in FAISS (up to 800 chars)
- Preprocessed to ~500 chars before embedding (headings + summary)
- Fits within 512 token limit

### Hybrid Chunking Strategy (Table-Aware)

**Decision:** Conditional use of md2chunks based on content type

**Current Implementation:**
```python
if tables_found_in_content:
    # Use md2chunks_splitter - preserves table structure
    return md2chunks_split(content, ...)
else:
    # Use heading-based chunking - better section preservation
    return heading_based_chunking(content, ...)
```

**Rationale (Verified 2026-02-23):**

| Content Type | Method | Result | Quality |
|-------------|--------|--------|---------|
| **With tables** | md2chunks_split | Tables as atomic units, text around tables | ✅ Good - preserves table structure |
| **Without tables** | md2chunks_split | All content → 1 chunk, NO heading context | ❌ Poor - loses section hierarchy |
| **Without tables** | Heading-based | Content split by ## headings | ✅ Good - preserves sections |

**Test Results:**
- `extract_tables()` regex: ~0.04ms per file (negligible cost)
- md2chunks without tables: Loses all ## heading context
- Heading-based without tables: Preserves section structure

**Conclusion:** Architecture is correct. Conditional routing provides optimal chunking for each content type. The 0.04ms regex scan is not a bottleneck.

### 3. Multi-Factor Ranking

**Formula:**
```
Final Score = (Semantic × 0.5) + (Recency × 0.3) + (Location × 0.2)
```

**Semantic Score:**
- FAISS inner product similarity
- Range: 0.0 to 1.0

**Recency Score:**
- Exponential decay: `exp(-age/30 days)`
- Never below 0.1 (min_recency_score)
- Modified time from filesystem

**Location Score:**
- Directory-based weights (docs: 1.5x, projects: 1.3x, chats: 0.8x)
- Normalized to 0.0-1.0 range
- Case-insensitive path matching

### 4. Storage Layer

**FAISS Index:**
- Type: IndexIDMap + IndexFlatIP (inner product)
- Dimension: **384** (all-minilm:22m) (was 768 for nomic-embed-text legacy)
- Persistence: Binary file `faiss_index.fai`

**SQLite Database:**
- Tables: `documents`, `chunks`, `embeddings`
- Index on `parent_file` for fast chunk lookup
- Schema version tracking

**chunk_index_map:**
Critical mapping that links FAISS indices to documents/chunks:
- Maps FAISS index position → (filepath, chunk_id)
- Stored as JSON: `chunk_index_map.json`
- Essential for chunk-to-document resolution after search
- Maintained during indexing and loaded on startup

**JSON Metadata:**
- Document-level info (filepath, mtime, chunk_count)
- Separate from chunk metadata for efficiency
- Used for recency ranking and display

### 5. Embedding Cache

**Type:** LRU Cache with TTL
- Max size: 10,000 entries
- TTL: 1 hour
- Eviction: Least recently used

**Purpose:** Cache embeddings to avoid redundant model inference for identical text

### 6. Configuration System

**Hierarchy (highest priority first):**
1. Environment variables (FMEM_DATA_DIR, etc.)
2. Config file (~/.openclaw/memory/fmem.conf)
3. Default values

**Key Settings:**
- `data_dir`: Storage location
- `embedding_model`: FastEmbed model name (default: sentence-transformers/all-MiniLM-L6-v2)
- `max_file_size`: 50MB limit
- `extensions`: Whitelist (.md, .txt, .py, etc.)

## OpenClaw Plugin Architecture (fmem-auto)

The fmem-auto plugin is an OpenClaw plugin that automatically injects relevant memories into LLM context before prompt building. It bridges the gap between the user's conversation and fmem's retrieval engine, making memory recall transparent and automatic.

### Plugin Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    fmem-auto Plugin (TypeScript)                 │
│                                                                  │
│  ┌────────────┐  ┌──────────────┐  ┌────────────────────────┐   │
│  │  index.ts  │  │  triggers.ts │  │     fmem-client.ts     │   │
│  │  (entry)   │  │  (patterns)  │  │  (CLI bridge)          │   │
│  └─────┬──────┘  └──────┬───────┘  └───────────┬────────────┘   │
│        │                │                      │                │
│  ┌─────┴──────┐  ┌──────┴───────┐  ┌───────────┴────────────┐   │
│  │ Hook Reg.  │  │ Pattern Match│  │ runExec → fmem CLI     │   │
│  │ before_    │  │ regex/class  │  │ search / status        │   │
│  │ prompt_   │  │ based        │  │                        │   │
│  │ build     │  │              │  │                        │   │
│  └────────────┘  └──────────────┘  └────────────────────────┘   │
│                                                                  │
│  ┌────────────┐  ┌──────────────────────────────────────────┐    │
│  │  types.ts  │  │            formatter.ts                  │    │
│  │ (interfaces)│  │  Result → LLM context formatting       │    │
│  └────────────┘  └──────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### Component Details

#### `index.ts` — Entry Point & Hook Registration
- Registers the `before_prompt_build` hook with OpenClaw's plugin system
- This hook fires before the LLM prompt is built, allowing fmem to inject retrieved context
- Coordinates the trigger → search → format pipeline
- Exports the plugin manifest and lifecycle hooks

#### `triggers.ts` — Pattern Matching
- Determines whether a given user message should trigger a memory search
- Uses pattern-based matching (regex and/or classification) to avoid searching on every message
- Prevents unnecessary CLI calls for messages that don't benefit from memory recall (e.g., greetings, simple commands)
- Returns a boolean or extracted query string

#### `fmem-client.ts` — CLI Bridge
- Calls the fmem CLI via OpenClaw's `runExec` utility
- Constructs and executes: `fmem search "<query>" --json` (or equivalent)
- Parses CLI output (JSON) into structured result objects
- Handles errors gracefully (fmem not installed, index empty, CLI failures)

#### `formatter.ts` — Result Formatting
- Transforms raw search results into LLM-consumable context
- Formats results as `prependContext` — text injected before the user's message in the prompt
- Typically wraps results in `<retrieved_memory>` or similar delimiters
- Ensures output is concise enough for context windows while preserving relevance

#### `types.ts` — TypeScript Interfaces
- Defines shared type definitions used across the plugin
- Interfaces for search results, trigger configurations, plugin settings
- Ensures type safety between components

### Plugin Data Flow

```
User sends message
       │
       ▼
┌──────────────────────┐
│ OpenClaw Gateway     │
│ receives message     │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ before_prompt_build  │
│ hook fires           │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐     ┌────────────────────┐
│ triggers.ts          │────▶│ Pattern match      │
│ Should search?       │     │ against message    │
└──────────┬───────────┘     └────────────────────┘
           │
           │ Yes (trigger matched)
           ▼
┌──────────────────────┐     ┌────────────────────┐
│ fmem-client.ts       │────▶│ runExec:           │
│ Call fmem CLI        │     │ fmem search "..."  │
└──────────┬───────────┘     └────────────────────┘
           │
           ▼
┌──────────────────────┐
│ fmem Core            │
│ FAISS search →       │
│ ranked results       │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ formatter.ts         │
│ Format results as    │
│ prependContext       │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ OpenClaw builds     │
│ final prompt with   │
│ memory context      │
└──────────────────────┘
```

### Plugin Configuration

The plugin is registered in OpenClaw's plugin configuration:

```yaml
plugins:
  entries:
    - name: fmem-auto
      config:
        # Optional: override default trigger patterns
        # Optional: set max results to inject
        # Optional: configure prependContext format
```

### Plugin ↔ Core Interface Contract

The plugin communicates with fmem exclusively through the CLI — there is no direct Python API call from TypeScript. This boundary is intentional:

| Concern | Plugin Side (TS) | Core Side (Python) |
|---------|------------------|---------------------|
| Search invocation | `runExec("fmem search ...")` | `cli.py` → `MemoryRetrieval.search()` |
| Result format | Parses JSON stdout | Emits JSON via `--json` flag |
| Error handling | Catches non-zero exit codes | Returns structured error JSON |
| Index management | Not in scope (use CLI directly) | `fmem index`, `fmem status` |

**Benefits of CLI boundary:**
- Language isolation: No FFI or subprocess protocol complexity
- Version independence: Plugin and core can evolve separately
- Testability: Plugin can be tested with mocked CLI output
- Simplicity: Single well-defined interface contract

## Data Flow

### Indexing Flow

```
Document File
     │
     ▼
┌──────────────┐
│ Read Content │
│ (or provided)│
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Sanitize    │
│   Path       │
└──────┬───────┘
       │
       ▼
┌──────────────┐     ┌──────────────┐
│   Chunk by   │────▶│  Generate    │
│  Sections?   │     │  Embeddings  │
└──────────────┘     └──────┬───────┘
                            │
                            ▼
                     ┌──────────────┐
                     │  Store in    │
                     │ FAISS + DB   │
                     └──────────────┘
```

### Search Flow (CLI Direct)

```
Query String
     │
     ▼
┌──────────────┐
│  Validate    │
│  (length)    │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   Generate   │
│  Embedding   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  FAISS       │
│  Search      │
│  (top_k*2)   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   Enhance    │
│  (recency,   │
│  location)   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   Filter &   │
│    Sort      │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   Return     │
│   Results    │
└──────────────┘
```

### Search Flow (Plugin-Mediated)

```
User Message
     │
     ▼
┌──────────────────┐
│ OpenClaw Gateway │
│ receives message │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ before_prompt_   │
│ build hook       │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Trigger Detection│
│ (triggers.ts)    │
└──────┬───────────┘
       │
       │ Matched
       ▼
┌──────────────────┐
│ fmem search CLI  │
│ (fmem-client.ts) │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ FAISS Search +   │
│ Multi-Factor     │
│ Ranking          │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Format Results   │
│ (formatter.ts)   │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ prependContext   │
│ injected into    │
│ LLM prompt       │
└──────────────────┘
```

**Mermaid Visualization (Combined Flows):**

```mermaid
flowchart TB
    subgraph Plugin ["OpenClaw Plugin (fmem-auto)"]
        A[User Message] --> B[before_prompt_build Hook]
        B --> C{Trigger Detection}
        C -->|No match| X[Skip - no memory injection]
        C -->|Match| D[Extract Query]
    end

    subgraph CLI ["fmem CLI"]
        D --> E[fmem search --json]
        E --> F[Query Embedding]
    end

    subgraph Core ["fmem Core"]
        F --> G[FAISS Search]
        G --> H[Raw Results]
        H --> I[Multi-Factor Scoring]
        I --> J[Recency Boost]
        J --> K[Location Boost]
        K --> L[Final Ranking]
        L --> M[Top-k Results]
    end

    subgraph Output ["Plugin Output"]
        M --> N[formatter.ts]
        N --> O[prependContext]
        O --> P[LLM Prompt with Memory]
    end

    style I fill:#f9f, stroke:#333
    note right of I: Semantic: 50%\nRecency: 30%\nLocation: 20%
```

## Security Architecture

### Defense in Depth

1. **Path Validation**
   - `sanitize_path()`: Rejects `..`, absolute paths
   - Whitelist of allowed base directories
   - Symbolic link validation

2. **Input Sanitization**
   - Query length limit: 1000 chars
   - File size limit: 50MB
   - Extension whitelist

3. **SQL Injection Prevention**
   - Parameterized queries only
   - No string interpolation in SQL

4. **Embedding Safety**
   - Content size validation before embedding
   - Batch processing for efficiency
   - Model error handling

### Trust Boundaries

- **Inside fmem:** Trusted (validated at entry points)
- **File System:** Untrusted (always validate paths)
- **FastEmbed:** Local execution (no external API)
- **User Input:** Untrusted (validate everything)
- **Plugin → CLI boundary:** Untrusted (CLI output parsed defensively)

### Plugin-Specific Security

- **CLI injection:** fmem-client.ts sanitizes query strings before passing to CLI
- **Output parsing:** formatter.ts validates structure of JSON output from CLI
- **Context injection:** prependContext is clearly delimited — LLM can distinguish memory from user input
- **Trigger gating:** Not every message triggers a search, limiting surface area

## Performance Characteristics

### Time Complexity

| Operation | Complexity | Notes |
|-----------|-----------|-------|
| Indexing | O(n) | n = chunks, linear embedding generation |
| Search | O(log n) | FAISS approximate search |
| Cache hit | O(1) | Hash lookup |
| Cache miss | O(n) | n = embedding dimension (384) |
| Plugin trigger check | O(1) | Pattern match against message |
| Plugin search call | O(log n) | CLI subprocess + FAISS search |

### Space Complexity

| Component | Size | Scaling |
|-----------|------|---------|
| FAISS Index | 4KB per vector | Linear with documents |
| SQLite DB | ~1KB per chunk | Linear with chunks |
| Embedding Cache | Max 30MB | Bounded (10k entries) |
| Metadata JSON | ~100B per doc | Linear with documents |
| Plugin prependContext | ~1-4KB | Bounded by top_k results |

### Bottlenecks

1. **Embedding Generation:** FastEmbed inference (local ONNX)
2. **FAISS Search:** Index size > 100k vectors
3. **File I/O:** Large files (>10MB)
4. **SQLite:** Without proper indexing on `parent_file`
5. **Plugin CLI subprocess:** `runExec` spawns a process per search — negligible for interactive use but not suitable for high-frequency batch scenarios

## Integration Patterns

### OpenClaw Plugin Integration (Primary)

The fmem-auto plugin is the primary integration path for OpenClaw agents. It provides transparent, automatic memory recall without requiring explicit CLI calls from the agent.

```
User Message
     │
     ▼
┌──────────────┐
│  before_     │
│  prompt_     │
│  build hook  │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  triggers.ts │
│  Match?      │
└──────┬───────┘
       │ Yes
       ▼
┌──────────────┐
│  fmem-client │
│  search CLI  │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  formatter   │
│  results →   │
│  context     │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ prependContext│
│ for LLM      │
└──────────────┘
```

**Advantages over manual CLI calls:**
- **Automatic:** No agent code needed to trigger searches
- **Transparent:** Memory context appears naturally in the prompt
- **Consistent:** Same trigger logic and formatting every time
- **Efficient:** Only fires when trigger patterns match

### CLI Integration

Direct Python API access via `fmem.cli` module:

**Commands:**
- `fmem index [directory]` - Index files (auto-indexes configured dirs if no argument)
- `fmem search "query" [-k N]` - Search memory
- `fmem status` - Show index status

**Implementation:**
- Arguments parsed with argparse
- Output: Formatted text or JSON
- Delegates to `MemoryRetrieval` methods

**CLI Architecture:**
```
CLI Command → argparse → cmd_handler() → MemoryRetrieval.method()
                                            ↓
                                      FAISS/SQLite operations
                                            ↓
                                      Formatted output
```

### Future MCP Integration

```
MCP Client (any)
     │
     │ JSON-RPC
     ▼
┌──────────────┐
│ MCP Server   │
│ (TypeScript) │
└──────┬───────┘
       │
       │ Subprocess
       ▼
┌──────────────┐
│ Python Bridge │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   fmem Core   │
└──────────────┘
```

## Extension Points

### Custom Ranking

Override `MemoryRetrieval._enhance_search_results()`:
```python
class CustomMemoryRetrieval(MemoryRetrieval):
    def _enhance_search_results(self, results):
        # Custom ranking logic
        return super()._enhance_search_results(results)
```

### Custom Chunking

Override `chunk_markdown()` function:
```python
def custom_chunker(content: str) -> List[ChunkMetadata]:
    # Custom splitting logic
    pass

memory.add_document(filepath, chunk_by_sections=False)
# Then manually chunk with custom_chunker
```

### Custom Embedding

Replace FastEmbed with custom provider:
```python
class CustomMemoryRetrieval(MemoryRetrieval):
    def _get_embedding(self, text: str) -> Optional[np.ndarray]:
        # Custom embedding generation
        pass
```

### Custom Plugin Triggers

Extend `triggers.ts` with new patterns:
```typescript
// Add domain-specific triggers
const customTriggers: TriggerPattern[] = [
  { pattern: /project status/i, queryExtractor: (msg) => `${msg} status` },
  { pattern: /how do we handle/i, queryExtractor: (msg) => msg },
];
```

### Custom Result Formatting

Override `formatter.ts` for different output styles:
```typescript
// Compact format for smaller context windows
function compactFormat(results: SearchResult[]): string {
  return results.map(r => `${r.heading}: ${r.content.slice(0, 100)}`).join('\n');
}
```

## Known Limitations

1. **Single-node only:** No distributed support
2. **Local filesystem only:** No network storage
3. **Synchronous only:** No async/await support
4. **English-optimized:** Token estimation assumes English text
5. **Local execution:** Runs on CPU (GPU acceleration not yet implemented)
6. **Plugin CLI subprocess:** Each search spawns a new process — not ideal for sub-millisecond latency requirements
7. **Trigger false positives/negatives:** Pattern-based trigger detection may miss edge cases; requires tuning

## Future Architecture (MCP Phase)

**Mermaid Visualization:**

```mermaid
graph TB
    subgraph Input [User Input]
        A[Query]
    end
    
    subgraph Plugin [OpenClaw Plugin (fmem-auto)]
        B[before_prompt_build]
        C[Trigger Detection]
        D[fmem-client.ts]
        E[formatter.ts]
    end
    
    subgraph Core [fmem Core]
        F[MemoryRetrieval]
        G[Chunk Index]
        H[FAISS Index]
        I[SQLite DB]
    end
    
    subgraph Output [Results]
        J[prependContext → LLM]
    end
    
    A --> B
    B --> C
    C -->|Triggers| D
    D --> F
    F --> G
    F --> H
    F --> I
    F --> E
    E --> J
```

**ASCII Visualization:**
```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Universal Clients                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │OpenClaw  │  │  Claude  │  │  VS Code │  │  Cursor  │  │   ...    │ │
│  │ Plugin   │  │          │  │          │  │          │  │          │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘ │
└───────┼─────────────┼─────────────┼─────────────┼─────────────┼───────┘
        │             │             │             │             │
        └─────────────┴─────────────┴─────────────┴─────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      MCP Protocol (JSON-RPC)                            │
└─────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       fmem (Unchanged Core)                              │
└─────────────────────────────────────────────────────────────────────────┘
```

## References

- FAISS Documentation: https://faiss.ai/
- FastEmbed: https://github.com/qdrant/fastembed
- MCP Specification: https://spec.modelcontextprotocol.io/
- all-MiniLM-L6-v2: https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2 (current, 384 dims)
- OpenClaw Plugin System: https://github.com/nickthecook/openclaw

---

**Last Updated:** 2026-04-22  
**Version:** 3.1.0  
**Architecture Owner:** fmem Development Team