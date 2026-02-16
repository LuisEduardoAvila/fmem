# MCP Wrapper for fmem - Rationale and Analysis

## Executive Summary

This document explains why a **Model Context Protocol (MCP) wrapper** is the optimal evolution path for fmem, transforming it from an OpenClaw-specific integration to a universal memory system accessible by multiple AI clients.

---

## Current State Analysis

### How fmem Works Today

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐
│   OpenClaw  │────▶│  fmem_integration │────▶│    fmem     │
│   Agent     │     │     (Python)       │     │   (Python)  │
└─────────────┘     └──────────────────┘     └─────────────┘
        │                                               │
        │           Direct exec() calls                  │
        │                                               ▼
        │                                     ┌─────────────┐
        └─────────────────────────────────────│   Ollama    │
                                              │  (Local)    │
                                              └─────────────┘
```

**Strengths:**
- ✅ Full Python ecosystem (FAISS, SQLite, Ollama)
- ✅ Zero external dependencies
- ✅ Complete control over implementation

**Limitations:**
- ❌ OpenClaw-specific (via exec tool)
- ❌ No native tool registration
- ❌ Not discoverable by other clients
- ❌ Manual integration required

---

## What is MCP?

**Model Context Protocol (MCP)** is an open standard developed by Anthropic that enables AI systems to connect to external data sources and tools through a standardized interface.

### MCP Core Concepts

| Concept | Description | fmem Mapping |
|---------|-------------|--------------|
| **Server** | Provides tools/resources | fmem-mcp-server |
| **Client** | Consumes tools (Claude, OpenClaw, etc.) | Any MCP-compatible client |
| **Tool** | Callable function with schema | `search_memory`, `add_document` |
| **Resource** | Readable data with URI | `memory://index/status` |
| **Prompt** | Template for common tasks | "Remember my projects" template |

### MCP Communication Flow

```
┌─────────────┐              ┌──────────────────┐              ┌─────────────┐
│   Client    │◄────────────▶│   MCP Server     │◄────────────▶│    fmem     │
│  (Any AI)   │   JSON-RPC   │   (TypeScript)    │   Python     │   Core      │
└─────────────┘   over stdio  └──────────────────┘   subprocess  └─────────────┘
        │                                               │
        │           Standard protocol                   ▼
        │                                     ┌─────────────┐
        └─────────────────────────────────────│   Ollama    │
                                              └─────────────┘
```

---

## Why MCP for fmem?

### 1. Universal Accessibility

**Current:** Only OpenClaw can use fmem  
**With MCP:** Any MCP-compatible client can use fmem

| Client | Without MCP | With MCP |
|--------|-------------|----------|
| OpenClaw | ✅ Via exec() | ✅ Native tool |
| Claude Desktop | ❌ No access | ✅ Full access |
| Claude Code | ❌ No access | ✅ Full access |
| VS Code (Cline) | ❌ No access | ✅ Full access |
| Other MCP clients | ❌ No access | ✅ Full access |

### 2. Standardized Discovery

**Current:** Agent must know fmem exists and how to call it  
**With MCP:** Client auto-discovers available tools

```json
// MCP tool schema (auto-discovered)
{
  "name": "search_memory",
  "description": "Search local memory using semantic similarity",
  "input_schema": {
    "query": "string",
    "top_k": "number (default: 5)",
    "chunk_mode": "enum: chunk|document|hybrid"
  }
}
```

### 3. Type Safety & Validation

**Current:** Python type hints only, no runtime validation  
**With MCP:** JSON Schema validation on all inputs

### 4. Ecosystem Growth

MCP adoption is accelerating:
- ✅ Anthropic (creator) - full support
- ✅ OpenAI - exploring integration
- ✅ Cursor - beta support
- ✅ Multiple community implementations

---

## Technical Architecture: MCP Wrapper

### Proposed Design

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         MCP Server (TypeScript)                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│  │   Tools     │  │  Resources  │  │   Prompts   │  │  Config Mgmt    │ │
│  │             │  │             │  │             │  │                 │ │
│  │ • search    │  │ • status    │  │ • Remember │  │ • port          │ │
│  │ • add_doc   │  │ • index     │  │ • Recall    │  │ • data_dir      │ │
│  │ • status    │  │ • stats     │  │ • Context   │  │ • ollama_url    │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ JSON-RPC over stdio
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      Python Bridge (fmem-mcp-bridge)                     │
│  • Wraps fmem core                                                     │
│  • Handles MCP protocol translation                                     │
│  • Manages subprocess communication                                     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ Python API calls
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          fmem Core (unchanged)                          │
│  • FAISS index                                                         │
│  • SQLite database                                                     │
│  • Chunking logic                                                      │
│  • Ollama embeddings                                                   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Why TypeScript for MCP Server?

