# Session End Routine

## Overview

The session end routine is a Python script that automatically summarizes key decisions from daily memory files and writes them to the permanent MEMORY.md file at the end of each session.

## Purpose

- **Decisions Extraction**: Automatically identifies key decisions from daily memory files
- **Clean Memory Management**: Only finalized decisions go into permanent memory (MEMORY.md)
- **Token Efficiency**: Reduces memory bloat by filtering out raw chatter
- **Automated Workflow**: Runs automatically at session end (no manual intervention required)

## How It Works

### 1. Daily Content Scan
- Scans for today's daily memory file (e.g., `memory/2026-02-23.md`)
- Extracts raw content from daily files
- Parses for key decisions and action items

### 2. Decision Filtering
- Identifies decision-making phrases ("decided to", "chose", "will implement", etc.)
- Filters out conversational chatter
- Prioritizes action items and commitments

### 3. MEMORY.md Update
- Appends new section to permanent memory
- Adds timestamp and summary
- Preserves historical context
- Maintains clean, organized structure

## Usage

### Manual Run (for testing)
```bash
python3 session-end.py
```

### Cron Integration (automatic)
```bash
# Run at end of daily session
0 22 * * * cd /home/luis/.openclaw/workspace && /usr/bin/python3 session-end.py
```

### API Integration
```python
from session_end import SessionEndRoutine

routine = SessionEndRoutine()
summary = routine.generate_summary(daily_content)
print(summary)
```

## Configuration

The routine can be customized via `memory-session-end-config.md`:

- **Output File**: Where to write the summary (default: `MEMORY.md`)
- **Topic Filters**: Prioritize certain topics (e.g., "memory", "system")
- **Summary Length**: Control output verbosity
- **Time Filters**: Only include content from specific time ranges

## Example Output

```markdown
### 2026-02-23

- **Memory System v2.0** — Implemented time-gated scanner (30-minute delay) and session end routine
- **Google API Integration** — Setup Gmail/Calendar APIs with OAuth 2.0
- **Pathogen Identification** — Completed requirement analysis and SSH configuration
```

## Integration with Memory System v2.0

The session end routine completes the memory system workflow:

1. **During Conversation**: Content auto-saves to daily files
2. **Scanner (30-minute delay)**: Indexes content >30 minutes old
3. **Session End**: Extracts decisions and writes to MEMORY.md
4. **Result**: Clean, permanent memory with only key decisions

## Error Handling

- **Missing File**: Gracefully handles missing daily memory files
- **Empty Content**: Outputs minimal summary when no decisions found
- **Permission Issues**: Logs errors and exits cleanly
- **Encoding Problems**: Assumes UTF-8 encoding for all memory files

## Files

- `session-end.py` - Main routine script
- `memory-session-end-config.md` - Configuration file
- `SESSION-END.md` - This documentation

## Dependencies

- Python 3.8+
- Standard library only (no external dependencies)
- Compatible with system Python (/usr/bin/python3)