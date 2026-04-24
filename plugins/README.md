# fmem Plugins

Plugins extend **fmem** with automatic integration into your OpenClaw workflow.

---

## Available Plugins

### openclaw-fmem-auto

Automatically injects relevant memories into your OpenClaw prompts — no manual recall needed.

**Hook:** `before_prompt_build`

The plugin hooks into OpenClaw's `before_prompt_build` lifecycle event. It uses `event.prompt` (the clean user message, pre-extracted by OpenClaw) as the primary input, falling back to parsing `event.messages` only as a secondary path. This avoids parsing envelope metadata that some providers attach.

Matching results are silently injected into the prompt context before the LLM processes your message, giving the model access to your stored knowledge without you having to ask for it.

#### Triggers

Memories are recalled based on four trigger types:

| Trigger | Description |
|---------|-------------|
| **Explicit** | User directly asks for memory (e.g., "look up", "recall", "remember", "show me") |
| **Recency** | User references time periods (e.g., "last week", "recently", "yesterday") |
| **Location** | User mentions a directory, path, or location category (e.g., "in docs", "under projects/") |
| **Context patterns** | User references personal context patterns (e.g., "my preferences", "my goals", workspace terms) |

#### Configuration

```yaml
plugins:
  entries:
    fmem-auto:
      enabled: true
      topK: 3          # Max memories to inject per prompt
      minScore: 0.25   # Minimum relevance score (0–1)
      timeoutMs: 5000  # Max time to wait for recall
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | boolean | `true` | Enable or disable auto-recall |
| `topK` | number | `3` | Maximum number of memories to inject |
| `minScore` | number | `0.25` | Minimum relevance score for a memory to be included |
| `timeoutMs` | number | `5000` | Timeout for recall queries (ms) |
#### Deduplication & Rate Limiting

To avoid noise and redundant lookups:

- **Deduplication:** Recalled memories are cached per-session with a **5-minute TTL**. The same memory won't be injected twice within that window.
- **Rate limiting:** Recall queries are limited to **1 per second** per session, preventing excessive lookups during rapid conversations.
- **Message length limit:** Messages longer than **10,000 characters** are skipped (DoS protection).
- **Content preview:** Injected memories show up to **150 characters** of content (adaptively up to 400 for single results).

#### Installation

1. Install the plugin: `openclaw plugin install fmem-auto`
2. Or manually: copy the `openclaw-fmem-auto` plugin directory to your OpenClaw workspace `plugins/` directory
3. OpenClaw loads TypeScript plugins directly — no build step required
4. Add the configuration block above to your OpenClaw config (`~/.openclaw/config.yaml`)
5. Restart OpenClaw (or reload plugins)

#### Custom Triggers

You can override any trigger category with your own patterns via config:

```yaml
plugins:
  entries:
    fmem-auto:
      triggers:
        explicit:
          - "look up"
          - "find"
          - "recall"
        recency:
          - "last week"
          - "yesterday"
        location:
          - "in docs"
          - "from projects"
        context:
          - "my preferences"
          - "my goals"
```

Any trigger category not specified in config falls back to the built-in defaults.

#### Usage

Once configured, the plugin works transparently — just chat as normal. Relevant memories will be automatically included in your prompt context based on the trigger rules.

To disable temporarily without removing the config:

```yaml
plugins:
  entries:
    fmem-auto:
      enabled: false
```

---

## More Information

See the [main README](../README.md) for full fmem documentation, API reference, and general usage.