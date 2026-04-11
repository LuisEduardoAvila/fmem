# Proposal: MCP Server Implementation

## Problem Statement

fmem is currently OpenClaw-specific, accessed via Python imports and exec() calls. This limits adoption:

1. **No Claude Desktop support**: Users can't use fmem with Claude Desktop
2. **No VS Code integration**: No IDE-native memory search
3. **No multi-client support**: Each client needs custom integration
4. **Protocol lock-in**: Tied to OpenClaw's specific calling convention

MCP (Model Context Protocol) is the emerging standard for AI tool integration, supported by Anthropic, OpenAI, and others. Implementing MCP makes fmem universally accessible.

## Success Criteria

- [ ] Implement MCP server with stdio transport
- [ ] Support MCP Streamable HTTP transport (optional but recommended)
- [ ] Expose at minimum 6 tools (search, vector_search, deep_search, get, multi_get, status)
- [ ] Handle MCP protocol handshake and capability negotiation
- [ ] Support graceful shutdown and error handling
- [ ] Provide installation instructions for Claude Desktop, VS Code, Claude Code
- [ ] Write comprehensive tests for MCP protocol compliance
- [ ] Document performance characteristics and limitations

## Out of Scope

- MCP resources (memory://status) - Phase 2
- MCP prompts ("Remember this" workflows) - Phase 2  
- WebSocket transport - Future consideration
- Authentication/authorization - Not needed for local-only tool

## Notes

**Inspiration:** QMD implements MCP natively with both stdio and HTTP transports. Their CLI doubles as MCP server via `qmd mcp`.

**Approach:** Python MCP SDK (fastmcp) is most mature. Creates FastAPI-like decorator-based server.

**Risk:** Medium-High - New protocol, potential SDK churn, requires careful error handling

**Effort Estimate:** 1-2 weeks for full implementation with testing and documentation.

**Architecture Decisions:**
- **Language:** Python (fmem is Python, keeps codebase unified)
- **Transport:** stdio (default) + HTTP (optional daemon mode)
- **SDK:** fastmcp (official SDK recommendation)
- **Entry Point:** `fmem mcp` CLI subcommand
