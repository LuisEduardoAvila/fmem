# fmem Plugins

Plugins extend **fmem** with automatic integration into your OpenClaw workflow.

---

## Available Plugins

### openclaw-fmem-auto

Automatically injects relevant memories into your OpenClaw prompts — no manual recall needed.

**Hook:** `before_prompt_build`

The plugin intercepts each prompt before it's sent to the model and queries fmem for contextually relevant memories. Matching results are silently injected into the prompt context, giving the model access to your stored knowledge without you having to ask for it.

#### Triggers

Memories are recalled based on four trigger types:

| Trigger | Description |
|---------|-------------|
| **Explicit** | Direct mention of a memory topic in the prompt |
| **Recency** | Recently stored memories surface automatically |
| **Location** | Memories tagged with relevant locations or contexts |
| **Context patterns** | Semantic similarity between the prompt and stored memories |

#### Configuration

```yaml
plugins:
  entries:
    fmem-auto:
      enabled: true
      topK: 3          # Max memories to inject per prompt
      minScore: 0.25   # Minimum relevance score (0–1)
      timeoutMs: 500   # Max time to wait for recall
      gracefulDegradation: true  # Skip on error instead of failing
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | boolean | `true` | Enable or disable auto-recall |
| `topK` | number | `3` | Maximum number of memories to inject |
| `minScore` | number | `0.25` | Minimum relevance score for a memory to be included |
| `timeoutMs` | number | `500` | Timeout for recall queries (ms) |
| `gracefulDegradation` | boolean | `true` | If recall fails, continue without memories rather than erroring |

#### Deduplication & Rate Limiting

To avoid noise and redundant lookups:

- **Deduplication:** Recalled memories are cached per-session with a **5-minute TTL**. The same memory won't be injected twice within that window.
- **Rate limiting:** Recall queries are limited to **1 per second** per session, preventing excessive lookups during rapid conversations.

#### Installation

1. Copy the `openclaw-fmem-auto` plugin directory to your OpenClaw plugins path
2. Run `npm install` inside the plugin directory
3. Add the configuration block above to your OpenClaw config
4. Restart OpenClaw (or reload plugins)

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