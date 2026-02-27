# Specification: MCP Server

## Requirements

### REQ-001: MCP Protocol Compliance
**As a** Claude Desktop user  
**I want** fmem to implement the MCP protocol  
**So that** it can be registered as an MCP server in my IDE

#### Scenarios

##### SC-001: Protocol Handshake
**Given** MCP client initiates connection  
**When** server responds with capabilities  
**Then** server announces: tools list, no resources/prompts (Phase 1)

##### SC-002: Tool Listing
**Given** MCP client requests tool list  
**When** server responds  
**Then** returns JSON schema for all 6 tools with descriptions

##### SC-003: Tool Invocation
**Given** client calls `tools/fmemory_search`  
**When** server processes request  
**Then** executes search and returns results in MCP format

##### SC-004: Error Handling
**Given** invalid search parameters  
**When** tool execution fails  
**Then** returns MCP error response (not raw exception)

---

### REQ-002: Tool Implementations

#### Tool: fmemory_search
**Purpose:** Fast BM25/keyword search  
**Parameters:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| query | string | Yes | Search query |
| collection | string | No | Filter by collection |
| top_k | int | No | Number of results (default: 5) |
| min_score | float | No | Minimum relevance threshold |

**Returns:** List of documents with path, score, snippet

#### Tool: fmemory_vector_search
**Purpose:** Semantic vector search  
**Parameters:** Same as fmemory_search  
**Returns:** Semantically similar documents

#### Tool: fmemory_deep_search
**Purpose:** Hybrid search + reranking (best quality)  
**Parameters:** Same as above + expand_query bool  
**Returns:** High-quality results with LLM reranking

#### Tool: fmemory_get
**Purpose:** Retrieve specific document  
**Parameters:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| path | string | Yes | Document path or docid |
| line_start | int | No | Start line number |
| max_lines | int | No | Max lines to return |

**Returns:** Full document content with metadata

#### Tool: fmemory_multi_get
**Purpose:** Retrieve multiple documents  
**Parameters:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| paths | array | Yes | List of paths or globs |
| max_bytes | int | No | Skip files larger than N |

**Returns:** Multiple documents

#### Tool: fmemory_status
**Purpose:** Check index health  
**Parameters:** None  
**Returns:** Index stats, collection list, last indexed

---

### REQ-003: Transport Support

#### stdio Transport
**As a** Claude Desktop user  
**I want** MCP via stdio  
**So that** server runs as subprocess with no network port

**Scenario:**
- Client spawns: `fmem mcp`
- Server reads JSON-RPC from stdin
- Server writes JSON-RPC to stdout
- Server exits on stdin EOF

#### HTTP Transport (Optional)
**As a** multi-client user  
**I want** MCP via HTTP  
**So that** multiple clients share one server instance

**Scenario:**
- Server runs: `fmem mcp --http --port 8181`
- Endpoint: POST /mcp for MCP messages
- Endpoint: GET /health for liveness
- Supports persistent connections

---

### REQ-004: Error Handling

**Must handle:**
- Invalid JSON
- Missing required parameters
- Search timeout
- Index not found
- Malformed requests

---

## Protocol Schema

### Initialize Request
```json
{
  "jsonrpc": "2.0",
  "id": 0,
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {},
    "clientInfo": {"name": "claude", "version": "1.0"}
  }
}
```

### Initialize Response
```json
{
  "jsonrpc": "2.0",
  "id": 0,
  "result": {
    "protocolVersion": "2024-11-05",
    "capabilities": {"tools": {}},
    "serverInfo": {"name": "fmemory-mcp", "version": "3.2.0"}
  }
}
```
