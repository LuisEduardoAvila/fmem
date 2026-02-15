#!/usr/bin/env python3
"""Basic usage example for fmem."""

from fmem import MemoryRetrieval

# Initialize memory system
memory = MemoryRetrieval()

# Add a document with chunk-level indexing
memory.add_document("my_notes.md", chunk_by_sections=True)

# Search using chunk mode for precise results
results = memory.search(
    "project ideas",
    top_k=3,
    chunk_mode='chunk'  # 'chunk', 'document', or 'hybrid'
)

# Display results
for result in results:
    print(f"Score: {result['score']:.3f}")
    if 'chunk_info' in result:
        print(f"Section: {result['chunk_info']['heading']}")
        print(f"Keywords: {result['chunk_info']['keywords']}")
    print(f"Content: {result['content'][:100]}...")
    print()
