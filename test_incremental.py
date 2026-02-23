#!/usr/bin/env python3
"""Test incremental batch indexing with resource monitoring"""
import os
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, 'src')
from fmem.fmem import MemoryRetrieval

def get_temp():
    try:
        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
            return int(f.read().strip()) / 1000
    except:
        return None

def run_pass(pass_num, memory):
    print(f"\n{'='*60}")
    print(f"PASS {pass_num}")
    print(f"{'='*60}")
    
    temp_before = get_temp()
    start = time.time()
    
    count = memory.index_directory_batched(
        '/home/luis/.openclaw/workspace/memory',
        max_files=3,
        batch_size=25
    )
    
    elapsed = time.time() - start
    temp_after = get_temp()
    
    # Get indexed files
    indexed = [d['filepath'] for d in memory.doc_metadata]
    
    print(f"\n📊 Results:")
    print(f"   Files indexed: {count}")
    print(f"   Time: {elapsed:.2f}s")
    print(f"   Temp: {temp_before:.1f}°C → {temp_after:.1f}°C" if temp_before else "   Temp: N/A")
    print(f"   Total chunks: {memory.index.ntotal if memory.index else 0}")
    print(f"   Indexed files: {[Path(f).name for f in indexed]}")
    
    return count, elapsed, indexed

def main():
    print("🧪 FMEM Incremental Indexing Test")
    
    # Pass 1
    memory1 = MemoryRetrieval()
    count1, time1, files1 = run_pass(1, memory1)
    
    # Pass 2 (fresh instance to test persistence)
    memory2 = MemoryRetrieval()
    count2, time2, files2 = run_pass(2, memory2)
    
    # Find new files
    new_files = [f for f in files2 if f not in files1]
    
    # Test query
    print(f"\n{'='*60}")
    print("QUERY TEST")
    print(f"{'='*60}")
    
    query = "session memory fmem"
    print(f"\nQuery: '{query}'")
    
    start = time.time()
    results = memory2.search(query, top_k=3)
    qt = time.time() - start
    
    print(f"Results ({len(results)} in {qt:.3f}s):")
    for i, r in enumerate(results[:3], 1):
        score = r.get('score', 0)
        fp = Path(r.get('filepath', 'unknown')).name
        preview = r.get('content', '')[:60].replace('\n', ' ')
        print(f"  {i}. [{score:.3f}] {fp}")
        print(f"     {preview}...")
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"✅ Pass 1: {count1} files in {time1:.2f}s")
    print(f"✅ Pass 2: {count2} files in {time2:.2f}s")
    print(f"✅ Total unique: {len(files2)} files")
    print(f"✅ New from Pass 2: {len(new_files)} files")
    print(f"✅ Query: {len(results)} results returned")
    
    if len(files2) >= 6:
        print("\n🎉 SUCCESS: Indexed 6+ files across 2 passes")
    else:
        print(f"\n⚠️  Only {len(files2)} files total (expected 6)")

if __name__ == "__main__":
    main()
