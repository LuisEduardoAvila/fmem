#!/usr/bin/env python3
"""Command-line interface for fmem."""

import argparse
import sys

try:
    # Try relative import first (for package use)
    from .fmem import MemoryRetrieval, __version__
except ImportError:
    # Fall back to absolute import (for running as module)
    from fmem.fmem import MemoryRetrieval, __version__


def main():
    parser = argparse.ArgumentParser(description='fmem - Local FAISS Memory Search')
    parser.add_argument('command', choices=['search', 'add', 'status', 'reset', 'health', 'version'],
                       help='Command to execute')
    parser.add_argument('query', nargs='?', help='Search query or file path')
    parser.add_argument('-k', '--top-k', type=int, default=5, help='Number of results')
    parser.add_argument('--chunk-mode', choices=['chunk', 'document', 'hybrid'],
                       default='chunk', help='Search mode')
    
    args = parser.parse_args()
    
    # Handle version command (no initialization needed)
    if args.command == 'version':
        print(f"fmem version {__version__}")
        sys.exit(0)
    
    # Initialize memory for other commands
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
        status = memory.get_status()
        print(f"Documents: {status.get('document_count', 0)}")
        print(f"Index exists: {status.get('index_exists', False)}")
        print(f"Database: {status.get('database_path', 'N/A')}")
    
    elif args.command == 'reset':
        success = memory.reset()
        print("Memory reset complete" if success else "Failed to reset memory")
    
    elif args.command == 'health':
        is_healthy = memory.health_check()
        if is_healthy:
            print("✓ Health check passed")
            print("  - Ollama: reachable")
            print("  - Index: ready")
            print("  - Database: connected")
        else:
            print("✗ Health check failed", file=sys.stderr)
            print("  Check that Ollama is running and the index is accessible", file=sys.stderr)
            sys.exit(1)


if __name__ == '__main__':
    main()
