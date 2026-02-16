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
        
        if args.directory:
            # Single directory mode
            directory = Path(args.directory).resolve()
            
            # SECURITY: Resolve and validate directory (prevents traversal)
            if not directory.exists():
                print(f"Error: Directory '{directory}' does not exist", file=sys.stderr)
                sys.exit(1)
            
            if directory.is_file():
                # Single file mode
                print(f"Indexing file {directory}...")
                count = memory.index_file(str(directory))
                print(f"✓ Indexed {count} chunks from {directory}")
            elif directory.is_dir():
                # Directory mode  
                # Use parent as base_dir for security validation, or directory if at root
                base_dir = directory.parent if directory.parent != directory else directory
                
                print(f"Indexing directory {directory}...")
                count = memory.index_directory(str(directory), base_dir=str(base_dir))
                print(f"✓ Indexed {count} files from {directory}")
            else:
                print(f"Error: '{directory}' is not a file or directory", file=sys.stderr)
                sys.exit(1)
        else:
            # Auto-index mode from config
            config = fmem.CONFIG
            
            # Build list of directories to index
            directories = []
            
            # Add additional directories from config
            # Note: data_dir is for index storage only, not content indexing
            if hasattr(config, 'additional_dirs') and config.additional_dirs:
                additional = [d.strip() for d in config.additional_dirs.split(',') if d.strip()]
                directories.extend(additional)
            
            # Build exclusion list from config
            exclude_dirs = []
            if hasattr(config, 'exclude_dirs') and config.exclude_dirs:
                exclude_dirs = [d.strip() for d in config.exclude_dirs.split(',') if d.strip()]
            
            if not directories:
                print("Error: No directories configured for indexing", file=sys.stderr)
                print("Configure directories in fmem.conf:", file=sys.stderr)
                print("  - Set additional_dirs (comma-separated list)", file=sys.stderr)
                sys.exit(1)
            
            print(f"Indexing {len(directories)} configured directories...")
            print(f"File types: {', '.join(config.VALID_EXTENSIONS)}")
            if exclude_dirs:
                print(f"Excluding: {', '.join(exclude_dirs)}")
            
            total_count = 0
            for directory in directories:
                dir_path = Path(directory).resolve()
                if dir_path.exists() and dir_path.is_dir():
                    # Check if this directory should be excluded
                    dir_name_lower = dir_path.name.lower()
                    if dir_name_lower in [d.lower() for d in exclude_dirs]:
                        print(f"   ⏭️  Skipping excluded directory: {directory}")
                        continue
                    
                    print(f"\n📁 Indexing {directory}...")
                    count = memory.index_directory(str(dir_path), base_dir=str(dir_path.parent))
                    print(f"   ✓ Indexed {count} files")
                    total_count += count
                else:
                    print(f"   ⚠️  Directory not found: {directory}")
            
            print(f"\n✅ Total indexed {total_count} files across all configured directories")
        
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
    index_parser.add_argument("directory", nargs="?", help="Directory to index (optional - auto-indexes all configured directories)")
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
