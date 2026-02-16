# MCP Wrapper Implementation Plan

## Phase 3: MCP Server Development

**Timeline:** 1-2 weeks (after Phase 1-2 complete)  
**Complexity:** Medium  
**Risk:** Low (bridge pattern preserves existing code)

---

## Project Structure

```
projects/fmem/mcp-wrapper/
├── README.md                 # Quick start guide
├── package.json              # Node.js dependencies
├── tsconfig.json             # TypeScript config
├── src/
│   ├── server.ts             # MCP server main entry
│   ├── tools/
│   │   ├── search.ts         # search_memory tool
│   │   ├── add-document.ts   # add_document tool
│   │   ├── get-status.ts     # get_status tool
│   │   └── index.ts          # Tool registration
│   ├── resources/
│   │   ├── status.ts         # memory://status resource
│   │   ├── index-info.ts     # memory://index resource
│   │   └── index.ts          # Resource registration
│   ├── prompts/
│   │   ├── remember.ts       # "Remember this" prompt
│   │   ├── recall.ts         # "Recall previous" prompt
│   │   └── index.ts          # Prompt registration
│   ├── bridge/
│   │   ├── python-bridge.ts  # Subprocess management
│   │   ├── protocol.ts       # JSON-RPC protocol
│   │   └── types.ts          # Shared type definitions
│   └── config/
│       ├── loader.ts         # Configuration loading
│       └── validation.ts     # Config validation
├── python-bridge/
│   ├── fmem-mcp-bridge.py    # Python bridge entry
│   ├── handlers/
│   │   ├── search.py         # Search handler
│   │   ├── add_document.py   # Add document handler
│   │   └── status.py         # Status handler
│   └── protocol.py           # Protocol parsing
└── tests/
    ├── unit/                 # Unit tests
    └── integration/          # Integration tests
```

---

## Week 1: Core MCP Server

### Day 1-2: Project Setup

```bash
# Initialize project
cd projects/fmem/mcp-wrapper
npm init -y
npm install @modelcontextprotocol/sdk typescript @types/node

# Create tsconfig.json
npx tsc --init
```

**Deliverable:** Project structure with build pipeline

### Day 3-4: Basic Server

```typescript
// src/server.ts
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

const transport = new StdioServerTransport();
await server.connect(transport);
console.error('fmem MCP server running on stdio');
```

**Deliverable:** Server starts and responds to initialization

### Day 5-7: Python Bridge

```python
# python-bridge/fmem-mcp-bridge.py
import sys
import json
from fmem import MemoryRetrieval

class MCPBridge:
    def __init__(self):
        self.memory = MemoryRetrieval()
    
    def handle(self, request):
        method = request.get('method')
        params = request.get('params', {})
        
        if method == 'search':
            return self.memory.search(
                params['query'],
                top_k=params.get('top_k', 5),
                chunk_mode=params.get('chunk_mode', 'chunk')
            )
        elif method == 'add_document':
            return self.memory.add_document(
                params['filepath'],
                chunk_by_sections=params.get('chunk_by_sections', True)
            )
        # ... etc
        
        raise ValueError(f"Unknown method: {method}")

if __name__ == '__main__':
    bridge = MCPBridge()
    for line in sys.stdin:
        request = json.loads(line)
        try:
            result = bridge.handle(request)
            response = {'id': request['id'], 'result': result}
        except Exception as e:
            response = {'id': request['id'], 'error': str(e)}
        
        print(json.dumps(response))
        sys.stdout.flush()
```

**Deliverable:** Bridge communication working

---

## Week 2: Tools & Integration

### Day 8-10: Tool Implementation

**Tools to implement:**

1. `search_memory`
   ```typescript
   {
     name: 'search_memory',
     description: 'Search local memory using semantic similarity',
     inputSchema: {
       type: 'object',
       properties: {
         query: { type: 'string', description: 'Search query' },
         top_k: { type: 'number', default: 5 },
         chunk_mode: { 
           type: 'string', 
           enum: ['chunk', 'document', 'hybrid'],
           default: 'chunk'
         }
       },
       required: ['query']
     }
   }
   ```

2. `add_document`
3. `get_status`
4. `reset_memory`

**Deliverable:** All tools functional via MCP

### Day 11-12: Resources & Prompts