**MCP SDK:** Official SDK is TypeScript-first
**Performance:** Lightweight, fast startup
**Ecosystem:** Best tooling and examples
**Compatibility:** Node.js runtime widely available

### Why Python Bridge?

**Reuse:** fmem core remains Python (no rewrite needed)
**Performance:** FAIFF + Ollama already optimized in Python
**Maintenance:** Single core codebase for both modes

---

## Implementation Approaches

### Approach 1: Full TypeScript Rewrite (NOT RECOMMENDED)

**Pros:**
- Single language
- Direct MCP SDK integration

**Cons:**
- Rewrite ~2000 lines of Python
- Lose FAISS optimizations
- Months of work
- Risk of bugs

### Approach 2: TypeScript Server + Python Subprocess (RECOMMENDED)

**Pros:**
- Keep existing fmem core
- Minimal code changes
- Fast implementation (~1 week)
- Low risk

**Cons:**
- Two processes to manage
- Slight overhead (JSON serialization)

### Approach 3: Pure Python MCP (Alternative)

**Pros:**
- Single language
- No subprocess overhead

**Cons:**
- No official MCP SDK in Python
- Community SDKs immature
- More maintenance burden

---

## Recommended Implementation

### Architecture: TypeScript MCP Server + Python Bridge

```typescript
// mcp-server.ts
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';

const server = new Server({
  name: 'fmem-mcp-server',
  version: '3.0.0'
}, {
  capabilities: {
    tools: {},
    resources: {},
    prompts: {}
  }
});

// Tool: search_memory
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  if (request.params.name === 'search_memory') {
    // Call Python bridge
    const result = await pythonBridge.search(
      request.params.arguments.query,
      request.params.arguments.top_k,
      request.params.arguments.chunk_mode
    );
    return { content: [{ type: 'text', text: JSON.stringify(result) }] };
  }
});
```

```python
# fmem-mcp-bridge.py
import sys
import json
from fmem import MemoryRetrieval

memory = MemoryRetrieval()

for line in sys.stdin:
    request = json.loads(line)
    
    if request['method'] == 'search':
        results = memory.search(
            request['params']['query'],
            top_k=request['params'].get('top_k', 5),
            chunk_mode=request['params'].get('chunk_mode', 'chunk')
        )
        response = {'result': results}
        print(json.dumps(response))
        sys.stdout.flush()
```

---

## Benefits Summary

| Benefit | Impact | Priority |
|---------|--------|----------|
| Multi-client support | High | 🔴 Critical |
| Standardized interface | High | 🟡 High |
| Auto-discovery | Medium | 🟡 High |
| Type safety | Medium | 🟢 Medium |
| Ecosystem growth | Long-term | 🟢 Medium |

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| MCP standard changes | Low | Medium | Abstract protocol layer |
| Performance overhead | Medium | Low | Benchmark before/after |
| Maintenance burden | Medium | Medium | Clear separation of concerns |
| Adoption delays | Medium | Low | Keep existing integration |

---

## Conclusion

**MCP wrapper is the optimal evolution path for fmem.**

It provides:
1. ✅ Universal accessibility (not just OpenClaw)
2. ✅ Standardized interface (industry adoption)
3. ✅ Minimal implementation effort (bridge pattern)
4. ✅ Preserved core investment (Python fmem unchanged)

**Recommendation:** Implement MCP wrapper as Phase 3 of fmem roadmap, maintaining current OpenClaw integration as primary until MCP adoption matures.

---

## Next Steps

1. **Prototype:** Basic MCP server with 1-2 tools
2. **Test:** Integration with Claude Desktop
3. **Validate:** Performance benchmarks
4. **Document:** Usage guide for multiple clients
5. **Release:** Beta to early adopters

See [IMPLEMENTATION.md](./IMPLEMENTATION.md) for detailed implementation plan.
