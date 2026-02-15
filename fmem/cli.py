#!/usr/bin/env python3
"""Command-line interface for fmem."""

import argparse
import sys
from .fmem import MemoryRetrieval

def main():
    parser = argparse.ArgumentParser(description='fmem - Local FAISS Memory Search')
    parser.add_argument('command', choices=['search', 'add', 'status', 'reset'],
                       help='Command to execute')
    parser.add_argument('query', nargs='?', help='Search query or file path')
    parser.add_argument('-k', '--top-k', type=int, default=5, help='Number of results')
    parser.add_argument('--chunk-mode', choices=['chunk', 'document', 'hybrid'],
                       default='chunk', help='Search mode')
    
    args = parser.parse_args()
    
    memory = MemoryRetrieval()
    
    if args.command == 'search':
        if not args.query:
            print("Error: search requires a query", file=sys.stderr)
            sys.exit(1)
        results = memory.search(args.query, top_k=args.top_k, chunk_mode=args.chunk_mode)
        for i, r in enumerate(results, 1):
            print(f"[{i}] Score: {r.get('score', 0):.3f}")
            if 'chunk_info' in r:
                print(f"    Section: {r['chunk_info'].get('heading', 'N/A')}")
            print(f"    {r.get('content', '')[:200]}...")
            print()
    
    elif args.command == 'add':
        if not args.query:
            print("Error: add requires a file path", file=sys.stderr)
            sys.exit(1)
        success = memory.add_document(args.query, chunk_by_sections=True)
        print(f"{'Added' if success else 'Failed to add'} {args.query}")
    
    elif args.command == 'status':
        print(f"Documents: {memory.get_document_count()}")
    
    elif args.command == 'reset':
        memory.reset()
        print("Memory reset complete")

if __name__ == '__main__':
    main()
