#!/usr/bin/env python3
"""Simple CLI for fmem memory search."""

import argparse
import sys
from pathlib import Path

from .memory_retrieval import MemoryRetrieval
from .fmem import CONFIG


def _get_files_in_directory(directory: Path, config, exclude_dirs: list) -> list:
    """Recursively get all valid files in a directory."""
    files = []
    valid_extensions = {ext.lower() for ext in config.VALID_EXTENSIONS}
    exclude_set = {d.lower() for d in exclude_dirs}
    
    for item in directory.rglob('*'):
        if item.is_file():
            # Check if this file is in an excluded directory
            path_parts = [p.lower() for p in item.relative_to(directory).parts[:-1]]
            if any(part in exclude_set for part in path_parts):
                continue
            if item.suffix.lower() in valid_extensions:
                files.append(str(item))
    
    return files


def cmd_index(args):
    """Index a directory of files."""
    try:
        memory = MemoryRetrieval()
        
        if args.directory:
            # Single directory mode
            directory = Path(args.directory).resolve()
            
            if not directory.exists():
                print(f"Error: Directory '{directory}' does not exist", file=sys.stderr)
                sys.exit(1)
            
            if directory.is_file():
                # Single file mode
                print(f"Indexing file {directory}...")
                success = memory.add_document(str(directory))
                if success:
                    memory.persist()
                    print(f"✓ Indexed {directory}")
                else:
                    print(f"   ⏭️  Skipped (already indexed or error): {directory}")
            elif directory.is_dir():
                # Directory mode
                print(f"Indexing directory {directory}...")
                files = _get_files_in_directory(directory, memory.config, [])
                if not files:
                    print(f"   ⚠️  No valid files found in {directory}")
                    return
                
                results = memory.add_documents_batch(files, use_progress=False)
                successful = sum(1 for v in results.values() if v)
                memory.persist()
                print(f"✓ Indexed {successful}/{len(files)} files from {directory}")
            else:
                print(f"Error: '{directory}' is not a file or directory", file=sys.stderr)
                sys.exit(1)
        else:
            # Auto-index mode from config
            config = memory.config
            
            # Build list of directories to index
            directories = []
            
            if hasattr(config, 'additional_dirs') and config.additional_dirs:
                directories = [d.strip() for d in config.additional_dirs.split(',') if d.strip()]
            
            if not directories:
                print("Error: No directories configured for indexing", file=sys.stderr)
                print("Configure directories in fmem.conf:", file=sys.stderr)
                print("  additional_dirs = /path/to/memory, /path/to/notes", file=sys.stderr)
                sys.exit(1)
            
            # Build exclusion list from config
            exclude_dirs = []
            if hasattr(config, 'exclude_dirs') and config.exclude_dirs:
                exclude_dirs = [d.strip().lower() for d in config.exclude_dirs.split(',') if d.strip()]
            
            # Default exclusions
            default_excludes = ['venv', 'env', '.venv', '.env', 'node_modules', '__pycache__', 
                           '.git', '.pytest_cache', 'cache', 'dist', 'build', '.tox']
            exclude_dirs.extend(default_excludes)
            
            print(f"Indexing {len(directories)} configured directories...")
            print(f"File types: {', '.join(config.VALID_EXTENSIONS)}")
            if exclude_dirs:
                print(f"Excluding: {', '.join(exclude_dirs[:5])}{'...' if len(exclude_dirs) > 5 else ''}")
            
            total_files = 0
            total_successful = 0
            
            for directory in directories:
                dir_path = Path(directory).expanduser().resolve()
                if dir_path.exists() and dir_path.is_dir():
                    # Check if this directory should be excluded
                    if dir_path.name.lower() in exclude_dirs:
                        print(f"   ⏭️  Skipping excluded directory: {directory}")
                        continue
                    
                    print(f"\n📁 Indexing {directory}...")
                    files = _get_files_in_directory(dir_path, config, exclude_dirs)
                    if not files:
                        print(f"   ⚠️  No valid files found")
                        continue
                    
                    results = memory.add_documents_batch(files, use_progress=False)
                    successful = sum(1 for v in results.values() if v)
                    total_files += len(files)
                    total_successful += successful
                    print(f"   ✓ Indexed {successful}/{len(files)} files")
                else:
                    print(f"   ⚠️  Directory not found: {directory}")
            
            # Persist all changes
            memory.persist()
            
            # Index specific files (e.g., project READMEs)
            if hasattr(config, 'index_files') and config.index_files:
                files = [f.strip() for f in config.index_files.split(',') if f.strip()]
                if files:
                    print(f"\n📄 Indexing {len(files)} specific files...")
                    for filepath in files:
                        file_path = Path(filepath).expanduser().resolve()
                        if file_path.exists() and file_path.is_file():
                            if file_path.suffix.lower() in config.VALID_EXTENSIONS:
                                print(f"   Indexing {filepath}...")
                                success = memory.add_document(str(file_path))
                                if success:
                                    total_successful += 1
                                    print(f"   ✓ Indexed {filepath}")
                                else:
                                    print(f"   ⏭️  Skipped (already indexed): {filepath}")
                            else:
                                print(f"   ⏭️  Skipping (not in allowed extensions): {filepath}")
                        else:
                            print(f"   ⚠️  File not found: {filepath}")
                    memory.persist()
            
            print(f"\n✅ Total indexed {total_successful}/{total_files} files across all directories")
            
            # Show stats
            stats = memory.get_stats()
            print(f"\nIndex stats: {stats['documents']['total_documents']} documents, "
                  f"{stats['index_size']} chunks")
        
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


def cmd_search(args):
    """Search the memory index."""
    try:
        memory = MemoryRetrieval()
        
        results = memory.search(args.query, top_k=args.top_k)
        
        if not results:
            print("No results found")
            return
        
        for i, r in enumerate(results, 1):
            print(f"\n{i}. Score: {r['score']:.3f}")
            source = r.get('source', r.get('filepath', 'unknown'))
            print(f"   Source: {source}")
            content = r.get('content', r.get('chunk', r.get('summary', '')))
            preview = content[:200] + "..." if len(content) > 200 else content
            print(f"   {preview}")
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_status(args):
    """Show index status."""
    try:
        memory = MemoryRetrieval()
        
        stats = memory.get_stats()
        
        print("fmem Index Status")
        print("=" * 40)
        print(f"Documents indexed: {stats['documents']['total_documents']}")
        print(f"Total chunks: {stats['index_size']}")
        print(f"Embedding cache size: {stats['embedding_cache_size']}")
        
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