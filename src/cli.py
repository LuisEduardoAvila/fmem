#!/usr/bin/env python3
"""Simple CLI for fmem memory search."""

import argparse
import sys
from fmem import MemoryRetrieval

def main():
    parser = argparse.ArgumentParser(description="Search memory with fmem")
    parser.add_argument("query", help="Search query")
    parser.add_argument("-k", "--top-k", type=int, default=5, help="Number of results")
    parser.add_argument("-d", "--directory", help="Directory to search")
    
    args = parser.parse_args()
    
    try:
        memory = MemoryRetrieval()
        
        if args.directory:
            print(f"Indexing {args.directory}...")
            memory.index_directory(args.directory)
        
        results = memory.search(args.query, top_k=args.top_k)
        
        for i, r in enumerate(results, 1):
            print(f"\n{i}. Score: {r['score']:.3f}")
            print(f"   Source: {r['source']}")
            print(f"   {r['content'][:200]}...")
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
