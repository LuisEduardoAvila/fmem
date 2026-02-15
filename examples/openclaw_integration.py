#!/usr/bin/env python3
"""
OpenClaw Integration Example

Shows how to use fmem with OpenClaw's automatic recall system.
"""

from fmem.fmem_integration import auto_recall, format_results

# This would be called by OpenClaw when a trigger is detected
user_message = "Remember my project ideas from last week"

# Trigger automatic recall
context = auto_recall(
    query=user_message,
    query_type='semantic',  # or 'recency', 'location'
    max_results=3,
    chunk_mode='chunk'
)

# Format for display
formatted = format_results(context, format_type='openclaw')
print(formatted)
