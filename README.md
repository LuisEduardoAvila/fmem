# fmem — FAISS Memory Search — Technical Documentation

## Usage as Skill

The fmem skill is invoked from the command line:

### Basic Usage
```bash
# Search memory
fmem search "your query here"

# Add document to memory
fmem add /path/to/document.md

# Reset all memory
fmem reset
```

### Manual Search (Direct Invocation)
```bash
python3 fmem.py search "your query" -k 5
```

### Integration with OpenClaw
Once the skill is installed in your workspace, you can call it directly using the CLI interface.

**Example workflow:**
1. Populate memory: `fmem add /path/to/file.md`
2. Search results: `fmem search "query"`
3. Persist automatically on skill exit

---

## Dependencies

### Python Packages

| Package | Version | Purpose |
|---------|---------|---------|
| `faiss-cpu` | Latest | FAISS library for efficient vector similarity search |
| `nomic-embed` | Latest | Local embeddings via nomic-embed-text model |

### External Services

| Service | Required? | Endpoint | Purpose |
|---------|----------|----------|---------|
| Ollama | ✅ Yes | `http://127.0.0.1:11434` | Runs nomic-embed-text model locally |
| litellm | ✅ Yes | `http://127.0.0.1:11434/v1` | API gateway to Ollama for embeddings |

**Note:** No OpenAI, Pinecone, or cloud services required — fully offline.

## Installation Guide

### 1. Install Python Dependencies

```bash
pip install faiss-cpu
pip install nomic-embed
```

**Verify installation:**
```bash
python3 -c "import faiss; import nomic_embed; print('✓ All dependencies installed')"
```

### 2. Ensure Ollama Running

```bash
# Start Ollama if not running
ollama serve

# Pull nomic-embed-text model (if not already)
ollama pull nomic-embed-text
```

**Test litellm endpoint:**
```bash
curl http://127.0.0.1:11434/v1/models
```

Should list `nomic-embed-text` and `voytas26/openclaw-qwen3vl-8b-opt`.

### 3. Create Data Directory

```bash
mkdir -p /home/luis/.openclaw/memory/
chmod 755 /home/luis/.openclaw/memory/
```

FAISS index and metadata are stored here.

## Technical Architecture

### Data Flow

```
User Query → FAISS Memory Search → nomic-embed-text (embedding) → FAISS Index → Sorted Results
```

### FAISS Implementation

- **Index type:** IndexFlatIP (inner product) for cosine similarity
- **Embedding dimension:** 768 (nomic-embed-text)
- **Search method:** K-nearest neighbors (default k=5)
- **Storage:** Flat index with persistent disk storage
- **Memory footprint:** ~8KB index + metadata per document

### Memory Management

**Files Created:**
- `/home/luis/.openclaw/memory/faiss_index.fai` — Persistent FAISS index
- `/home/luis/.openclaw/memory/doc_metadata.json` — Document metadata

**Lifecycle:**
1. Index loads from disk if exists
2. Documents added for new queries
3. Embedding generated via litellm→Ollama
4. Search completes in <20ms (FAISS) + ~200ms (embedding)
5. Index saved on exit

## Performance Benchmarks (RPi)

| Operation | Expected Time | Notes |
|-----------|--------------|-------|
| First query (embed) | 100-200ms | Embedding in-flight |
| Subsequent queries | <20ms | Pure FAISS search |
| Add 100 docs | ~5-10s | Batch embedding generation |
| Memory (1k docs) | ~500KB | 768-dim × 1k embeddings |

**Optimizations:**
- Batch embedding generation (save on repeated queries)
- Pre-load common documents
- Cache embeddings in memory between runs

## Troubleshooting

### "ModuleNotFoundError: No module named 'faiss'"

**Solution:**
```bash
pip install faiss-cpu
```

### "No models found in Ollama"

**Solution:**
```bash
ollama pull nomic-embed-text
curl http://127.0.0.1:11434/v1/models
```

### FAISS Index Not Persisting

**Check:**
```bash
ls -lh /home/luis/.openclaw/memory/
```

Ensure directory writable:
```bash
chmod 755 /home/luis/.openclaw/memory/
```

### Embedding Too Slow

**Pre-load documents:**
```bash
fmem-add /home/luis/.openclaw/MEMORY.md
fmem-add /home/luis/.openclaw/workspace/projects/*/*.md
```

Then search without re-embedding.

## Development Notes

### Code Organization

```
fmem/
├── SKILL.md       # User-facing documentation
├── README.md     # This file — technical details
└── memory_search.py  # Core implementation module
```

### Testing

**Manual test:**
```bash
python3 -c "
from fmem.memory_search import MemoryRetrieval
import sys
sys.path.insert(0, '/home/luis/.openclaw/workspace/skills/fmem')

memory = MemoryRetrieval()
results = memory.search('test', top_k=3)
print(f'Found {len(results)} results')
"
```

**Integration test:**
```
fmem "test query"
```

## Future Enhancements

- [ ] Auto-recall triggers on chat tags
- [ ] Document auto-population (scan workspace automatically)
- [ ] Multi-language search (add cross-lingual embeddings)
- [ ] Personalized relevance weighting
- [ ] Document versioning

---

**Last Updated:** 2026-02-12
**Version:** 1.0.0
**Author:** SmartSpud (Bob)