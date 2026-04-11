# Design: MCP Server Implementation

## Overview

Implement a Model Context Protocol (MCP) server for fmem using Python's fastmcp SDK. This enables universal client support (Claude Desktop, VS Code, OpenClaw) via standardized protocol.

## Architecture

### Component Structure

```
projects/fmem/
├── src/
│   └── fmem/
│       ├── mcp_server.py              # NEW - MCP server main
│       ├── tools/                     # NEW - Tool implementations
│       └── cli.py                     # Modified (add mcp subcommand)
├── mcp-wrapper/
│   └── README.md                     # Installation guide
└── pyproject.toml                     # Modified (add fastmcp)
```

### Architecture Decision: Python vs TypeScript

**Decision:** Use Python (fastmcp SDK) for unified codebase with fmem.

## Implementation

### 1. MCP Server Core

```python
# src/fmem/mcp_server.py
from fastmcp import FastMCP
from .memory_retrieval import MemoryRetrieval

mcp = FastMCP("fmemory")

@mcp.tool()
def fmemory_search(query: str, collection: str = None, top_k: int = 5) -> str:
    """Fast keyword search across indexed documents."""
    memory = MemoryRetrieval()
    results = memory.search(query=query, top_k=top_k)
    return _format_results(results)

@mcp.tool()
def fmemory_get(path: str, line_start: int = None) -> str:
    """Retrieve a specific document."""
    # Implementation...

@mcp.tool()
def fmemory_status() -> str:
    """Get fmem index status."""
    # Implementation...

def run_stdio():
    """Run MCP server in stdio mode."""
    mcp.run_stdio()

def run_http(host: str = "127.0.0.1", port: int = 8181):
    """Run MCP server in HTTP mode."""
    mcp.run_http(host=host, port=port)
```

### 2. CLI Integration

Add `fmem mcp` subcommand:
- `fmem mcp` - stdio mode
- `fmem mcp --http` - HTTP mode
- `fmem mcp --http --daemon` - Background daemon

### 3. Client Configurations

**Claude Desktop:**
```json
{
  "mcpServers": {
    "fmemory": {
      "command": "fmem",
      "args": ["mcp"]
    }
  }
}
```

## Dependencies

Add to pyproject.toml:
```toml
[project.optional-dependencies]
mcp = [
    "fastmcp>=0.4.0",
    "starlette>=0.20.0",
    "uvicorn>=0.20.0",
]
```

## Migration Strategy

**Brownfield:**
- MCP is additive - existing Python API unchanged
- CLI gains `mcp` subcommand - no breaking changes
- Optional dependency - `pip install fmem[mcp]`
- Backward compatible