**Resources:**
- `memory://status` - System status
- `memory://index/info` - Index statistics
- `memory://config` - Current configuration

**Prompts:**
- `remember_this` - "Remember this conversation"
- `recall_previous` - "Recall my previous work on..."

**Deliverable:** Complete MCP capabilities

### Day 13-14: Testing & Documentation

**Testing:**
```bash
# Unit tests
npm test

# Integration with Claude Desktop
echo '{"method": "search", "params": {"query": "test"}}' | npm start

# Performance benchmark
python3 benchmark/mcp-vs-direct.py
```

**Documentation:**
- Usage guide for Claude Desktop
- Configuration for OpenClaw
- Troubleshooting

**Deliverable:** Beta release ready

---

## Configuration

### MCP Server Config (for clients)

```json
{
  "mcpServers": {
    "fmem": {
      "command": "node",
      "args": ["/path/to/fmem/mcp-wrapper/dist/server.js"],
      "env": {
        "FMEM_DATA_DIR": "~/.openclaw/memory/",
        "FMEM_OLLAMA_URL": "http://localhost:11434"
      }
    }
  }
}
```

### For Claude Desktop

```json
// ~/Library/Application Support/Claude/claude_desktop_config.json
{
  "mcpServers": {
    "fmem": {
      "command": "node",
      "args": ["/home/luis/.openclaw/workspace/projects/fmem/mcp-wrapper/dist/server.js"]
    }
  }
}
```

### For OpenClaw

```yaml
# OpenClaw config
plugins:
  entries:
    fmem-mcp:
      kind: mcp-client
      command: node
      args:
        - /home/luis/.openclaw/workspace/projects/fmem/mcp-wrapper/dist/server.js
```

---

## Testing Strategy

### Unit Tests

```typescript
// tests/unit/search.test.ts
import { searchTool } from '../../src/tools/search';

describe('search_memory tool', () => {
  it('should return results for valid query', async () => {
    const result = await searchTool.handler({
      query: 'test',
      top_k: 3
    });
    expect(result.content).toHaveLength(1);
  });
  
  it('should validate chunk_mode', async () => {
    await expect(
      searchTool.handler({ query: 'test', chunk_mode: 'invalid' })
    ).rejects.toThrow();
  });
});
```

### Integration Tests

```bash
# Start server and test via stdio
echo '{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}' | \
  node dist/server.js

# Expected: List of available tools
```

### Performance Tests

```python
# benchmark/mcp-vs-direct.py
import time
import subprocess

# Direct call
direct_start = time.time()
# ... call fmem directly ...
direct_time = time.time() - direct_start

# MCP call
mcp_start = time.time()
# ... call via MCP ...
mcp_time = time.time() - mcp_start

print(f"Overhead: {(mcp_time/direct_time - 1)*100:.1f}%")
# Acceptable if < 20% overhead
```

---

## Rollout Plan

### Phase A: Internal Testing (1 week)
- [ ] Test with Claude Desktop
- [ ] Test with OpenClaw
- [ ] Performance validation
- [ ] Bug fixes

### Phase B: Beta Release (1 week)
- [ ] GitHub release (pre-release)
- [ ] Documentation published
- [ ] Community feedback

### Phase C: Full Release
- [ ] Merge to main
- [ ] Announcement
- [ ] Update all documentation

---

## Success Criteria

| Metric | Target | Measurement |
|--------|--------|-------------|
| Tool response time | < 500ms | Average over 100 calls |
| MCP overhead | < 20% | vs direct Python calls |
| Error rate | < 1% | Over 1000 operations |
| Code coverage | > 80% | Unit + integration tests |
| Documentation | Complete | All tools documented |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| MCP standard changes | Keep abstraction layer thin |
| Performance issues | Benchmark early, optimize if needed |
| Complexity explosion | Start minimal, add incrementally |
| Maintenance burden | Clear separation TS/Python |

---

## Conclusion

This implementation plan provides a **low-risk, incremental path** to MCP compatibility while preserving the existing fmem investment.

**Estimated effort:** 80-100 hours (2 weeks full-time, or 4-6 weeks part-time)

**Outcome:** fmem accessible by any MCP-compatible client, including OpenClaw, Claude Desktop, VS Code extensions, and future clients.
