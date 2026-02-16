#!/usr/bin/env python3
"""Simple CLI for fmem memory search."""

import argparse
import sys
from pathlib import Path

from . import fmem


def cmd_index(args):
    """Index a directory of files."""
    try:
        memory = fmem.MemoryRetrieval()
        directory = Path(args.directory).resolve()
        
        # SECURITY: Resolve and validate directory (prevents traversal)
        if not directory.exists():
            print(f"Error: Directory '{directory}' does not exist", file=sys.stderr)
            sys.exit(1)
        
        if not directory.is_dir():
            print(f"Error: '{directory}' is not a directory", file=sys.stderr)
            sys.exit(1)
        
        # Use parent as base_dir for security validation, or directory if at root
        base_dir = directory.parent if directory.parent != directory else directory
        
        print(f"Indexing {directory}...")
        count = memory.index_directory(str(directory), base_dir=str(base_dir))
        print(f"✓ Indexed {count} files from {directory}")
        
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_search(args):
    """Search the memory index."""
    try:
        memory = fmem.MemoryRetrieval()
        
        results = memory.search(args.query, top_k=args.top_k)
        
        if not results:
            print("No results found")
            return
        
        for i, r in enumerate(results, 1):
            print(f"\n{i}. Score: {r['score']:.3f}")
            print(f"   Source: {r.get('source', r.get('filepath', 'unknown'))}")
            content = r.get('content', r.get('chunk', ''))
            preview = content[:200] + "..." if len(content) > 200 else content
            print(f"   {preview}")
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_status(args):
    """Show index status."""
    try:
        memory = fmem.MemoryRetrieval()
        
        doc_count = memory.get_document_count()
        chunk_count = memory.get_chunk_count()
        
        print("fmem Index Status")
        print("=" * 40)
        print(f"Documents indexed: {doc_count}")
        print(f"Chunks indexed: {chunk_count}")
        
        # Show config info
        print("\nConfiguration:")
        print(f"  Data directory: {memory.config.data_dir}")
        print(f"  Ollama URL: {memory.config.ollama_url}")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="fmem - FAISS-based Memory Search for OpenClaw",
        prog="fmem"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Index command
    index_parser = subparsers.add_parser("index", help="Index a directory")
    index_parser.add_argument("directory", help="Directory to index")
    index_parser.set_defaults(func=cmd_index)
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Search memory")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("-k", "--top-k", type=int, default=5, help="Number of results")
    search_parser.set_defaults(func=cmd_search)
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Show index status")
    status_parser.set_defaults(func=cmd_status)
    
    # Parse arguments
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        sys.exit(0)
    
    # Call the appropriate command handler
    args.func(args)


if __name__ == "__main__":
    main()
