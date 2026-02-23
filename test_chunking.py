#!/usr/bin/env python3
"""Quick test of chunking"""
import sys
sys.path.insert(0, 'src')

from pathlib import Path
from fmem.fmem import chunk_markdown
import time

md_files = list(Path('/home/luis/.openclaw/workspace/memory').glob('*.md'))[:3]
print(f"Testing chunking on {len(md_files)} files...")

for f in md_files:
    print(f"\n{f.name}: {f.stat().st_size} bytes", end="", flush=True)
    content = f.read_text()
    print(" [read]", end="", flush=True)
    
    start = time.time()
    chunks = chunk_markdown(content, str(f), max_chunk_size=800)
    elapsed = time.time() - start
    print(f" [chunked: {len(chunks)} in {elapsed:.2f}s]")