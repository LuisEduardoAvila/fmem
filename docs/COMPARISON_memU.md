# fmem vs memU: Architecture Comparison

## Overview

Both fmem and memU are memory systems for AI agents, but they have fundamentally different approaches and design philosophies.

| Aspect | **fmem** | **memU** |
|--------|----------|----------|
| **Primary Use Case** | Reactive memory retrieval for conversational agents | 24/7 proactive agent memory |
| **Trigger Model** | User-message triggers (reactive) | Continuous background monitoring (proactive) |
| **Cost Focus** | Zero-cost with local Ollama | Reduces LLM token costs through caching |
| **Privacy** | 100% local, no external APIs | Cloud or self-hosted (PostgreSQL) |
| **Architecture** | FAISS + SQLite | Hierarchical 3-layer system |
| **Deployment** | Python library, CLI, OpenClaw integration | Python library, cloud API, hosted service |

---

## Key Differences

### 1. Trigger Model

**fmem: Reactive**
```
User Message → OpenClaw → should_search() → fmem.search() → Response with context
```
- OpenClaw decides when to search based on trigger words ("remember", "what about")
- Searches only happen when patterns match
- Low computational cost, efficient

**memU: Proactive (Always-On)**
```
Continuous Loop: Monitor → Memorize → Predict → Act
                           ↑___________↓
```
- Background memU Bot continuously monitors all interactions
- Automatically extracts facts, skills, preferences
- Predicts user intent before explicit queries

**Verdict:** fmem is simpler and lower-cost; memU is more powerful but computationally expensive

---

### 2. Memory Organization

**fmem: Semantic Chunking**
- Documents split by `##` headings
- Chunks stored in FAISS with embeddings
- Multi-factor ranking: semantic (50%) + recency (30%) + location (20%)
- Flat search across all chunks

**memU: Hierarchical File System**
```
memory/
├── preferences/
│   ├── communication_style.md
│   └── topic_interests.md
├── relationships/
│   ├── contacts/
│   └── interaction_history/
├── knowledge/
│   ├── domain_expertise/
│   └── learned_skills/
└── context/
    ├── recent_conversations/
    └── pending_tasks/
```
- Three layers: Resource → Item → Category
- File system metaphor for organization
- Cross-references between related memories

**Verdict:** fmem is flatter and simpler; memU is more structured for complex relationships

---

### 3. Cost Model

**fmem: Zero-Cost Priority**
- Local Ollama embeddings (no API fees)
- Local FAISS vector search (no cloud costs)
- Queries only on trigger words (not every message)
- Designed for homelab/Pi deployment

**memU: Token Cost Optimization**
- Cloud API option (pay per request)
- Caches insights to reduce redundant LLM calls
- Commercial pricing for enterprise
- Reduces costs vs naive continuous LLM queries

**Verdict:** fmem is cheaper for self-hosters; memU manages costs better for commercial use

---

### 4. Integration Model

**fmem: OpenClaw-Native**
```python
# AGENTS.md integration
from fmem import auto_recall, should_search

if should_search(user_message):
    context = auto_recall(user_message)
    # context injected into prompt
```
- Designed specifically for OpenClaw
- Simple API: `auto_recall(query, top_k=3)`
- Returns formatted `<retrieved_memory>` block

**memU: Multi-Agent Support**
```python
# Standalone proactive agent
import memu

bot = memu.Bot()
bot.monitor(agent.input_output_pairs)
bot.memorize(extract_insights)
bot.predict(user_intent)
bot.run_proactive_tasks()
```
- Supports multiple agent frameworks
- Cloud API for easy integration
- Also mentions OpenClaw ("moltbot, clawdbot") as alternative

**Verdict:** fmem is optimized for OpenClaw; memU is more framework-agnostic

---

### 5. Technology Stack

| Component | fmem | memU |
|-----------|------|------|
| **Embeddings** | Ollama (local) all-minilm:22m | OpenAI API |
| **Vector Store** | FAISS (in-memory + persistence) | PostgreSQL + pgvector |
| **Database** | SQLite + JSON files | PostgreSQL |
| **Chunking** | Markdown `##` headings + hybrid table handling | Content-type based extraction |
| **LLM Dependencies** | None (except optional indexing) | Required for extraction |

---

### 6. Unique Strengths

**fmem strengths:**
- ✅ Zero external dependencies
- ✅ Works offline (privacy-first)
- ✅ Simple, predictable API
- ✅ Chunk-level retrieval with section context
- ✅ Designed for resource-constrained environments (Pi)

**memU strengths:**
- ✅ Proactive intelligence without user prompts
- ✅ Automatic skill/knowledge extraction
- ✅ Commercial-grade with cloud option
- ✅ Intent prediction capabilities
- ✅ Built for 24/7 production deployment

---

## When to Use Which

### Use **fmem** when:
- You want 100% local, private memory
- Running on resource-constrained hardware (Raspberry Pi)
- Priority is keeping costs at zero
- OpenClaw is your primary framework
- Reactive (query-based) retrieval is sufficient

### Use **memU** when:
- Building commercial 24/7 agent applications
- Need proactive intelligence (anticipating user needs)
- Have budget for API costs or self-hosted infrastructure
- Require automatic skill/knowledge extraction
- Multi-agent framework support needed

---

## Potential Learning Points for fmem

From memU's approach:

1. **Proactive Memory:** Could add optional pre-fetch based on conversation context
2. **Hierarchical Organization:** Categories/tags beyond flat chunk storage
3. **Autonomous Actions:** Update todolists or prepare context automatically

From fmem's approach:

1. **Cost Efficiency:** memU could investigate local embedding models
2. **Open Source Simplicity:** fmem's zero-dependency design is valuable
3. **Chunk Structure:** Preservation of document structure (`##` headings)

---

## Conclusion

Both projects serve the same high-level goal (memory for AI agents) but with different trade-offs:

- **fmem:** Lean, local, economical, OpenClaw-optimized
- **memU:** Feature-rich, proactive, commercial-grade, framework-agnostic

Choose based on whether you prioritize **simplicity + zero-cost** (fmem) or **automation + power** (memU).
